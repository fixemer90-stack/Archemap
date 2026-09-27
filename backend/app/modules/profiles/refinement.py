"""Domain primitives for durable birth-data refinement."""

from __future__ import annotations

import math
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.astrotype_v2.models import NatalReportGeneration
from app.modules.profiles.models import PersonProfile, ProfileBirthDataRevision
from app.modules.users.models import User

COOLDOWN_WINDOW = timedelta(hours=24)
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
        super().__init__("Birth data can be refined again after the cooldown window", code="birth_data_cooldown")
        self.next_available_at = next_available_at
        self.retry_after_seconds = max(0, math.ceil((next_available_at - now).total_seconds()))


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
        super().__init__("Birth data did not change", code="birth_data_no_changes")


class BirthDataIdempotencyConflictError(ConflictError):
    """An idempotency key was reused with a different request payload."""

    def __init__(self) -> None:
        super().__init__(
            "Idempotency key was already used with another payload",
            code="birth_data_idempotency_conflict",
        )


class BirthDataProfileNotFoundError(NotFoundError):
    """The requested profile is absent or does not belong to the account."""

    def __init__(self) -> None:
        super().__init__("Profile not found", code="profile_not_found")


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
        now: datetime,
    ) -> BirthDataRevisionCreateResult:
        await self._lock_user(user_id)

        existing = await self._get_by_idempotency(user_id=user_id, idempotency_key=idempotency_key)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise BirthDataIdempotencyConflictError
            return BirthDataRevisionCreateResult(revision=existing, created=False)

        profile = await self._get_profile(user_id=user_id, profile_id=profile_id)
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
        BirthDataCooldownPolicy.ensure_available(last_successful_at=latest_created_at, now=now)

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
            created_at=now,
            updated_at=now,
        )
        self.session.add_all((generation, revision))
        await self.session.flush()
        return BirthDataRevisionCreateResult(revision=revision, created=True)

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
        profile = await self.session.scalar(
            select(PersonProfile).where(
                PersonProfile.id == profile_id,
                PersonProfile.user_id == user_id,
            )
        )
        if profile is None:
            raise BirthDataProfileNotFoundError
        return profile
