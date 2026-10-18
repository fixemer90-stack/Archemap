from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint, func, inspect, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.infrastructure.database import Base
from app.modules.astrotype_v2.models import (
    NatalChart,
    NatalFact,
    NatalFactEvidence,
    NatalHouse,
    NatalPlanetPosition,
)
from app.modules.child.models import (
    ChildChartVersion,
    ChildGeneration,
    ChildInteractionScore,
    ChildParentStyleScore,
    ChildProfile,
    ChildSynastryEvidence,
)
from app.modules.child.repository import (
    ChildLineageMismatchError,
    ChildRepository,
    InteractionProfilePersistenceResult,
    PersistedInteractionProfile,
)
from app.modules.child.scoring.types import InteractionDimension
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User
from tests.integration.test_child_needs import _payload

pytestmark = pytest.mark.usefixtures("_setup_database")
_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _run_alembic(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed interpreter/module and test-owned arguments
        [sys.executable, "-m", "alembic", *args],
        cwd=_BACKEND_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


async def _seed_pair(db_session: AsyncSession) -> tuple[User, ChildProfile, ChildGeneration]:
    owner = User(
        email=f"interaction-{uuid4()}@example.com",
        name="Parent",
        hashed_password="test-only-hash",  # noqa: S106
        is_active=True,
        is_verified=True,
    )
    db_session.add(owner)
    await db_session.flush()
    profile = PersonProfile(
        user_id=owner.id,
        name="Parent",
        birth_date=date(1990, 1, 1),
        birth_time=None,
        birth_time_accuracy="exact",
        birth_place="Moscow",
        latitude=55.7,
        longitude=37.6,
        timezone="Europe/Moscow",
    )
    db_session.add(profile)
    await db_session.flush()
    parent_chart = NatalChart(
        user_id=owner.id,
        profile_id=profile.id,
        engine_version="0.1.6",
        input_hash="p" * 64,
        birth_datetime_utc=datetime(1990, 1, 1, 9, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.7,
        longitude=37.6,
        house_system="P",
        calculation_payload={
            "birth_time_proof": {
                "contract_version": "natal-timing-proof-v1",
                "birth_time_confidence": "exact",
                "user_supplied_time": True,
                "synthetic_noon": False,
            }
        },
    )
    db_session.add(parent_chart)
    await db_session.flush()
    bodies = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus")
    db_session.add_all(
        [
            NatalPlanetPosition(
                chart_id=parent_chart.id,
                body=body,
                longitude=float(index * 30 + 1),
                latitude=0.0,
                speed=1.0,
                sign="Aries",
                sign_degree=1.0,
                house_number=index,
                retrograde=False,
            )
            for index, body in enumerate(bodies, start=1)
        ]
        + [
            NatalHouse(
                chart_id=parent_chart.id,
                house_number=number,
                longitude=float((number - 1) * 30),
                sign="Aries",
            )
            for number in range(1, 13)
        ]
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
            summary="not used",
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
                source_id=fact.id,
                source_key=key,
                payload={"source_quality": 1.0},
            )
        )
    child = ChildProfile(
        owner_user_id=owner.id,
        parent_profile_id=profile.id,
        display_name="Child",
        relationship_type="child",
        child_gender=None,
        birth_date=date(2021, 5, 12),
        birth_time=None,
        birth_time_confidence="exact",
        birth_place="Moscow",
        latitude=55.7,
        longitude=37.6,
        timezone="Europe/Moscow",
        caregiver_context={"must_not_be_read": True},
        birth_data_hash="c" * 64,
        idempotency_key=f"child-{uuid4()}",
        status="active",
        version=1,
    )
    db_session.add(child)
    await db_session.flush()
    child_payload = _payload()
    child_payload["houses"] = [
        {"house_number": number, "longitude": float((number - 1) * 30), "sign": "Aries"} for number in range(1, 13)
    ]
    child_chart = ChildChartVersion(
        child_profile_id=child.id,
        version=1,
        engine_version="0.1.6",
        input_hash="d" * 64,
        birth_time_confidence="exact",
        allowed_fact_families=[
            "planet_positions",
            "planet_signs",
            "moon_sign",
            "aspects",
            "houses",
            "angles",
            "house_assignments",
            "house_overlays",
        ],
        excluded_fact_families=[],
        uncertainty_reason=None,
        calculation_payload=child_payload,
    )
    db_session.add(child_chart)
    await db_session.flush()
    generation = ChildGeneration(
        child_profile_id=child.id,
        owner_user_id=owner.id,
        parent_chart_id=parent_chart.id,
        child_chart_version_id=child_chart.id,
        generation_id=uuid4(),
        operation="create",
        idempotency_key=f"generation-{uuid4()}",
        status="deterministic_pending",
        diagnostics={},
    )
    db_session.add(generation)
    await db_session.commit()
    return owner, child, generation


async def _persist_interaction(
    session: AsyncSession,
) -> tuple[User, ChildProfile, ChildGeneration, InteractionProfilePersistenceResult]:
    owner, child, generation = await _seed_pair(session)
    repository = ChildRepository(session)
    await repository.create_parent_style_profile(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        generation_id=generation.generation_id,
    )
    await repository.create_child_need_profile(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        generation_id=generation.generation_id,
    )
    result = await repository.create_interaction_profile(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        generation_id=generation.generation_id,
    )
    await session.commit()
    return owner, child, generation, result


def _snapshot(
    result: InteractionProfilePersistenceResult | PersistedInteractionProfile,
) -> tuple[object, ...]:
    evidence = result.evidence
    scores = result.scores
    return (
        tuple((row.id, row.source_key, row.reference_version, row.contribution, row.payload) for row in evidence),
        tuple((row.id, row.dimension, row.score, row.confidence, row.pattern, row.breakdown) for row in scores),
    )


@pytest.mark.asyncio
async def test_interaction_repository_concurrency_reload_versions_and_atomic_corruption(
    db_session: AsyncSession,
) -> None:
    owner, child, generation = await _seed_pair(db_session)
    await ChildRepository(db_session).create_parent_style_profile(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        generation_id=generation.generation_id,
    )
    await ChildRepository(db_session).create_child_need_profile(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        generation_id=generation.generation_id,
    )
    await db_session.commit()
    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def create_same() -> tuple[bool, tuple[object, ...]]:
        async with sessions() as session:
            result = await ChildRepository(session).create_interaction_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=generation.generation_id,
            )
            await session.commit()
            return result.created, _snapshot(result)

    first, second = await asyncio.gather(create_same(), create_same())
    assert sorted((first[0], second[0])) == [False, True]
    assert first[1] == second[1]

    async with sessions() as session:
        loaded = await ChildRepository(session).load_interaction_profile(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            generation_id=generation.generation_id,
        )
        assert _snapshot(loaded) == first[1]
        assert tuple(row.dimension for row in loaded.scores) == tuple(d.value for d in InteractionDimension)
        assert all(row.parent_chart_id == generation.parent_chart_id for row in loaded.scores)
        assert all(row.child_chart_version_id == generation.child_chart_version_id for row in loaded.scores)
        assert any(row.source_type == "house_overlay" for row in loaded.evidence)
        session.add_all(
            [
                ChildInteractionScore(
                    child_profile_id=child.id,
                    parent_chart_id=generation.parent_chart_id,
                    child_chart_version_id=generation.child_chart_version_id,
                    generation_id=generation.generation_id,
                    dimension=dimension.value,
                    score=50.0,
                    confidence=0.0,
                    pattern="moderate_tension",
                    scoring_version="child-interaction-mvp-0",
                    evidence_refs=[],
                    breakdown={},
                )
                for dimension in InteractionDimension
            ]
        )
        session.add(
            ChildSynastryEvidence(
                child_profile_id=child.id,
                parent_chart_id=generation.parent_chart_id,
                child_chart_version_id=generation.child_chart_version_id,
                generation_id=generation.generation_id,
                source_type="legacy",
                source_key="legacy-source",
                reference_version="child-synastry-reference-0",
                contribution=0.0,
                direction="supports",
                payload={},
            )
        )
        await session.commit()
        assert (
            await session.scalar(
                select(func.count())
                .select_from(ChildInteractionScore)
                .where(ChildInteractionScore.generation_id == generation.generation_id)
            )
            == 16
        )
        env = os.environ.copy()
        env["DATABASE_URL"] = engine.url.render_as_string(hide_password=False)
        stamp = await asyncio.to_thread(_run_alembic, env, "stamp", "e6f7a8b9c0d1")
        assert stamp.returncode == 0, stamp.stdout + stamp.stderr
        downgrade = await asyncio.to_thread(_run_alembic, env, "downgrade", "d5e6f7a8b9c0")
        assert downgrade.returncode != 0
        assert "Refusing lossy downgrade" in downgrade.stdout + downgrade.stderr
        assert await session.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_constraint "
                "WHERE conrelid = 'child_interaction_scores'::regclass "
                "AND conname = 'uq_child_interaction_generation_dimension_version')"
            )
        )

        sibling = ChildProfile(
            owner_user_id=owner.id,
            parent_profile_id=child.parent_profile_id,
            display_name="Sibling",
            relationship_type="child",
            child_gender=None,
            birth_date=date(2022, 6, 13),
            birth_time=None,
            birth_time_confidence="exact",
            birth_place="Moscow",
            latitude=55.7,
            longitude=37.6,
            timezone="Europe/Moscow",
            caregiver_context={},
            birth_data_hash="s" * 64,
            idempotency_key=f"sibling-{uuid4()}",
            status="active",
            version=1,
        )
        session.add(sibling)
        await session.flush()
        sibling_chart = ChildChartVersion(
            child_profile_id=sibling.id,
            version=1,
            engine_version="0.1.6",
            input_hash="e" * 64,
            birth_time_confidence="exact",
            allowed_fact_families=[
                "planet_positions",
                "planet_signs",
                "moon_sign",
                "aspects",
                "houses",
                "angles",
                "house_assignments",
                "house_overlays",
            ],
            excluded_fact_families=[],
            uncertainty_reason=None,
            calculation_payload=_payload(),
        )
        session.add(sibling_chart)
        await session.flush()
        sibling_generation = ChildGeneration(
            child_profile_id=sibling.id,
            owner_user_id=owner.id,
            parent_chart_id=generation.parent_chart_id,
            child_chart_version_id=sibling_chart.id,
            generation_id=uuid4(),
            operation="create",
            idempotency_key=f"sibling-generation-{uuid4()}",
            status="deterministic_pending",
            diagnostics={},
        )
        session.add(sibling_generation)
        await session.commit()
        repository = ChildRepository(session)
        await repository.create_parent_style_profile(
            owner_user_id=owner.id,
            child_profile_id=sibling.id,
            generation_id=sibling_generation.generation_id,
        )
        await repository.create_child_need_profile(
            owner_user_id=owner.id,
            child_profile_id=sibling.id,
            generation_id=sibling_generation.generation_id,
        )
        sibling_result = await repository.create_interaction_profile(
            owner_user_id=owner.id,
            child_profile_id=sibling.id,
            generation_id=sibling_generation.generation_id,
        )
        await session.commit()
        assert {row.id for row in loaded.evidence}.isdisjoint(row.id for row in sibling_result.evidence)
        assert {row.id for row in loaded.scores}.isdisjoint(row.id for row in sibling_result.scores)

    async with sessions() as session:
        with pytest.raises(ChildLineageMismatchError, match="not owned"):
            await ChildRepository(session).load_interaction_profile(
                owner_user_id=uuid4(),
                child_profile_id=child.id,
                generation_id=generation.generation_id,
            )
        with pytest.raises(ChildLineageMismatchError, match="does not belong"):
            await ChildRepository(session).create_interaction_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=uuid4(),
            )
        await session.commit()

    async with sessions() as session:
        row = await session.scalar(
            select(ChildInteractionScore).where(
                ChildInteractionScore.generation_id == generation.generation_id,
                ChildInteractionScore.scoring_version == "child-interaction-mvp-1",
            )
        )
        assert row is not None
        corrupted_id = row.id
        await session.execute(
            text(
                "UPDATE child_interaction_scores "
                "SET breakdown = jsonb_set(breakdown, '{raw_delta}', '0.999'::jsonb) "
                "WHERE id = :row_id"
            ),
            {"row_id": corrupted_id},
        )
        await session.commit()

    async with sessions() as session:
        with pytest.raises(ChildLineageMismatchError, match="raw delta"):
            await ChildRepository(session).load_interaction_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=generation.generation_id,
            )
        await session.commit()
        persisted = await session.scalar(
            select(ChildInteractionScore).where(
                ChildInteractionScore.generation_id == generation.generation_id,
                ChildInteractionScore.scoring_version == "child-interaction-mvp-1",
                ChildInteractionScore.id == corrupted_id,
            )
        )
        assert persisted is not None
        assert persisted.breakdown["raw_delta"] == 0.999


@pytest.mark.asyncio
async def test_reload_uses_fresh_database_values_after_identity_map_preload(db_session: AsyncSession) -> None:
    owner, child, generation, _ = await _persist_interaction(db_session)
    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sessions() as session_a:
        repository = ChildRepository(session_a)
        preloaded = await repository.load_interaction_profile(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            generation_id=generation.generation_id,
        )
        score_id = preloaded.scores[0].id
        evidence_id = preloaded.evidence[0].id
        await session_a.commit()

        async with sessions() as session_b:
            await session_b.execute(
                text(
                    "UPDATE child_interaction_scores "
                    "SET breakdown = jsonb_set(breakdown, '{raw_delta}', '0.777'::jsonb) "
                    "WHERE id = :score_id"
                ),
                {"score_id": score_id},
            )
            await session_b.execute(
                text("UPDATE child_synastry_evidence SET contribution = contribution / 2 WHERE id = :evidence_id"),
                {"evidence_id": evidence_id},
            )
            await session_b.commit()

        with pytest.raises(ChildLineageMismatchError):
            await repository.load_interaction_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=generation.generation_id,
            )


@pytest.mark.asyncio
async def test_reload_rejects_exact_evidence_after_parent_timing_becomes_unknown(db_session: AsyncSession) -> None:
    owner, child, generation, created = await _persist_interaction(db_session)
    assert any(row.source_type in {"angle_aspect", "house_overlay"} for row in created.evidence)
    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sessions() as session_a:
        repository = ChildRepository(session_a)
        await repository.load_interaction_profile(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            generation_id=generation.generation_id,
        )
        await session_a.commit()

        async with sessions() as session_b:
            await session_b.execute(
                text(
                    "UPDATE astrotype_v2_natal_charts "
                    "SET calculation_payload = jsonb_set("
                    "jsonb_set(jsonb_set(calculation_payload, "
                    "'{birth_time_proof,birth_time_confidence}', '\"unknown\"'::jsonb), "
                    "'{birth_time_proof,user_supplied_time}', 'false'::jsonb), "
                    "'{birth_time_proof,synthetic_noon}', 'true'::jsonb) "
                    "WHERE id = :chart_id"
                ),
                {"chart_id": generation.parent_chart_id},
            )
            await session_b.commit()

        with pytest.raises(ChildLineageMismatchError, match="pinned chart source state"):
            await repository.load_interaction_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=generation.generation_id,
            )


@pytest.mark.asyncio
async def test_reload_locks_exact_owned_child_route_before_reading_parent_profile(
    db_session: AsyncSession,
) -> None:
    owner, child, generation, _ = await _persist_interaction(db_session)
    alternate_parent = PersonProfile(
        user_id=owner.id,
        name="Alternate Parent",
        birth_date=date(1991, 2, 2),
        birth_time=None,
        birth_time_accuracy="exact",
        birth_place="Moscow",
        latitude=55.7,
        longitude=37.6,
        timezone="Europe/Moscow",
    )
    sibling = ChildProfile(
        owner_user_id=owner.id,
        parent_profile_id=child.parent_profile_id,
        display_name="Sibling",
        relationship_type="child",
        child_gender=None,
        birth_date=date(2022, 6, 13),
        birth_time=None,
        birth_time_confidence="exact",
        birth_place="Moscow",
        latitude=55.7,
        longitude=37.6,
        timezone="Europe/Moscow",
        caregiver_context={},
        birth_data_hash="s" * 64,
        idempotency_key=f"routing-lock-sibling-{uuid4()}",
        status="active",
        version=1,
    )
    db_session.add_all([alternate_parent, sibling])
    await db_session.commit()

    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with (
        sessions() as loader,
        sessions() as target_updater,
        sessions() as sibling_updater,
        sessions() as observer,
    ):
        loader_pid = await loader.scalar(text("SELECT pg_backend_pid()"))
        updater_pid = await target_updater.scalar(text("SELECT pg_backend_pid()"))
        assert isinstance(loader_pid, int)
        assert isinstance(updater_pid, int)

        loaded = await ChildRepository(loader).load_interaction_profile(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            generation_id=generation.generation_id,
        )
        update_started = asyncio.Event()

        async def update_target_route() -> None:
            await target_updater.execute(text("SET LOCAL lock_timeout = '15s'"))
            update_started.set()
            await target_updater.execute(
                text("UPDATE child_profiles SET parent_profile_id = :parent_id WHERE id = :child_id"),
                {"parent_id": alternate_parent.id, "child_id": child.id},
            )
            await target_updater.commit()

        update_task = asyncio.create_task(update_target_route())
        await update_started.wait()
        blocked_by_loader = False
        async with asyncio.timeout(5):
            while not blocked_by_loader:
                blockers = await observer.scalar(
                    text("SELECT pg_blocking_pids(:updater_pid)"), {"updater_pid": updater_pid}
                )
                blocked_by_loader = isinstance(blockers, list) and loader_pid in blockers

        assert not update_task.done()
        await sibling_updater.execute(text("SET LOCAL lock_timeout = '1s'"))
        await sibling_updater.execute(
            text("UPDATE child_profiles SET parent_profile_id = :parent_id WHERE id = :child_id"),
            {"parent_id": alternate_parent.id, "child_id": sibling.id},
        )
        await sibling_updater.commit()
        assert tuple(row.dimension for row in loaded.scores) == tuple(d.value for d in InteractionDimension)

        await loader.commit()
        await update_task

    async with sessions() as fresh:
        assert await fresh.scalar(select(ChildProfile.parent_profile_id).where(ChildProfile.id == sibling.id)) == (
            alternate_parent.id
        )
        with pytest.raises(ChildLineageMismatchError, match="pinned chart lineage"):
            await ChildRepository(fresh).load_interaction_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=generation.generation_id,
            )


@pytest.mark.asyncio
async def test_reload_holds_shared_source_locks_until_validation_transaction_ends(
    db_session: AsyncSession,
) -> None:
    owner, child, generation, _ = await _persist_interaction(db_session)
    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sessions() as loader, sessions() as updater, sessions() as observer:
        loader_pid = await loader.scalar(text("SELECT pg_backend_pid()"))
        updater_pid = await updater.scalar(text("SELECT pg_backend_pid()"))
        assert isinstance(loader_pid, int)
        assert isinstance(updater_pid, int)

        loaded = await ChildRepository(loader).load_interaction_profile(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            generation_id=generation.generation_id,
        )
        parent_score_id = await observer.scalar(
            select(ChildParentStyleScore.id).where(ChildParentStyleScore.generation_id == generation.generation_id)
        )
        assert parent_score_id is not None

        update_started = asyncio.Event()

        async def update_parent_score() -> None:
            await updater.execute(text("SET LOCAL lock_timeout = '15s'"))
            update_started.set()
            await updater.execute(
                text("UPDATE child_parent_style_scores SET score = score + 1 WHERE id = :score_id"),
                {"score_id": parent_score_id},
            )
            await updater.commit()

        update_task = asyncio.create_task(update_parent_score())
        await update_started.wait()
        blocked_by_loader = False
        async with asyncio.timeout(5):
            while not blocked_by_loader:
                blockers = await observer.scalar(
                    text("SELECT pg_blocking_pids(:updater_pid)"), {"updater_pid": updater_pid}
                )
                blocked_by_loader = isinstance(blockers, list) and loader_pid in blockers

        assert not update_task.done()
        assert tuple(row.dimension for row in loaded.scores) == tuple(d.value for d in InteractionDimension)
        await loader.commit()
        await update_task

    async with sessions() as fresh:
        with pytest.raises(ChildLineageMismatchError):
            await ChildRepository(fresh).load_interaction_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=generation.generation_id,
            )


def _s07_schema_snapshot(sync_connection: Connection) -> dict[str, object]:
    inspector = inspect(sync_connection)
    snapshot: dict[str, object] = {}
    for table_name in ("child_synastry_evidence", "child_interaction_scores"):
        table = Base.metadata.tables[table_name]
        actual_foreign_keys = {
            (
                tuple(item["constrained_columns"]),
                item["referred_table"],
                tuple(item["referred_columns"]),
            )
            for item in inspector.get_foreign_keys(table_name)
        }
        expected_foreign_keys = {
            (
                tuple(column.name for column in constraint.columns),
                next(iter(constraint.elements)).column.table.name,
                tuple(element.column.name for element in constraint.elements),
            )
            for constraint in table.constraints
            if isinstance(constraint, ForeignKeyConstraint)
        }
        actual_uniques = {
            (item["name"], tuple(item["column_names"])) for item in inspector.get_unique_constraints(table_name)
        }
        expected_uniques = {
            (constraint.name, tuple(column.name for column in constraint.columns))
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        actual_checks = {item["name"] for item in inspector.get_check_constraints(table_name)}
        expected_checks = {
            constraint.name for constraint in table.constraints if isinstance(constraint, CheckConstraint)
        }
        actual_unique_names = {name for name, _columns in actual_uniques}
        actual_indexes = {
            (item["name"], tuple(item["column_names"]), item["unique"])
            for item in inspector.get_indexes(table_name)
            if item["name"] not in actual_unique_names
        }
        expected_indexes = {
            (index.name, tuple(column.name for column in index.columns), index.unique) for index in table.indexes
        }
        snapshot[table_name] = {
            "columns": ({item["name"] for item in inspector.get_columns(table_name)}, set(table.columns.keys())),
            "foreign_keys": (actual_foreign_keys, expected_foreign_keys),
            "uniques": (actual_uniques, expected_uniques),
            "checks": (actual_checks, expected_checks),
            "indexes": (actual_indexes, expected_indexes),
        }
    return snapshot


@pytest.mark.asyncio
async def test_e6_real_d5_upgrade_downgrade_reupgrade_and_schema_parity(db_session: AsyncSession) -> None:
    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
    env = os.environ.copy()
    env["DATABASE_URL"] = engine.url.render_as_string(hide_password=False)

    upgrade_d5 = await asyncio.to_thread(_run_alembic, env, "upgrade", "d5e6f7a8b9c0")
    assert upgrade_d5.returncode == 0, upgrade_d5.stdout + upgrade_d5.stderr
    upgrade_e6 = await asyncio.to_thread(_run_alembic, env, "upgrade", "e6f7a8b9c0d1")
    assert upgrade_e6.returncode == 0, upgrade_e6.stdout + upgrade_e6.stderr
    async with engine.connect() as connection:
        schema = await connection.run_sync(_s07_schema_snapshot)
        direct_fk = await connection.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_constraint "
                "WHERE conrelid = 'child_interaction_scores'::regclass "
                "AND conname = 'fk_child_interaction_child_chart_version')"
            )
        )
    assert direct_fk is True
    for table_snapshot in schema.values():
        assert isinstance(table_snapshot, dict)
        for actual, expected in table_snapshot.values():
            assert actual == expected

    downgrade = await asyncio.to_thread(_run_alembic, env, "downgrade", "d5e6f7a8b9c0")
    assert downgrade.returncode == 0, downgrade.stdout + downgrade.stderr
    reupgrade = await asyncio.to_thread(_run_alembic, env, "upgrade", "e6f7a8b9c0d1")
    assert reupgrade.returncode == 0, reupgrade.stdout + reupgrade.stderr
    async with engine.connect() as connection:
        reupgraded_schema = await connection.run_sync(_s07_schema_snapshot)
    assert reupgraded_schema == schema
