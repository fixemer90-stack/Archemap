from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, time
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.modules.astrotype_v2.models import NatalChart
from app.modules.child.chart_adapter import ChildChartBuild
from app.modules.child.models import ChildChartVersion, ChildProfile, ChildReport
from app.modules.child.repository import ChildIdempotencyTargetMismatchError, ChildRepository
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User

pytestmark = pytest.mark.usefixtures("_setup_database")


def _chart_build(input_hash: str, *, confidence: str) -> ChildChartBuild:
    return ChildChartBuild(
        engine_version="child-chart-test-1",
        input_hash=input_hash,
        birth_time_confidence=confidence,
        allowed_fact_families=("planet_signs",),
        excluded_fact_families=() if confidence == "exact" else ("houses",),
        uncertainty_reason=None if confidence == "exact" else "unknown time",
        calculation_payload={
            "contract_version": "child-birth-time-policy-v2",
            "technical_reference": {"synthetic_noon": confidence == "unknown"},
        },
    )


@pytest.mark.asyncio
async def test_chart_persistence_is_concurrent_idempotent_and_correction_preserves_report_lineage(
    db_session: AsyncSession,
) -> None:
    owner = User(
        email=f"child-chart-{uuid4()}@example.com",
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
        birth_time=time(9, 0),
        birth_time_accuracy="exact",
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
        birth_datetime_utc=datetime(1990, 1, 1, 6, 0, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.7558,
        longitude=37.6173,
        house_system="P",
        calculation_payload={},
    )
    db_session.add(parent_chart)
    await db_session.flush()
    child_result = await ChildRepository(db_session).create_child_idempotently(
        owner_user_id=owner.id,
        parent_profile_id=parent_profile.id,
        display_name="Child",
        relationship_type="child",
        child_gender="female",
        birth_date=date(2021, 1, 3),
        birth_time=None,
        birth_time_confidence="unknown",
        birth_place="Moscow",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        caregiver_context={},
        birth_data_hash="a" * 64,
        idempotency_key="child-chart-profile",
    )
    await db_session.commit()

    assert isinstance(db_session.bind, AsyncEngine)
    session_factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    original_build = _chart_build("b" * 64, confidence="unknown")

    async def persist_original() -> tuple[bool, UUID]:
        async with session_factory() as session:
            result = await ChildRepository(session).create_chart_version_idempotently(
                owner_user_id=owner.id,
                child_profile_id=child_result.child.id,
                chart=original_build,
            )
            await session.commit()
            return result.created, result.chart.id

    first, second = await asyncio.gather(persist_original(), persist_original())
    assert sorted([first[0], second[0]]) == [False, True]
    assert first[1] == second[1]
    original_chart_id = first[1]

    repository = ChildRepository(db_session)
    generation = await repository.create_generation_idempotently(
        owner_user_id=owner.id,
        child_profile_id=child_result.child.id,
        parent_chart_id=parent_chart.id,
        child_chart_version_id=original_chart_id,
        operation="create",
        idempotency_key="original-generation",
    )
    report = await repository.create_report_idempotently(
        owner_user_id=owner.id,
        child_profile_id=child_result.child.id,
        generation_id=generation.generation.generation_id,
        parent_chart_id=parent_chart.id,
        child_chart_version_id=original_chart_id,
        idempotency_key="original-report",
        version=1,
        status="deterministic_ready",
        scoring_version="child-score-1",
        reference_version="child-reference-1",
        questionnaire_version="child-questionnaire-1",
        prompt_version="child-prompt-1",
        report_payload={},
        presentation_manifest={},
    )
    await db_session.commit()

    corrected = await repository.correct_birth_data_and_create_chart(
        owner_user_id=owner.id,
        child_profile_id=child_result.child.id,
        birth_date=date(2021, 1, 3),
        birth_time=time(10, 30),
        birth_time_confidence="exact",
        birth_place="Moscow",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        birth_data_hash="c" * 64,
        chart=_chart_build("d" * 64, confidence="exact"),
    )
    await db_session.commit()

    chart_versions = (
        (
            await db_session.execute(
                select(ChildChartVersion)
                .where(ChildChartVersion.child_profile_id == child_result.child.id)
                .order_by(ChildChartVersion.version)
            )
        )
        .scalars()
        .all()
    )
    persisted_report = await db_session.get(ChildReport, report.report.id)
    persisted_child = await db_session.get(ChildProfile, child_result.child.id)

    assert [(row.id, row.version) for row in chart_versions] == [
        (original_chart_id, 1),
        (corrected.chart.id, 2),
    ]
    assert persisted_report is not None
    assert persisted_report.child_chart_version_id == original_chart_id
    assert persisted_child is not None
    assert persisted_child.birth_time == time(10, 30)
    assert persisted_child.birth_time_confidence == "exact"
    assert persisted_child.version == 2
    child_id = persisted_child.id

    with pytest.raises(ChildIdempotencyTargetMismatchError):
        await repository.correct_birth_data_and_create_chart(
            owner_user_id=owner.id,
            child_profile_id=child_result.child.id,
            birth_date=date(2021, 1, 3),
            birth_time=time(11, 0),
            birth_time_confidence="exact",
            birth_place="Moscow",
            latitude=55.7558,
            longitude=37.6173,
            timezone="Europe/Moscow",
            birth_data_hash="e" * 64,
            chart=_chart_build("d" * 64, confidence="exact"),
        )
    await db_session.rollback()

    unchanged_child = await db_session.get(ChildProfile, child_id)
    assert unchanged_child is not None
    assert unchanged_child.birth_time == time(10, 30)
    assert unchanged_child.version == 2
