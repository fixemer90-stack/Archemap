from __future__ import annotations

import asyncio
import copy
import json
import os
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.modules.astrotype_v2.models import NatalChart, NatalFact, NatalFactEvidence
from app.modules.child.models import ChildChartVersion, ChildGeneration, ChildParentStyleScore, ChildProfile
from app.modules.child.repository import ChildLineageMismatchError, ChildRepository
from app.modules.child.scoring.types import ParentStyleDimension
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

    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    def run_alembic(*args: str, succeeds: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["DATABASE_URL"] = engine.url.render_as_string(hide_password=False)
        result = subprocess.run(  # noqa: S603 - fixed interpreter/module and test-owned Alembic arguments
            [sys.executable, "-m", "alembic", *args],
            cwd=Path(__file__).resolve().parents[2],
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        assert (result.returncode == 0) is succeeds, result.stdout + result.stderr
        return result

    async def constraint_exists(name: str) -> bool:
        async with engine.connect() as connection:
            return bool(
                await connection.scalar(
                    text(
                        "SELECT EXISTS ("
                        "SELECT 1 FROM pg_constraint "
                        "WHERE conrelid = 'child_parent_style_scores'::regclass AND conname = :name)"
                    ),
                    {"name": name},
                )
            )

    async with engine.begin() as connection:
        await connection.execute(
            text(
                "ALTER TABLE child_parent_style_scores "
                "DROP CONSTRAINT uq_child_parent_style_generation_dimension_version"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE child_parent_style_scores "
                "ADD CONSTRAINT uq_child_parent_style_generation_dimension UNIQUE (generation_id, dimension)"
            )
        )
    run_alembic("stamp", "b3c4d5e6f7a8")
    run_alembic("upgrade", "c4d5e6f7a8b9")
    assert await constraint_exists("uq_child_parent_style_generation_dimension_version")
    run_alembic("downgrade", "b3c4d5e6f7a8")
    assert await constraint_exists("uq_child_parent_style_generation_dimension")
    run_alembic("upgrade", "c4d5e6f7a8b9")
    assert await constraint_exists("uq_child_parent_style_generation_dimension_version")

    db_session.add_all(
        [
            ChildParentStyleScore(
                child_profile_id=child.id,
                parent_chart_id=parent_chart.id,
                generation_id=generation_id,
                dimension=dimension.value,
                score=50.0,
                confidence=0.0,
                scoring_version="parent-style-mvp-1",
                breakdown={},
                evidence_refs=[],
            )
            for dimension in ParentStyleDimension
        ]
    )
    await db_session.commit()

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

    assert persisted_count == 16
    assert tuple(row.id for row in loaded.scores) == first[1]
    assert _score_snapshot(loaded.scores) == first[2] == second[2]
    assert loaded.parent_chart_id == parent_chart.id
    assert loaded.generation_id == generation_id

    failed_downgrade = run_alembic("downgrade", "b3c4d5e6f7a8", succeeds=False)
    assert "Refusing lossy downgrade" in failed_downgrade.stderr
    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "c4d5e6f7a8b9"
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM child_parent_style_scores WHERE generation_id = :generation_id"),
                {"generation_id": generation_id},
            )
            == 16
        )
    assert await constraint_exists("uq_child_parent_style_generation_dimension_version")
    assert not await constraint_exists("uq_child_parent_style_generation_dimension")

    invalid_generation_id = uuid4()
    async with session_factory() as invalid_session:
        invalid_session.add(
            ChildGeneration(
                child_profile_id=child.id,
                owner_user_id=owner.id,
                parent_chart_id=parent_chart.id,
                child_chart_version_id=child_chart.id,
                generation_id=invalid_generation_id,
                operation="create",
                idempotency_key="parent-style-invalid-numeric-generation",
                status="deterministic_pending",
                diagnostics={},
            )
        )
        invalid_evidence = (
            await invalid_session.execute(
                select(NatalFactEvidence).where(NatalFactEvidence.chart_id == parent_chart.id).limit(1)
            )
        ).scalar_one()
        invalid_evidence.payload = {"source_quality": -0.1}
        await invalid_session.flush()
        with pytest.raises(ValueError, match="source_quality"):
            await ChildRepository(invalid_session).create_parent_style_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=invalid_generation_id,
            )
        await invalid_session.commit()
        assert (
            await invalid_session.scalar(
                select(func.count())
                .select_from(ChildParentStyleScore)
                .where(ChildParentStyleScore.generation_id == invalid_generation_id)
            )
            == 0
        )
        invalid_evidence.payload = {"source_quality": 1.0}
        await invalid_session.commit()

    async with session_factory() as corrupt_session:
        first_score_id, original_dimension, original_breakdown = (
            await corrupt_session.execute(
                select(ChildParentStyleScore.id, ChildParentStyleScore.dimension, ChildParentStyleScore.breakdown)
                .where(
                    ChildParentStyleScore.generation_id == generation_id,
                    ChildParentStyleScore.scoring_version == "parent-style-mvp-2",
                )
                .order_by(ChildParentStyleScore.dimension)
                .limit(1)
            )
        ).one()
        await corrupt_session.execute(
            text("UPDATE child_parent_style_scores SET dimension = :dimension WHERE id = :row_id"),
            {"dimension": "unexpected_current_dimension", "row_id": first_score_id},
        )
        await corrupt_session.commit()

    async with session_factory() as corrupt_load_session:
        with pytest.raises(ChildLineageMismatchError, match="incomplete or not canonically ordered"):
            await ChildRepository(corrupt_load_session).load_parent_style_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=generation_id,
            )

    supports_string = cast(dict[str, Any], copy.deepcopy(original_breakdown))
    supports_string["supports"] = "not-a-list"
    bad_confidence_component = cast(dict[str, Any], copy.deepcopy(original_breakdown))
    bad_confidence_component["confidence_components"]["coverage"] = 1.1
    malformed_nested_refs = cast(dict[str, Any], copy.deepcopy(original_breakdown))
    malformed_nested_refs["independent_lineage_refs"] = ["source:one", 7]
    arbitrary_scale = cast(dict[str, Any], copy.deepcopy(original_breakdown))
    arbitrary_scale["scale"] = {"zero": "copied", "hundred": "copied", "neutral": "copied"}
    contradictory_count = cast(dict[str, Any], copy.deepcopy(original_breakdown))
    contradictory_count["required_family_count"] = 1
    duplicate_lineage_ref = cast(dict[str, Any], copy.deepcopy(original_breakdown))
    duplicate_lineage_ref["independent_lineage_refs"].append(duplicate_lineage_ref["independent_lineage_refs"][0])
    empty_nested_refs = cast(dict[str, Any], copy.deepcopy(original_breakdown))
    empty_nested_refs["supports"][0]["evidence_refs"] = []
    corruptions = (
        supports_string,
        bad_confidence_component,
        malformed_nested_refs,
        arbitrary_scale,
        contradictory_count,
        duplicate_lineage_ref,
        empty_nested_refs,
    )
    for malformed in corruptions:
        async with session_factory() as corrupt_session:
            await corrupt_session.execute(
                text(
                    "UPDATE child_parent_style_scores "
                    "SET dimension = :dimension, breakdown = CAST(:breakdown AS jsonb) WHERE id = :row_id"
                ),
                {
                    "dimension": original_dimension,
                    "breakdown": json.dumps(malformed),
                    "row_id": first_score_id,
                },
            )
            await corrupt_session.commit()

        async with session_factory() as corrupt_load_session:
            with pytest.raises(ChildLineageMismatchError, match="breakdown"):
                await ChildRepository(corrupt_load_session).load_parent_style_profile(
                    owner_user_id=owner.id,
                    child_profile_id=child.id,
                    generation_id=generation_id,
                )

    async with session_factory() as cleanup_session:
        await cleanup_session.execute(
            text("UPDATE child_parent_style_scores SET breakdown = CAST(:breakdown AS jsonb) WHERE id = :row_id"),
            {"breakdown": json.dumps(original_breakdown), "row_id": first_score_id},
        )
        await cleanup_session.execute(text("DROP TABLE alembic_version"))
        await cleanup_session.commit()

    async with session_factory() as foreign_session:
        with pytest.raises(ChildLineageMismatchError, match="not owned"):
            await ChildRepository(foreign_session).load_parent_style_profile(
                owner_user_id=intruder.id,
                child_profile_id=child.id,
                generation_id=generation_id,
            )
