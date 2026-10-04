"""PostgreSQL transaction coverage for birth-data refinement storage."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.astrotype_v2.models import NatalReportGeneration
from app.modules.profiles.dispatch import dispatch_birth_data_revision, dispatch_pending_birth_data_revisions
from app.modules.profiles.models import PersonProfile, ProfileBirthDataRevision
from app.modules.profiles.refinement import (
    BirthDataCooldownError,
    BirthDataIdempotencyConflictError,
    BirthDataNoChangesError,
    BirthDataProfileDeletionConflictError,
    BirthDataRevisionRepository,
    BirthDataSnapshot,
)
from app.modules.profiles.service import ProfileService
from app.modules.users.models import User
from tests.conftest import test_session_factory as session_factory


def _snapshot(
    *,
    place: str,
    latitude: float,
    longitude: float,
    birth_time: time = time(14, 30),
) -> BirthDataSnapshot:
    return BirthDataSnapshot(
        birth_time=birth_time,
        birth_time_accuracy="exact",
        birth_place=place,
        latitude=latitude,
        longitude=longitude,
        timezone="Europe/Moscow",
    )


async def _seed_account(db_session: AsyncSession, *, profiles: int = 1) -> tuple[uuid.UUID, list[uuid.UUID]]:
    user_id = uuid.uuid4()
    db_session.add(
        User(
            id=user_id,
            email=f"birth-revision-{user_id}@example.com",
            name="Revision Test",
            hashed_password="not-used",  # noqa: S106 - inert fixture value
            is_active=True,
            is_verified=True,
        )
    )
    await db_session.flush()
    profile_ids = [uuid.uuid4() for _ in range(profiles)]
    db_session.add_all(
        [
            PersonProfile(
                id=profile_id,
                user_id=user_id,
                name=f"Profile {index}",
                birth_date=date(1990, 1, index + 1),
                birth_time=time(12, 0),
                birth_time_accuracy="exact",
                birth_place="Moscow, Russia",
                latitude=55.7558,
                longitude=37.6173,
                timezone="Europe/Moscow",
            )
            for index, profile_id in enumerate(profile_ids)
        ]
    )
    await db_session.commit()
    return user_id, profile_ids


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_create_revision_updates_profile_and_persists_generation_atomically(
    db_session: AsyncSession,
) -> None:
    user_id, (profile_id,) = await _seed_account(db_session)
    now = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
    generation_id = uuid.uuid4()
    snapshot = _snapshot(place="Saint Petersburg, Russia", latitude=59.9343, longitude=30.3351)

    result = await BirthDataRevisionRepository(db_session).create_revision(
        user_id=user_id,
        profile_id=profile_id,
        new_snapshot=snapshot,
        idempotency_key="first-change",
        request_hash="a" * 64,
        generation_id=generation_id,
        now=now,
    )
    await db_session.commit()

    assert result.created is True
    assert result.revision.previous_snapshot["birth_place"] == "Moscow, Russia"
    assert result.revision.new_snapshot == snapshot.to_dict()
    assert result.revision.changed_fields == ["birth_time", "birth_place", "latitude", "longitude"]
    assert result.revision.created_at == now
    profile = await db_session.get(PersonProfile, profile_id)
    assert profile is not None
    assert profile.birth_place == "Saint Petersburg, Russia"
    generation = (
        await db_session.execute(
            select(NatalReportGeneration).where(NatalReportGeneration.generation_id == generation_id)
        )
    ).scalar_one()
    assert generation.status == "queued"
    assert generation.profile_id == profile_id


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_idempotent_replay_returns_original_and_payload_mismatch_conflicts(
    db_session: AsyncSession,
) -> None:
    user_id, (profile_id,) = await _seed_account(db_session)
    repository = BirthDataRevisionRepository(db_session)
    now = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
    snapshot = _snapshot(place="Kazan, Russia", latitude=55.7961, longitude=49.1064)
    first = await repository.create_revision(
        user_id=user_id,
        profile_id=profile_id,
        new_snapshot=snapshot,
        idempotency_key="stable-key",
        request_hash="b" * 64,
        generation_id=uuid.uuid4(),
        now=now,
    )
    await db_session.commit()

    replay = await repository.create_revision(
        user_id=user_id,
        profile_id=profile_id,
        new_snapshot=snapshot,
        idempotency_key="stable-key",
        request_hash="b" * 64,
        generation_id=uuid.uuid4(),
        now=now + timedelta(minutes=1),
    )
    assert replay.created is False
    assert replay.revision.id == first.revision.id

    with pytest.raises(BirthDataIdempotencyConflictError):
        await repository.create_revision(
            user_id=user_id,
            profile_id=profile_id,
            new_snapshot=snapshot,
            idempotency_key="stable-key",
            request_hash="c" * 64,
            generation_id=uuid.uuid4(),
            now=now + timedelta(minutes=1),
        )

    revision_count = await db_session.scalar(select(func.count()).select_from(ProfileBirthDataRevision))
    generation_count = await db_session.scalar(select(func.count()).select_from(NatalReportGeneration))
    assert revision_count == 1
    assert generation_count == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_noop_does_not_consume_cooldown_or_create_generation(db_session: AsyncSession) -> None:
    user_id, (profile_id,) = await _seed_account(db_session)
    repository = BirthDataRevisionRepository(db_session)
    now = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)

    with pytest.raises(BirthDataNoChangesError):
        await repository.create_revision(
            user_id=user_id,
            profile_id=profile_id,
            new_snapshot=_snapshot(
                place="Moscow, Russia",
                latitude=55.7558,
                longitude=37.6173,
                birth_time=time(12, 0),
            ),
            idempotency_key="noop",
            request_hash="d" * 64,
            generation_id=uuid.uuid4(),
            now=now,
        )

    assert await db_session.scalar(select(func.count()).select_from(ProfileBirthDataRevision)) == 0
    assert await db_session.scalar(select(func.count()).select_from(NatalReportGeneration)) == 0

    result = await repository.create_revision(
        user_id=user_id,
        profile_id=profile_id,
        new_snapshot=_snapshot(place="Kazan, Russia", latitude=55.7961, longitude=49.1064),
        idempotency_key="material",
        request_hash="e" * 64,
        generation_id=uuid.uuid4(),
        now=now,
    )
    assert result.created is True


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_account_cooldown_allows_exact_boundary_across_profiles(db_session: AsyncSession) -> None:
    user_id, profile_ids = await _seed_account(db_session, profiles=2)
    repository = BirthDataRevisionRepository(db_session)
    created_at = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    await repository.create_revision(
        user_id=user_id,
        profile_id=profile_ids[0],
        new_snapshot=_snapshot(place="Kazan, Russia", latitude=55.7961, longitude=49.1064),
        idempotency_key="first",
        request_hash="f" * 64,
        generation_id=uuid.uuid4(),
        now=created_at,
    )
    await db_session.commit()

    with pytest.raises(BirthDataCooldownError):
        await repository.create_revision(
            user_id=user_id,
            profile_id=profile_ids[1],
            new_snapshot=_snapshot(place="Omsk, Russia", latitude=54.9885, longitude=73.3242),
            idempotency_key="too-early",
            request_hash="1" * 64,
            generation_id=uuid.uuid4(),
            now=created_at + timedelta(hours=24) - timedelta(microseconds=1),
        )

    boundary = await repository.create_revision(
        user_id=user_id,
        profile_id=profile_ids[1],
        new_snapshot=_snapshot(place="Omsk, Russia", latitude=54.9885, longitude=73.3242),
        idempotency_key="at-boundary",
        request_hash="2" * 64,
        generation_id=uuid.uuid4(),
        now=created_at + timedelta(hours=24),
    )
    assert boundary.created is True


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_user_row_lock_serializes_concurrent_account_refinements(db_session: AsyncSession) -> None:
    user_id, profile_ids = await _seed_account(db_session, profiles=2)
    now = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)

    async def create(index: int) -> str:
        async with session_factory() as session:
            try:
                await BirthDataRevisionRepository(session).create_revision(
                    user_id=user_id,
                    profile_id=profile_ids[index],
                    new_snapshot=_snapshot(
                        place=("Kazan, Russia", "Omsk, Russia")[index],
                        latitude=(55.7961, 54.9885)[index],
                        longitude=(49.1064, 73.3242)[index],
                    ),
                    idempotency_key=f"concurrent-{index}",
                    request_hash=str(index) * 64,
                    generation_id=uuid.uuid4(),
                    now=now,
                )
                await session.commit()
                return "created"
            except BirthDataCooldownError:
                await session.rollback()
                return "cooldown"

    assert sorted(await asyncio.gather(create(0), create(1))) == ["cooldown", "created"]

    async with session_factory() as verification_session:
        assert await verification_session.scalar(select(func.count()).select_from(ProfileBirthDataRevision)) == 1
        assert await verification_session.scalar(select(func.count()).select_from(NatalReportGeneration)) == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_revision_facts_are_immutable_but_status_can_advance(db_session: AsyncSession) -> None:
    user_id, (profile_id,) = await _seed_account(db_session)
    result = await BirthDataRevisionRepository(db_session).create_revision(
        user_id=user_id,
        profile_id=profile_id,
        new_snapshot=_snapshot(place="Kazan, Russia", latitude=55.7961, longitude=49.1064),
        idempotency_key="immutable",
        request_hash="9" * 64,
        generation_id=uuid.uuid4(),
        now=datetime(2026, 9, 27, 12, 0, tzinfo=UTC),
    )
    await db_session.commit()

    result.revision.status = "processing"
    await db_session.commit()
    result.revision.previous_snapshot = {"tampered": True}
    with pytest.raises(ValueError, match="immutable"):
        await db_session.flush()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_idempotency_key_is_bound_to_the_original_owned_profile(db_session: AsyncSession) -> None:
    user_id, profile_ids = await _seed_account(db_session, profiles=2)
    repository = BirthDataRevisionRepository(db_session)
    now = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
    await repository.create_revision(
        user_id=user_id,
        profile_id=profile_ids[0],
        new_snapshot=_snapshot(place="Kazan, Russia", latitude=55.7961, longitude=49.1064),
        idempotency_key="profile-bound-key",
        request_hash="3" * 64,
        generation_id=uuid.uuid4(),
        now=now,
    )
    await db_session.commit()

    with pytest.raises(BirthDataIdempotencyConflictError):
        await repository.create_revision(
            user_id=user_id,
            profile_id=profile_ids[1],
            new_snapshot=_snapshot(place="Omsk, Russia", latitude=54.9885, longitude=73.3242),
            idempotency_key="profile-bound-key",
            request_hash="3" * 64,
            generation_id=uuid.uuid4(),
            now=now + timedelta(minutes=1),
        )


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_durable_dispatch_releases_failure_and_recovers_without_duplicate_publish(
    db_session: AsyncSession,
) -> None:
    user_id, (profile_id,) = await _seed_account(db_session)
    result = await BirthDataRevisionRepository(db_session).create_revision(
        user_id=user_id,
        profile_id=profile_id,
        new_snapshot=_snapshot(place="Kazan, Russia", latitude=55.7961, longitude=49.1064),
        idempotency_key="dispatch",
        request_hash="4" * 64,
        generation_id=uuid.uuid4(),
        now=datetime(2026, 9, 27, 12, 0, tzinfo=UTC),
    )
    await db_session.commit()

    def fail_sender(**_kwargs: object) -> object:
        raise RuntimeError("contains private birth place")

    assert await dispatch_birth_data_revision(db_session, revision_id=result.revision.id, sender=fail_sender) is False
    await db_session.refresh(result.revision)
    assert result.revision.dispatch_status == "pending"
    assert result.revision.dispatch_attempts == 1
    assert result.revision.dispatch_error_code == "broker_unavailable"

    sent: list[dict[str, object]] = []

    def sender(**kwargs: object) -> object:
        sent.append(kwargs)
        return object()

    dispatched, failed = await dispatch_pending_birth_data_revisions(db_session, sender=sender)
    assert (dispatched, failed) == (1, 0)
    assert sent == [
        {
            "revision_id": result.revision.id,
            "profile_id": profile_id,
            "user_id": user_id,
            "generation_id": result.revision.generation_id,
        }
    ]
    assert await dispatch_birth_data_revision(db_session, revision_id=result.revision.id, sender=sender) is True
    assert len(sent) == 1
    await db_session.refresh(result.revision)
    assert result.revision.dispatch_status == "dispatched"
    assert result.revision.dispatch_attempts == 2
    assert result.revision.dispatch_error_code is None


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_profile_with_revision_history_has_defined_delete_conflict(db_session: AsyncSession) -> None:
    user_id, (profile_id,) = await _seed_account(db_session)
    await BirthDataRevisionRepository(db_session).create_revision(
        user_id=user_id,
        profile_id=profile_id,
        new_snapshot=_snapshot(place="Kazan, Russia", latitude=55.7961, longitude=49.1064),
        idempotency_key="delete-conflict",
        request_hash="5" * 64,
        generation_id=uuid.uuid4(),
        now=datetime(2026, 9, 27, 12, 0, tzinfo=UTC),
    )
    await db_session.commit()

    with pytest.raises(BirthDataProfileDeletionConflictError) as exc_info:
        await ProfileService(db_session).delete(profile_id=profile_id, user_id=user_id)

    assert exc_info.value.code == "profile_has_birth_data_revisions"
    assert await db_session.get(PersonProfile, profile_id) is not None
