"""Domain primitives for durable birth-data refinement."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ArchemapError, AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.infrastructure.timezone import TimezoneResolver
from app.modules.astrotype_v2.models import NatalReportGeneration
from app.modules.profiles.models import PersonProfile, ProfileBirthDataRevision
from app.modules.profiles.schemas import BirthDataRefinementRequest, BirthDataRefinementStatusResponse
from app.modules.users.models import User

COOLDOWN_WINDOW = timedelta(hours=24)
GEOCODE_SELECTION_TTL = timedelta(hours=24)
_BIRTH_DATA_FIELDS = (
    "birth_time",
    "birth_time_accuracy",
    "birth_place",
    "latitude",
    "longitude",
    "timezone",
)


@dataclass(frozen=True, slots=True)
class BirthDataSnapshot:
    """Complete normalized birth-data input used by one chart calculation."""

    birth_time: time | None
    birth_time_accuracy: str
    birth_place: str
    latitude: float
    longitude: float
    timezone: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["birth_time"] = self.birth_time.isoformat() if self.birth_time is not None else None
        return payload

    def changed_fields(self, other: BirthDataSnapshot) -> list[str]:
        return [field for field in _BIRTH_DATA_FIELDS if getattr(self, field) != getattr(other, field)]


class BirthDataCooldownError(ConflictError):
    """The account-wide rolling refinement window has not elapsed."""

    def __init__(self, *, next_available_at: datetime, now: datetime) -> None:
        super().__init__(
            "Данные рождения можно уточнять не чаще одного раза за 24 часа",
            code="birth_data_refinement_cooldown",
        )
        self.next_available_at = next_available_at
        self.retry_after_seconds = max(0, math.ceil((next_available_at - now).total_seconds()))


class BirthDataAccuracyMismatchError(ArchemapError):
    def __init__(self) -> None:
        super().__init__("Birth time and accuracy are inconsistent", code="birth_time_accuracy_mismatch")


class BirthDataPlaceNotGeocodedError(ValidationError):
    def __init__(self) -> None:
        super().__init__("Birth place must be selected from a geocoded result", code="birth_place_not_geocoded")


class BirthDataProfileNotOwnedError(AuthorizationError):
    def __init__(self) -> None:
        super().__init__("Profile does not belong to the current user", code="profile_not_owned")


class BirthDataCooldownPolicy:
    """Pure boundary policy shared by repository and API layers."""

    @staticmethod
    def ensure_available(*, last_successful_at: datetime | None, now: datetime) -> None:
        if last_successful_at is None:
            return
        next_available_at = last_successful_at + COOLDOWN_WINDOW
        if now < next_available_at:
            raise BirthDataCooldownError(next_available_at=next_available_at, now=now)


class BirthDataNoChangesError(ValidationError):
    """The submitted complete snapshot matches the stored profile."""

    def __init__(self) -> None:
        super().__init__("Birth data did not change", code="birth_data_unchanged")


class BirthDataIdempotencyConflictError(ConflictError):
    """An idempotency key was reused with a different request payload."""

    def __init__(self) -> None:
        super().__init__(
            "Idempotency key was already used with another payload",
            code="idempotency_key_conflict",
        )


class BirthDataProfileNotFoundError(NotFoundError):
    """The requested profile is absent or does not belong to the account."""

    def __init__(self) -> None:
        super().__init__("Profile not found", code="profile_not_found")


class BirthDataProfileDeletionConflictError(ConflictError):
    """A profile with immutable birth-data history cannot be deleted."""

    def __init__(self) -> None:
        super().__init__(
            "Profile cannot be deleted because birth-data refinement history exists",
            code="profile_has_birth_data_revisions",
        )


@dataclass(frozen=True, slots=True)
class BirthDataRevisionCreateResult:
    revision: ProfileBirthDataRevision
    created: bool


class BirthDataRevisionRepository:
    """Transactional creation boundary serialized by the owning user row."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_revision(
        self,
        *,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        new_snapshot: BirthDataSnapshot,
        idempotency_key: str,
        request_hash: str,
        generation_id: uuid.UUID,
        now: datetime | None = None,
    ) -> BirthDataRevisionCreateResult:
        await self._lock_user(user_id)
        profile = await self._get_profile(user_id=user_id, profile_id=profile_id)
        committed_at = now or await self.session.scalar(select(func.now()))
        if committed_at is None:
            committed_at = datetime.now(UTC)

        existing = await self._get_by_idempotency(user_id=user_id, idempotency_key=idempotency_key)
        if existing is not None:
            if existing.profile_id != profile_id or existing.request_hash != request_hash:
                raise BirthDataIdempotencyConflictError
            return BirthDataRevisionCreateResult(revision=existing, created=False)

        previous_snapshot = BirthDataSnapshot(
            birth_time=profile.birth_time,
            birth_time_accuracy=profile.birth_time_accuracy,
            birth_place=profile.birth_place,
            latitude=profile.latitude,
            longitude=profile.longitude,
            timezone=profile.timezone,
        )
        changed_fields = previous_snapshot.changed_fields(new_snapshot)
        if not changed_fields:
            raise BirthDataNoChangesError

        latest_created_at = await self.session.scalar(
            select(ProfileBirthDataRevision.created_at)
            .where(ProfileBirthDataRevision.user_id == user_id)
            .order_by(ProfileBirthDataRevision.created_at.desc(), ProfileBirthDataRevision.id.desc())
            .limit(1)
        )
        BirthDataCooldownPolicy.ensure_available(last_successful_at=latest_created_at, now=committed_at)

        profile.birth_time = new_snapshot.birth_time
        profile.birth_time_accuracy = new_snapshot.birth_time_accuracy
        profile.birth_place = new_snapshot.birth_place
        profile.latitude = new_snapshot.latitude
        profile.longitude = new_snapshot.longitude
        profile.timezone = new_snapshot.timezone

        generation = NatalReportGeneration(
            generation_id=generation_id,
            user_id=user_id,
            profile_id=profile_id,
            status="queued",
            diagnostics={"source": "birth_data_refinement"},
        )
        revision = ProfileBirthDataRevision(
            user_id=user_id,
            profile_id=profile_id,
            previous_snapshot=previous_snapshot.to_dict(),
            new_snapshot=new_snapshot.to_dict(),
            changed_fields=changed_fields,
            status="queued",
            generation_id=generation_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            created_at=committed_at,
            updated_at=committed_at,
        )
        self.session.add_all((generation, revision))
        await self.session.flush()
        return BirthDataRevisionCreateResult(revision=revision, created=True)

    async def ensure_owned_profile(self, *, user_id: uuid.UUID, profile_id: uuid.UUID) -> PersonProfile:
        return await self._get_profile(user_id=user_id, profile_id=profile_id)

    async def latest_revision_at(self, *, user_id: uuid.UUID) -> datetime | None:
        latest: datetime | None = await self.session.scalar(
            select(ProfileBirthDataRevision.created_at)
            .where(ProfileBirthDataRevision.user_id == user_id)
            .order_by(ProfileBirthDataRevision.created_at.desc(), ProfileBirthDataRevision.id.desc())
            .limit(1)
        )
        return latest

    async def get_revision(
        self,
        *,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        revision_id: uuid.UUID,
    ) -> ProfileBirthDataRevision:
        await self._get_profile(user_id=user_id, profile_id=profile_id)
        revision = await self.session.scalar(
            select(ProfileBirthDataRevision).where(
                ProfileBirthDataRevision.id == revision_id,
                ProfileBirthDataRevision.profile_id == profile_id,
                ProfileBirthDataRevision.user_id == user_id,
            )
        )
        if revision is None:
            raise BirthDataProfileNotFoundError
        return revision

    async def get_generation(self, generation_id: uuid.UUID) -> NatalReportGeneration | None:
        generation: NatalReportGeneration | None = await self.session.scalar(
            select(NatalReportGeneration).where(NatalReportGeneration.generation_id == generation_id)
        )
        return generation

    async def claim_dispatch(
        self,
        *,
        revision_id: uuid.UUID,
        stale_before: datetime,
    ) -> ProfileBirthDataRevision | None:
        result = await self.session.execute(
            update(ProfileBirthDataRevision)
            .where(
                ProfileBirthDataRevision.id == revision_id,
                or_(
                    ProfileBirthDataRevision.dispatch_status == "pending",
                    (
                        (ProfileBirthDataRevision.dispatch_status == "dispatching")
                        & (ProfileBirthDataRevision.dispatch_claimed_at < stale_before)
                    ),
                ),
            )
            .values(
                dispatch_status="dispatching",
                dispatch_attempts=ProfileBirthDataRevision.dispatch_attempts + 1,
                dispatch_claimed_at=func.now(),
                dispatch_error_code=None,
            )
            .returning(ProfileBirthDataRevision)
        )
        return result.scalar_one_or_none()

    async def mark_dispatched(self, *, revision_id: uuid.UUID) -> None:
        await self.session.execute(
            update(ProfileBirthDataRevision)
            .where(ProfileBirthDataRevision.id == revision_id)
            .values(dispatch_status="dispatched", dispatched_at=func.now(), dispatch_error_code=None)
        )

    async def release_dispatch(self, *, revision_id: uuid.UUID, error_code: str) -> None:
        await self.session.execute(
            update(ProfileBirthDataRevision)
            .where(ProfileBirthDataRevision.id == revision_id)
            .values(dispatch_status="pending", dispatch_claimed_at=None, dispatch_error_code=error_code)
        )

    async def list_dispatchable(self, *, stale_before: datetime, limit: int = 100) -> list[uuid.UUID]:
        result = await self.session.execute(
            select(ProfileBirthDataRevision.id)
            .where(
                or_(
                    ProfileBirthDataRevision.dispatch_status == "pending",
                    (
                        (ProfileBirthDataRevision.dispatch_status == "dispatching")
                        & (ProfileBirthDataRevision.dispatch_claimed_at < stale_before)
                    ),
                )
            )
            .order_by(ProfileBirthDataRevision.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _lock_user(self, user_id: uuid.UUID) -> None:
        user = await self.session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None:
            raise BirthDataProfileNotFoundError

    async def _get_by_idempotency(
        self,
        *,
        user_id: uuid.UUID,
        idempotency_key: str,
    ) -> ProfileBirthDataRevision | None:
        revision: ProfileBirthDataRevision | None = await self.session.scalar(
            select(ProfileBirthDataRevision).where(
                ProfileBirthDataRevision.user_id == user_id,
                ProfileBirthDataRevision.idempotency_key == idempotency_key,
            )
        )
        return revision

    async def _get_profile(self, *, user_id: uuid.UUID, profile_id: uuid.UUID) -> PersonProfile:
        profile = await self.session.scalar(select(PersonProfile).where(PersonProfile.id == profile_id))
        if profile is None:
            raise BirthDataProfileNotFoundError
        if profile.user_id != user_id:
            raise BirthDataProfileNotOwnedError
        return profile


def _normalize_place(value: str) -> str:
    return " ".join(value.split())


def _geocode_token_payload(
    *,
    place: str,
    latitude: float,
    longitude: float,
    timezone: str,
    issued_at: datetime,
) -> dict[str, object]:
    return {
        "place": _normalize_place(place),
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6),
        "timezone": timezone,
        "issued_at": int(issued_at.timestamp()),
    }


def create_geocode_selection_token(
    *,
    secret: str,
    place: str,
    latitude: float,
    longitude: float,
    timezone: str,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    payload = _geocode_token_payload(
        place=place,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        issued_at=issued_at,
    )
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(secret.encode(), encoded, hashlib.sha256).digest()
    encoded_token = base64.urlsafe_b64encode(encoded).decode().rstrip("=")
    signature_token = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{encoded_token}.{signature_token}"


def verify_geocode_selection_token(
    *,
    token: str,
    secret: str,
    place: str,
    latitude: float,
    longitude: float,
    timezone: str,
    now: datetime | None = None,
) -> None:
    try:
        encoded_part, signature_part = token.split(".", 1)
        encoded = base64.urlsafe_b64decode(encoded_part + "=" * (-len(encoded_part) % 4))
        signature = base64.urlsafe_b64decode(signature_part + "=" * (-len(signature_part) % 4))
        expected = hmac.new(secret.encode(), encoded, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        payload = json.loads(encoded)
        issued_at = datetime.fromtimestamp(int(payload["issued_at"]), tz=UTC)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise BirthDataPlaceNotGeocodedError from exc

    current = now or datetime.now(UTC)
    if issued_at > current + timedelta(minutes=5) or current - issued_at > GEOCODE_SELECTION_TTL:
        raise BirthDataPlaceNotGeocodedError
    expected_payload = _geocode_token_payload(
        place=place,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        issued_at=issued_at,
    )
    if payload != expected_payload:
        raise BirthDataPlaceNotGeocodedError


def map_generation_status(status: str) -> str:
    return {
        "queued": "queued",
        "running": "processing",
        "narrative_generating": "deterministic_ready",
        "deterministic_ready": "deterministic_ready",
        "complete": "ready",
        "ready": "ready",
        "already_exists": "ready",
        "partial": "ready",
        "narrative_failed": "deterministic_ready",
        "failed": "failed",
    }.get(status, "processing")


def canonical_request_hash(profile_id: uuid.UUID, request: BirthDataRefinementRequest) -> str:
    """Hash the profile-bound normalized request snapshot with canonical JSON."""

    payload = {"profile_id": str(profile_id), **request.model_dump(mode="json", exclude={"geocode_selection_token"})}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class BirthDataRefinementService:
    """Validation and persistence orchestration for refinement endpoints."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        timezone_resolver: TimezoneResolver,
        repository: BirthDataRevisionRepository | None = None,
        clock: Callable[[], datetime] | None = None,
        geocode_token_secret: str,
    ) -> None:
        self.session = session
        self.repository = repository or BirthDataRevisionRepository(session)
        self.timezone_resolver = timezone_resolver
        self.clock = clock
        self.geocode_token_secret = geocode_token_secret

    async def validate_snapshot(self, request: BirthDataRefinementRequest) -> BirthDataSnapshot:
        if request.birth_time_accuracy in {"exact", "approximate"} and request.birth_time is None:
            raise BirthDataAccuracyMismatchError
        if request.birth_time_accuracy == "unknown" and request.birth_time is not None:
            raise BirthDataAccuracyMismatchError
        if (
            not request.birth_place.strip()
            or len(request.birth_place) > 300
            or not (-90 <= request.latitude <= 90)
            or not (-180 <= request.longitude <= 180)
            or (request.latitude == 0.0 and request.longitude == 0.0)
            or not request.timezone
            or len(request.timezone) > 60
        ):
            raise BirthDataPlaceNotGeocodedError
        current = self.clock() if self.clock is not None else datetime.now(UTC)
        verify_geocode_selection_token(
            token=request.geocode_selection_token,
            secret=self.geocode_token_secret,
            place=request.birth_place,
            latitude=request.latitude,
            longitude=request.longitude,
            timezone=request.timezone,
            now=current,
        )
        try:
            ZoneInfo(request.timezone)
        except ZoneInfoNotFoundError as exc:
            raise BirthDataPlaceNotGeocodedError from exc
        resolved_timezone = await self.timezone_resolver.resolve(request.latitude, request.longitude)
        if resolved_timezone is None or resolved_timezone != request.timezone:
            raise BirthDataPlaceNotGeocodedError
        return BirthDataSnapshot(
            birth_time=request.birth_time,
            birth_time_accuracy=request.birth_time_accuracy,
            birth_place=request.birth_place,
            latitude=request.latitude,
            longitude=request.longitude,
            timezone=request.timezone,
        )

    async def get_status(
        self,
        *,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> BirthDataRefinementStatusResponse:
        await self.repository.ensure_owned_profile(user_id=user_id, profile_id=profile_id)
        now = self.clock() if self.clock is not None else datetime.now(UTC)
        last_refined_at = await self.repository.latest_revision_at(user_id=user_id)
        next_available_at = last_refined_at + COOLDOWN_WINDOW if last_refined_at is not None else None
        can_refine = next_available_at is None or now >= next_available_at
        retry_after_seconds = (
            0 if can_refine or next_available_at is None else math.ceil((next_available_at - now).total_seconds())
        )
        return BirthDataRefinementStatusResponse(
            profile_id=profile_id,
            can_refine=can_refine,
            last_refined_at=last_refined_at,
            next_available_at=next_available_at,
            retry_after_seconds=retry_after_seconds,
        )

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        request: BirthDataRefinementRequest,
        idempotency_key: uuid.UUID,
    ) -> BirthDataRevisionCreateResult:
        snapshot = await self.validate_snapshot(request)
        return await self.repository.create_revision(
            user_id=user_id,
            profile_id=profile_id,
            new_snapshot=snapshot,
            idempotency_key=str(idempotency_key),
            request_hash=canonical_request_hash(profile_id, request),
            generation_id=uuid.uuid4(),
            now=self.clock() if self.clock is not None else None,
        )
