from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

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
