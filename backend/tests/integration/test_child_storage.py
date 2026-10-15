from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.modules.astrotype_v2.models import NatalChart
from app.modules.child.models import ChildProfile
from app.modules.child.repository import ChildRepository
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User

pytestmark = pytest.mark.usefixtures("_setup_database")


@pytest.mark.asyncio
async def test_child_storage_isolates_multiple_children_and_database_idempotency(
    db_session: AsyncSession,
) -> None:
    owner = User(
        email=f"child-storage-{uuid4()}@example.com",
        name="Parent",
        hashed_password="test-only-hash",  # noqa: S106
        is_active=True,
        is_verified=True,
    )
    db_session.add(owner)
    await db_session.flush()
    parent_profile = PersonProfile(
        user_id=owner.id,
        name="Parent",
        birth_date=date(1990, 1, 1),
        birth_time=None,
        birth_time_accuracy="unknown",
        birth_place="Москва",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
    )
    db_session.add(parent_profile)
    await db_session.flush()
    parent_chart = NatalChart(
        user_id=owner.id,
        profile_id=parent_profile.id,
        engine_version="test-v1",
        input_hash="p" * 64,
        birth_datetime_utc=datetime(1990, 1, 1, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.7558,
        longitude=37.6173,
        house_system="P",
        calculation_payload={},
    )
    db_session.add(parent_chart)
    await db_session.commit()

    assert isinstance(db_session.bind, AsyncEngine)
    session_factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)

    async def create_same_child() -> tuple[bool, UUID]:
        async with session_factory() as session:
            result = await ChildRepository(session).create_child_idempotently(
                owner_user_id=owner.id,
                parent_profile_id=parent_profile.id,
                display_name="Миша",
                relationship_type="son",
                child_gender="male",
                birth_date=date(2021, 5, 12),
                birth_time=None,
                birth_time_confidence="unknown",
                birth_place="Москва",
                latitude=55.7558,
                longitude=37.6173,
                timezone="Europe/Moscow",
                caregiver_context={"primary_caregiver": True},
                birth_data_hash="a" * 64,
                idempotency_key="same-child-key",
            )
            await session.commit()
            return result.created, result.child.id

    first, second = await asyncio.gather(create_same_child(), create_same_child())
    assert sorted([first[0], second[0]]) == [False, True]
    assert first[1] == second[1]

    repository = ChildRepository(db_session)
    sibling = await repository.create_child_idempotently(
        owner_user_id=owner.id,
        parent_profile_id=parent_profile.id,
        display_name="Аня",
        relationship_type="daughter",
        child_gender="female",
        birth_date=date(2023, 2, 3),
        birth_time=None,
        birth_time_confidence="unknown",
        birth_place="Казань",
        latitude=55.7963,
        longitude=49.1088,
        timezone="Europe/Moscow",
        caregiver_context={"primary_caregiver": True},
        birth_data_hash="b" * 64,
        idempotency_key="sibling-key",
    )
    await db_session.commit()

    children = await repository.list_children_for_owner(owner_user_id=owner.id)
    assert {child.id for child in children} == {first[1], sibling.child.id}
    assert await db_session.scalar(select(func.count()).select_from(ChildProfile)) == 2

    first_child = await repository.get_child_for_owner(child_id=first[1], owner_user_id=owner.id)
    assert first_child is not None
    first_child.status = "archived"
    await db_session.commit()

    active = await repository.list_children_for_owner(owner_user_id=owner.id)
    all_children = await repository.list_children_for_owner(owner_user_id=owner.id, include_archived=True)
    assert [child.id for child in active] == [sibling.child.id]
    assert {child.id for child in all_children} == {first[1], sibling.child.id}

    await db_session.delete(first_child)
    await db_session.commit()
    assert await db_session.get(User, owner.id) is not None
    assert await db_session.get(PersonProfile, parent_profile.id) is not None
    assert await db_session.get(ChildProfile, sibling.child.id) is not None
