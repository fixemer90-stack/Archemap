from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.modules.astrotype_v2.models import NatalChart, NatalFact, NatalFactEvidence
from app.modules.child.models import ChildChartVersion, ChildGeneration, ChildParentStyleScore, ChildProfile
from app.modules.child.repository import ChildLineageMismatchError, ChildRepository
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User

pytestmark = pytest.mark.usefixtures("_setup_database")


def _score_snapshot(rows: tuple[ChildParentStyleScore, ...]) -> list[tuple[object, ...]]:
    return [
        (
            row.dimension,
            row.score,
            row.confidence,
            row.scoring_version,
            row.evidence_refs,
            row.breakdown,
        )
        for row in rows
    ]


@pytest.mark.asyncio
async def test_parent_style_persists_and_reloads_exact_versioned_profile_from_postgresql(
    db_session: AsyncSession,
) -> None:
    owner = User(
        email=f"parent-style-{uuid4()}@example.com",
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
        birth_place="Moscow",
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
        birth_datetime_utc=datetime(1990, 1, 1, 9, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.7558,
        longitude=37.6173,
        house_system="P",
        calculation_payload={
            "birth_time_proof": {
                "confidence": "exact",
                "user_supplied_time": True,
                "synthetic_noon": False,
            }
        },
    )
    db_session.add(parent_chart)
    await db_session.flush()

    child = ChildProfile(
        owner_user_id=owner.id,
        parent_profile_id=parent_profile.id,
        display_name="Child",
        relationship_type="child",
        child_gender="female",
        birth_date=date(2021, 5, 12),
        birth_time=None,
        birth_time_confidence="unknown",
        birth_place="Moscow",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        caregiver_context={},
        birth_data_hash="c" * 64,
        idempotency_key="parent-style-child",
        status="active",
        version=1,
    )
    db_session.add(child)
    await db_session.flush()
    child_chart = ChildChartVersion(
        child_profile_id=child.id,
        version=1,
        engine_version="child-test-v1",
        input_hash="d" * 64,
        birth_time_confidence="unknown",
        allowed_fact_families=["planet_signs"],
        excluded_fact_families=["houses"],
        uncertainty_reason="unknown time",
        calculation_payload={},
    )
    db_session.add(child_chart)
    await db_session.flush()
    generation_id = uuid4()
    db_session.add(
        ChildGeneration(
            child_profile_id=child.id,
            owner_user_id=owner.id,
            parent_chart_id=parent_chart.id,
            child_chart_version_id=child_chart.id,
            generation_id=generation_id,
            operation="create",
            idempotency_key="parent-style-generation",
            status="deterministic_pending",
            diagnostics={},
        )
    )
    intruder = User(
        email=f"parent-style-intruder-{uuid4()}@example.com",
        name="Intruder",
        hashed_password="test-only-hash",  # noqa: S106
        is_active=True,
        is_verified=True,
    )
    db_session.add(intruder)
    await db_session.flush()
    intruder_profile = PersonProfile(
        user_id=intruder.id,
        name="Intruder",
        birth_date=date(1988, 2, 2),
        birth_time=None,
        birth_time_accuracy="unknown",
        birth_place="Kazan",
        latitude=55.7963,
        longitude=49.1088,
        timezone="Europe/Moscow",
    )
    db_session.add(intruder_profile)
    await db_session.flush()
    intruder_chart = NatalChart(
        user_id=intruder.id,
        profile_id=intruder_profile.id,
        engine_version="test-v1",
        input_hash="i" * 64,
        birth_datetime_utc=datetime(1988, 2, 2, 9, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.7963,
        longitude=49.1088,
        house_system="P",
        calculation_payload={},
    )
    db_session.add(intruder_chart)
    await db_session.flush()
    bad_generation_id = uuid4()
    db_session.add(
        ChildGeneration(
            child_profile_id=child.id,
            owner_user_id=owner.id,
            parent_chart_id=intruder_chart.id,
            child_chart_version_id=child_chart.id,
            generation_id=bad_generation_id,
            operation="create",
            idempotency_key="parent-style-bad-generation",
            status="deterministic_pending",
            diagnostics={},
        )
    )

    fact_specs = (
        ("placement:moon:cancer:house_4", "placement", 1.0),
        ("placement:venus:libra:house_7", "placement", 1.0),
        ("placement:mercury:gemini:house_3", "placement", 1.0),
        ("placement:mars:aries:house_1", "placement", 1.0),
        ("placement:saturn:capricorn:house_10", "placement", 1.0),
        ("placement:uranus:aquarius:house_11", "placement", 1.0),
        ("placement:sun:leo:house_5", "placement", 1.0),
        ("balance:element:water", "balance", 0.8),
        ("balance:element:air", "balance", 0.7),
        ("balance:element:earth", "balance", 0.9),
        ("balance:modality:fixed", "balance", 0.6),
        ("balance:modality:mutable", "balance", 0.7),
    )
    for key, fact_type, weight in fact_specs:
        fact = NatalFact(
            chart_id=parent_chart.id,
            fact_type=fact_type,
            fact_key=key,
            title=key,
            summary="Persisted prose is not a scoring input.",
            weight=weight,
            confidence=1.0,
            payload={},
            source_version="v2.0",
        )
        db_session.add(fact)
        await db_session.flush()
        db_session.add(
            NatalFactEvidence(
                fact_id=fact.id,
                chart_id=parent_chart.id,
                source_table=f"astrotype_v2_{fact_type}",
                source_id=uuid4(),
                source_key=key,
                payload={"source_quality": 1.0},
            )
        )
    await db_session.commit()

    assert isinstance(db_session.bind, AsyncEngine)
    session_factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as rejected_session:
        with pytest.raises(ChildLineageMismatchError, match="does not match the owner"):
            await ChildRepository(rejected_session).create_parent_style_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=bad_generation_id,
            )
        await rejected_session.commit()
        assert (
            await rejected_session.scalar(
                select(func.count())
                .select_from(ChildParentStyleScore)
                .where(ChildParentStyleScore.generation_id == bad_generation_id)
            )
            == 0
        )

    async def create_same_profile() -> tuple[bool, tuple[object, ...], list[tuple[object, ...]]]:
        async with session_factory() as session:
            result = await ChildRepository(session).create_parent_style_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=generation_id,
            )
            await session.commit()
            return result.created, tuple(row.id for row in result.scores), _score_snapshot(result.scores)

    first, second = await asyncio.gather(create_same_profile(), create_same_profile())
    assert sorted((first[0], second[0])) == [False, True]
    assert first[1] == second[1]

    async with session_factory() as reload_session:
        loaded = await ChildRepository(reload_session).load_parent_style_profile(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            generation_id=generation_id,
        )
        persisted_count = len(
            (
                await reload_session.execute(
                    select(ChildParentStyleScore).where(ChildParentStyleScore.generation_id == generation_id)
                )
            )
            .scalars()
            .all()
        )

    assert persisted_count == 8
    assert tuple(row.id for row in loaded.scores) == first[1]
    assert _score_snapshot(loaded.scores) == first[2] == second[2]
    assert loaded.parent_chart_id == parent_chart.id
    assert loaded.generation_id == generation_id

    async with session_factory() as foreign_session:
        with pytest.raises(ChildLineageMismatchError, match="not owned"):
            await ChildRepository(foreign_session).load_parent_style_profile(
                owner_user_id=intruder.id,
                child_profile_id=child.id,
                generation_id=generation_id,
            )
