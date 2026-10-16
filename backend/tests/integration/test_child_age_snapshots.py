from __future__ import annotations

import asyncio
import importlib.util
from datetime import UTC, date, datetime, time
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Connection, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.modules.astrotype_v2.models import NatalChart
from app.modules.child.age_resolver import AGE_RULES_VERSION, age_snapshot_input_hash
from app.modules.child.birth_data import child_birth_data_hash
from app.modules.child.chart_adapter import ChildChartBuild, ChildChartInput, child_chart_input_hash
from app.modules.child.models import ChildAgeSnapshot, ChildChartVersion, ChildProfile, ChildReport
from app.modules.child.repository import (
    ChildAgeUpdateResult,
    ChildLineageMismatchError,
    ChildRepository,
)
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User

pytestmark = pytest.mark.usefixtures("_setup_database")
AGE_SNAPSHOT_MIGRATION = (
    Path(__file__).resolve().parents[2] / "alembic" / "versions" / "b3c4d5e6f7a8_include_age_snapshot_input_hash.py"
)


async def _seed_child_roots(db_session: AsyncSession) -> tuple[User, PersonProfile, NatalChart, ChildProfile]:
    owner = User(
        email=f"child-age-{uuid4()}@example.com",
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
        birth_datetime_utc=datetime(1990, 1, 1, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.7558,
        longitude=37.6173,
        house_system="P",
        calculation_payload={},
    )
    db_session.add(parent_chart)
    await db_session.flush()
    child = ChildProfile(
        owner_user_id=owner.id,
        parent_profile_id=parent_profile.id,
        display_name="Child",
        relationship_type="child",
        child_gender=None,
        birth_date=date(2021, 5, 12),
        birth_time=None,
        birth_time_confidence="unknown",
        birth_place="Moscow",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        caregiver_context={},
        birth_data_hash="a" * 64,
        idempotency_key=f"child-{uuid4()}",
        status="active",
        version=1,
    )
    db_session.add(child)
    await db_session.commit()
    return owner, parent_profile, parent_chart, child


@pytest.mark.asyncio
async def test_age_snapshot_is_server_derived_owner_scoped_and_concurrently_idempotent(
    db_session: AsyncSession,
) -> None:
    owner, _, _, child = await _seed_child_roots(db_session)
    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def persist() -> tuple[bool, UUID, str]:
        async with sessions() as session:
            result = await ChildRepository(session).create_age_snapshot_idempotently(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                now=datetime(2026, 5, 11, 21, 30, tzinfo=UTC),
                age_rules_version=AGE_RULES_VERSION,
            )
            await session.commit()
            return result.created, result.snapshot.id, result.snapshot.input_hash

    first, second = await asyncio.gather(persist(), persist())

    assert sorted([first[0], second[0]]) == [False, True]
    assert first[1] == second[1]
    assert (
        first[2]
        == second[2]
        == age_snapshot_input_hash(
            birth_date=child.birth_date,
            as_of_date=date(2026, 5, 12),
            age_rules_version=AGE_RULES_VERSION,
        )
    )

    repository = ChildRepository(db_session)
    listed = await repository.list_age_snapshots_for_owner(
        owner_user_id=owner.id,
        child_profile_id=child.id,
    )
    loaded = await repository.get_age_snapshot_for_owner(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        age_snapshot_id=first[1],
    )
    assert [row.id for row in listed] == [first[1]]
    assert loaded is not None and (loaded.age_years, loaded.age_months, loaded.age_days) == (5, 0, 0)

    foreign_owner = uuid4()
    assert (
        await repository.get_age_snapshot_for_owner(
            owner_user_id=foreign_owner,
            child_profile_id=child.id,
            age_snapshot_id=first[1],
        )
        is None
    )


@pytest.mark.asyncio
async def test_same_day_dob_correction_creates_distinct_snapshot_input_lineage(db_session: AsyncSession) -> None:
    owner, _, _, child = await _seed_child_roots(db_session)
    repository = ChildRepository(db_session)
    original = await repository.create_age_snapshot_idempotently(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        now=datetime(2026, 10, 16, 12, tzinfo=UTC),
    )
    await db_session.commit()

    persisted_child = await db_session.get(ChildProfile, child.id)
    assert persisted_child is not None
    persisted_child.birth_date = date(2021, 5, 13)
    persisted_child.birth_data_hash = "b" * 64
    persisted_child.version += 1
    await db_session.commit()

    corrected = await repository.create_age_snapshot_idempotently(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        now=datetime(2026, 10, 16, 12, tzinfo=UTC),
    )
    replay = await repository.create_age_snapshot_idempotently(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        now=datetime(2026, 10, 16, 12, tzinfo=UTC),
    )
    await db_session.commit()

    assert original.snapshot.id != corrected.snapshot.id
    assert original.snapshot.input_hash != corrected.snapshot.input_hash
    assert corrected.created is True
    assert replay.created is False
    assert replay.snapshot.id == corrected.snapshot.id
    rows = (
        (
            await db_session.execute(
                select(ChildAgeSnapshot)
                .where(ChildAgeSnapshot.child_profile_id == child.id)
                .order_by(ChildAgeSnapshot.created_at)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 2


async def _seed_report(
    db_session: AsyncSession,
) -> tuple[User, ChildProfile, ChildReport]:
    owner, _, parent_chart, child = await _seed_child_roots(db_session)
    chart = ChildChartVersion(
        child_profile_id=child.id,
        version=1,
        engine_version="child-chart-v1",
        input_hash="c" * 64,
        birth_time_confidence="unknown",
        allowed_fact_families=["planet_signs"],
        excluded_fact_families=["houses"],
        uncertainty_reason="unknown_time",
        calculation_payload={},
    )
    db_session.add(chart)
    await db_session.flush()
    repository = ChildRepository(db_session)
    generation = await repository.create_generation_idempotently(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        parent_chart_id=parent_chart.id,
        child_chart_version_id=chart.id,
        operation="create",
        idempotency_key="age-report-generation",
    )
    report = await repository.create_report_idempotently(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        generation_id=generation.generation.generation_id,
        parent_chart_id=parent_chart.id,
        child_chart_version_id=chart.id,
        idempotency_key="age-report",
        version=1,
        status="ready",
        scoring_version="score-v1",
        reference_version="reference-v1",
        questionnaire_version="questions-v1",
        prompt_version="prompt-v1",
        report_payload={"core": "immutable"},
        presentation_manifest={"sections": ["core"]},
    )
    await db_session.commit()
    return owner, child, report.report


@pytest.mark.asyncio
async def test_age_update_appends_guidance_and_shared_pin_without_mutating_core_report(
    db_session: AsyncSession,
) -> None:
    owner, child, report = await _seed_report(db_session)
    original_updated_at = report.updated_at
    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def persist_age_update() -> ChildAgeUpdateResult:
        async with sessions() as session:
            result = await ChildRepository(session).create_age_update_idempotently(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                report_id=report.id,
                now=datetime(2026, 10, 16, 12, tzinfo=UTC),
                idempotency_key="age-update-1",
                guidance_rules_version="age-guidance-v1",
                payload={"status": "pinned_only", "age_stage": "3-6"},
            )
            await session.commit()
            return result

    first_update, second_update = await asyncio.gather(persist_age_update(), persist_age_update())
    update = first_update if first_update.guidance_created else second_update
    replay = second_update if first_update.guidance_created else first_update

    assert sorted([first_update.snapshot_created, second_update.snapshot_created]) == [False, True]
    assert sorted([first_update.guidance_created, second_update.guidance_created]) == [False, True]
    assert replay.snapshot.id == update.snapshot.id
    assert replay.guidance.id == update.guidance.id

    repository = ChildRepository(db_session)

    persisted_report = await db_session.get(ChildReport, report.id)
    assert persisted_report is not None
    assert persisted_report.version == 1
    assert persisted_report.report_payload == {"core": "immutable"}
    assert persisted_report.presentation_manifest == {"sections": ["core"]}
    assert persisted_report.updated_at == original_updated_at

    web_pin = await repository.get_pinned_age_guidance_for_owner(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        report_id=report.id,
        age_snapshot_id=update.snapshot.id,
    )
    pdf_pin = await repository.get_pinned_age_guidance_for_owner(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        report_id=report.id,
        age_snapshot_id=update.snapshot.id,
    )
    assert web_pin == pdf_pin
    assert web_pin.age_snapshot.id == update.snapshot.id
    assert web_pin.core_report_version == 1

    sibling_owner, _, _, sibling = await _seed_child_roots(db_session)
    sibling_snapshot = await repository.create_age_snapshot_idempotently(
        owner_user_id=sibling_owner.id,
        child_profile_id=sibling.id,
        now=datetime(2026, 10, 16, 12, tzinfo=UTC),
    )
    await db_session.commit()
    with pytest.raises(ChildLineageMismatchError, match="snapshot"):
        await repository.get_pinned_age_guidance_for_owner(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            report_id=report.id,
            age_snapshot_id=sibling_snapshot.snapshot.id,
        )


@pytest.mark.asyncio
async def test_birth_correction_serializes_with_snapshot_creation_on_the_same_child_lock(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner, _, _, child = await _seed_child_roots(db_session)
    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    correction_has_lock = asyncio.Event()
    snapshot_attempted_lock = asyncio.Event()
    allow_correction = asyncio.Event()
    original_lock = ChildRepository._lock_child_lineage

    async def observed_lock(repository: ChildRepository, child_profile_id: UUID) -> None:
        if asyncio.current_task() is correction_task:
            await original_lock(repository, child_profile_id)
            correction_has_lock.set()
            await allow_correction.wait()
            return
        snapshot_attempted_lock.set()
        await original_lock(repository, child_profile_id)

    monkeypatch.setattr(ChildRepository, "_lock_child_lineage", observed_lock)
    corrected_input = ChildChartInput(
        birth_date=date(2021, 5, 13),
        birth_time=time(10, 30),
        birth_time_confidence="exact",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        house_system="P",
    )
    engine_version = "child-chart-race-test-1"
    corrected_chart = ChildChartBuild(
        engine_version=engine_version,
        input_hash=child_chart_input_hash(corrected_input, engine_version=engine_version),
        birth_time_confidence="exact",
        allowed_fact_families=("planet_signs",),
        excluded_fact_families=(),
        uncertainty_reason=None,
        calculation_payload={"contract_version": "child-birth-time-policy-v3"},
        source_input=corrected_input,
    )
    corrected_birth_hash = child_birth_data_hash(
        birth_date=corrected_input.birth_date,
        birth_time=corrected_input.birth_time,
        birth_time_confidence=corrected_input.birth_time_confidence,
        birth_place="Moscow",
        latitude=corrected_input.latitude,
        longitude=corrected_input.longitude,
        timezone=corrected_input.timezone,
    )

    async def correct_birth_data() -> None:
        async with sessions() as session:
            await ChildRepository(session).correct_birth_data_and_create_chart(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                birth_date=corrected_input.birth_date,
                birth_time=corrected_input.birth_time,
                birth_time_confidence=corrected_input.birth_time_confidence,
                birth_place="Moscow",
                latitude=corrected_input.latitude,
                longitude=corrected_input.longitude,
                timezone=corrected_input.timezone,
                house_system=corrected_input.house_system,
                birth_data_hash=corrected_birth_hash,
                chart=corrected_chart,
            )
            await session.commit()

    async def create_snapshot() -> ChildAgeSnapshot:
        async with sessions() as session:
            result = await ChildRepository(session).create_age_snapshot_idempotently(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                now=datetime(2026, 10, 16, 12, tzinfo=UTC),
            )
            await session.commit()
            return result.snapshot

    correction_task = asyncio.create_task(correct_birth_data())
    await correction_has_lock.wait()
    snapshot_task = asyncio.create_task(create_snapshot())
    await snapshot_attempted_lock.wait()
    assert not snapshot_task.done()
    allow_correction.set()
    await correction_task
    snapshot = await snapshot_task

    corrected_hash = age_snapshot_input_hash(
        birth_date=corrected_input.birth_date,
        as_of_date=date(2026, 10, 16),
        age_rules_version=AGE_RULES_VERSION,
    )
    old_hash = age_snapshot_input_hash(
        birth_date=child.birth_date,
        as_of_date=date(2026, 10, 16),
        age_rules_version=AGE_RULES_VERSION,
    )
    rows = (
        (await db_session.execute(select(ChildAgeSnapshot).where(ChildAgeSnapshot.child_profile_id == child.id)))
        .scalars()
        .all()
    )
    assert snapshot.input_hash == corrected_hash
    assert [row.input_hash for row in rows] == [corrected_hash]
    assert old_hash not in {row.input_hash for row in rows}


@pytest.mark.asyncio
async def test_age_snapshot_migration_downgrade_is_lossless_or_refuses_before_ddl(
    db_session: AsyncSession,
) -> None:
    owner, _, _, child = await _seed_child_roots(db_session)
    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    spec = importlib.util.spec_from_file_location("age_snapshot_migration_runtime", AGE_SNAPSHOT_MIGRATION)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    def downgrade(connection: Connection) -> None:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.downgrade()

    def upgrade(connection: Connection) -> None:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()

    async def constraint_exists(name: str) -> bool:
        async with engine.connect() as connection:
            return bool(
                await connection.scalar(
                    text(
                        "SELECT EXISTS ("
                        "SELECT 1 FROM pg_constraint "
                        "WHERE conrelid = 'child_age_snapshots'::regclass AND conname = :name)"
                    ),
                    {"name": name},
                )
            )

    async with engine.begin() as connection:
        await connection.run_sync(downgrade)
    assert await constraint_exists("uq_child_age_snapshots_profile_date_rules")
    async with engine.begin() as connection:
        await connection.run_sync(upgrade)

    repository = ChildRepository(db_session)
    first = await repository.create_age_snapshot_idempotently(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        now=datetime(2026, 10, 16, 12, tzinfo=UTC),
    )
    await db_session.commit()
    async with engine.begin() as connection:
        await connection.run_sync(downgrade)
    assert await constraint_exists("uq_child_age_snapshots_profile_date_rules")
    async with engine.begin() as connection:
        await connection.run_sync(upgrade)

    persisted_child = await db_session.get(ChildProfile, child.id)
    assert persisted_child is not None
    persisted_child.birth_date = date(2021, 5, 13)
    persisted_child.birth_data_hash = "b" * 64
    persisted_child.version += 1
    await db_session.commit()
    second = await repository.create_age_snapshot_idempotently(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        now=datetime(2026, 10, 16, 12, tzinfo=UTC),
    )
    await db_session.commit()
    assert first.snapshot.id != second.snapshot.id

    with pytest.raises(RuntimeError, match="Refusing lossy downgrade"):
        async with engine.begin() as connection:
            await connection.run_sync(downgrade)

    rows = (
        (await db_session.execute(select(ChildAgeSnapshot).where(ChildAgeSnapshot.child_profile_id == child.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 2
    assert await constraint_exists("uq_child_age_snapshots_profile_date_rules_input")
    assert not await constraint_exists("uq_child_age_snapshots_profile_date_rules")
