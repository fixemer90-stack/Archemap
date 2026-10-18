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

from app.modules.astrotype_v2.models import NatalChart
from app.modules.child.models import ChildChartVersion, ChildGeneration, ChildNeedScore, ChildProfile
from app.modules.child.repository import ChildLineageMismatchError, ChildRepository
from app.modules.child.scoring.types import ChildNeedDimension
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User

pytestmark = pytest.mark.usefixtures("_setup_database")


def _payload() -> dict[str, object]:
    positions = [
        ("Sun", "Leo", 5),
        ("Moon", "Cancer", 4),
        ("Mercury", "Gemini", 3),
        ("Venus", "Libra", 7),
        ("Mars", "Aries", 1),
        ("Jupiter", "Sagittarius", 9),
        ("Saturn", "Capricorn", 10),
        ("Uranus", "Aquarius", 11),
    ]
    return {
        "contract_version": "child-birth-time-policy-v3",
        "technical_reference": {
            "birth_datetime_utc": "2021-05-12T07:00:00+00:00",
            "synthetic_noon": False,
            "user_supplied_time": True,
            "birth_time_confidence": "exact",
        },
        "planet_positions": [
            {
                "body": body,
                "sign": sign,
                "house_number": house,
                "longitude": 1.0,
                "latitude": 0.0,
                "speed": 1.0,
                "sign_degree": 1.0,
                "retrograde": False,
            }
            for body, sign, house in positions
        ],
        "houses": [],
        "aspects": [
            {
                "body_a": "Moon",
                "body_b": "Venus",
                "aspect_code": "trine",
                "angle_degrees": 120.0,
                "orb_degrees": 1.0,
                "applying": True,
            }
        ],
        "stability_evidence": {
            "policy_version": "child-birth-time-policy-v3",
            "exact_input": True,
            "confidence": 1.0,
        },
        "exclusions": [],
    }


def _snapshot(rows: tuple[ChildNeedScore, ...]) -> list[tuple[object, ...]]:
    return [
        (row.dimension, row.score, row.confidence, row.scoring_version, row.evidence_refs, row.breakdown)
        for row in rows
    ]


@pytest.mark.asyncio
async def test_child_needs_persist_reload_concurrency_versions_and_corruption(
    db_session: AsyncSession,
) -> None:
    owner = User(
        email=f"child-needs-{uuid4()}@example.com",
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
        calculation_payload={},
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
        caregiver_context={"must_not_be_read": True},
        birth_data_hash="c" * 64,
        idempotency_key="child-needs-child",
        status="active",
        version=1,
    )
    db_session.add(child)
    await db_session.flush()
    chart = ChildChartVersion(
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
        calculation_payload=_payload(),
    )
    db_session.add(chart)
    await db_session.flush()
    generation_id = uuid4()
    db_session.add(
        ChildGeneration(
            child_profile_id=child.id,
            owner_user_id=owner.id,
            parent_chart_id=parent_chart.id,
            child_chart_version_id=chart.id,
            generation_id=generation_id,
            operation="create",
            idempotency_key="child-needs-generation",
            status="deterministic_pending",
            diagnostics={},
        )
    )
    await db_session.commit()

    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    def run_alembic(*args: str, succeeds: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["DATABASE_URL"] = engine.url.render_as_string(hide_password=False)
        result = subprocess.run(  # noqa: S603
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
                        "WHERE conrelid = 'child_need_scores'::regclass AND conname = :name)"
                    ),
                    {"name": name},
                )
            )

    async with engine.begin() as connection:
        await connection.execute(
            text("ALTER TABLE child_need_scores DROP CONSTRAINT uq_child_need_generation_dimension_version")
        )
        await connection.execute(
            text(
                "ALTER TABLE child_need_scores ADD CONSTRAINT uq_child_need_generation_dimension "
                "UNIQUE (generation_id, dimension)"
            )
        )
    run_alembic("stamp", "c4d5e6f7a8b9")
    run_alembic("upgrade", "d5e6f7a8b9c0")
    assert await constraint_exists("uq_child_need_generation_dimension_version")
    run_alembic("downgrade", "c4d5e6f7a8b9")
    assert await constraint_exists("uq_child_need_generation_dimension")
    run_alembic("upgrade", "d5e6f7a8b9c0")
    assert await constraint_exists("uq_child_need_generation_dimension_version")

    async def create_same() -> tuple[bool, tuple[object, ...], list[tuple[object, ...]]]:
        async with sessions() as session:
            result = await ChildRepository(session).create_child_need_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=generation_id,
            )
            await session.commit()
            return result.created, tuple(row.id for row in result.scores), _snapshot(result.scores)

    first, second = await asyncio.gather(create_same(), create_same())
    assert sorted((first[0], second[0])) == [False, True]
    assert first[1] == second[1]

    async with sessions() as session:
        loaded = await ChildRepository(session).load_child_need_profile(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            generation_id=generation_id,
        )
        assert _snapshot(loaded.scores) == first[2] == second[2]
        balance_evidence = [
            item
            for row in loaded.scores
            for item in [*row.breakdown["supports"], *row.breakdown["counters"]]
            if item["factor_key"].startswith("balance:")
        ]
        assert balance_evidence
        assert all(len(item["lineage_refs"]) > 1 for item in balance_evidence)
        assert all(
            ref.startswith("child_chart_versions:key:planet_positions:")
            for item in balance_evidence
            for ref in item["lineage_refs"]
        )
        session.add_all(
            [
                ChildNeedScore(
                    child_profile_id=child.id,
                    child_chart_version_id=chart.id,
                    generation_id=generation_id,
                    dimension=dimension.value,
                    score=50.0,
                    confidence=0.0,
                    scoring_version="child-needs-mvp-0",
                    breakdown={},
                    evidence_refs=[],
                )
                for dimension in ChildNeedDimension
            ]
        )
        await session.commit()

    async with sessions() as session:
        loaded = await ChildRepository(session).load_child_need_profile(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            generation_id=generation_id,
        )
        assert len(loaded.scores) == 10
        assert all(row.scoring_version == "child-needs-mvp-1" for row in loaded.scores)
        assert (
            await session.scalar(
                select(func.count()).select_from(ChildNeedScore).where(ChildNeedScore.generation_id == generation_id)
            )
            == 20
        )

    async with sessions() as session:
        with pytest.raises(ChildLineageMismatchError, match="not owned"):
            await ChildRepository(session).load_child_need_profile(
                owner_user_id=uuid4(),
                child_profile_id=child.id,
                generation_id=generation_id,
            )
        with pytest.raises(ChildLineageMismatchError, match="does not belong"):
            await ChildRepository(session).create_child_need_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=uuid4(),
            )
        await session.commit()
        assert (
            await session.scalar(
                select(func.count()).select_from(ChildNeedScore).where(ChildNeedScore.generation_id == generation_id)
            )
            == 20
        )

    failed = run_alembic("downgrade", "c4d5e6f7a8b9", succeeds=False)
    assert "Refusing lossy downgrade" in failed.stderr
    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "d5e6f7a8b9c0"
        assert (
            await connection.scalar(
                text("SELECT count(*) FROM child_need_scores WHERE generation_id = :generation_id"),
                {"generation_id": generation_id},
            )
            == 20
        )
    assert await constraint_exists("uq_child_need_generation_dimension_version")
    assert not await constraint_exists("uq_child_need_generation_dimension")

    async with sessions() as session:
        row_id, original = (
            await session.execute(
                select(ChildNeedScore.id, ChildNeedScore.breakdown)
                .where(
                    ChildNeedScore.generation_id == generation_id,
                    ChildNeedScore.scoring_version == "child-needs-mvp-1",
                )
                .limit(1)
            )
        ).one()
        malformed = cast(dict[str, Any], copy.deepcopy(original))
        malformed["supports"][0]["lineage_refs"] = []
        await session.execute(
            text("UPDATE child_need_scores SET breakdown = CAST(:payload AS jsonb) WHERE id = :row_id"),
            {"payload": json.dumps(malformed), "row_id": row_id},
        )
        await session.commit()

    async with sessions() as session:
        with pytest.raises(ChildLineageMismatchError, match="breakdown"):
            await ChildRepository(session).load_child_need_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=generation_id,
            )
        await session.commit()
        assert (
            await session.scalar(
                select(func.count()).select_from(ChildNeedScore).where(ChildNeedScore.generation_id == generation_id)
            )
            == 20
        )

    async with sessions() as session:
        split_leaf = cast(dict[str, Any], copy.deepcopy(original))
        first_support = split_leaf["supports"][0]
        duplicate_support = copy.deepcopy(first_support)
        first_support["factor_value"] /= 2
        first_support["contribution"] /= 2
        duplicate_support["factor_value"] /= 2
        duplicate_support["contribution"] /= 2
        split_leaf["supports"].append(duplicate_support)
        await session.execute(
            text("UPDATE child_need_scores SET breakdown = CAST(:payload AS jsonb) WHERE id = :row_id"),
            {"payload": json.dumps(split_leaf), "row_id": row_id},
        )
        await session.commit()

    async with sessions() as session:
        with pytest.raises(ChildLineageMismatchError, match="breakdown"):
            await ChildRepository(session).load_child_need_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=generation_id,
            )

    invalid_numeric_generation_id = uuid4()
    async with sessions() as session:
        invalid_chart = ChildChartVersion(
            child_profile_id=child.id,
            version=2,
            engine_version="0.1.6",
            input_hash="e" * 64,
            birth_time_confidence="approximate",
            allowed_fact_families=["stable_planet_signs", "stable_aspects", "stable_moon_sign"],
            excluded_fact_families=["houses", "angles", "house_assignments", "house_overlays", "unstable_facts"],
            uncertainty_reason=(
                "Birth time is approximate; only facts stable across the versioned window are retained."
            ),
            calculation_payload={
                **_payload(),
                "technical_reference": {
                    "birth_datetime_utc": "2021-05-12T07:00:00+00:00",
                    "synthetic_noon": False,
                    "user_supplied_time": True,
                    "birth_time_confidence": "approximate",
                },
                "stability_evidence": {
                    "policy_version": "child-birth-time-policy-v3",
                    "window_minutes": 60,
                    "sample_offsets_minutes": [-60, -30, 0, 30, 60],
                    "sample_datetimes_utc": [
                        "2021-05-12T06:00:00+00:00",
                        "2021-05-12T06:30:00+00:00",
                        "2021-05-12T07:00:00+00:00",
                        "2021-05-12T07:30:00+00:00",
                        "2021-05-12T08:00:00+00:00",
                    ],
                    "facts": {
                        "planet_sign:Moon": {
                            "stable": True,
                            "confidence": -0.1,
                            "observed_values": ["Cancer"] * 5,
                            "sample_count": 5,
                        }
                    },
                },
                "exclusions": ["houses", "angles", "house_assignments", "house_overlays", "unstable_facts"],
            },
        )
        session.add(invalid_chart)
        await session.flush()
        session.add(
            ChildGeneration(
                child_profile_id=child.id,
                owner_user_id=owner.id,
                parent_chart_id=parent_chart.id,
                child_chart_version_id=invalid_chart.id,
                generation_id=invalid_numeric_generation_id,
                operation="create",
                idempotency_key="child-needs-invalid-numeric",
                status="deterministic_pending",
                diagnostics={},
            )
        )
        await session.flush()
        with pytest.raises(ValueError, match="finite"):
            await ChildRepository(session).create_child_need_profile(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                generation_id=invalid_numeric_generation_id,
            )
        await session.commit()
        assert (
            await session.scalar(
                select(func.count())
                .select_from(ChildNeedScore)
                .where(ChildNeedScore.generation_id == invalid_numeric_generation_id)
            )
            == 0
        )

    invalid_generation_id = uuid4()
    async with sessions() as session:
        malformed_chart = ChildChartVersion(
            child_profile_id=child.id,
            version=3,
            engine_version="0.1.6",
            input_hash="f" * 64,
            birth_time_confidence="exact",
            allowed_fact_families=[
                "planet_positions",
                "planet_signs",
                "aspects",
                "houses",
                "angles",
                "house_assignments",
            ],
            excluded_fact_families=[],
            uncertainty_reason=None,
            calculation_payload={"contract_version": "bad"},
        )
        session.add(malformed_chart)
        await session.flush()
        session.add(
            ChildGeneration(
                child_profile_id=child.id,
                owner_user_id=owner.id,
                parent_chart_id=parent_chart.id,
                child_chart_version_id=malformed_chart.id,
                generation_id=invalid_generation_id,
                operation="create",
                idempotency_key="child-needs-invalid",
                status="deterministic_pending",
                diagnostics={},
            )
        )
        await session.flush()
        result = await ChildRepository(session).create_child_need_profile(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            generation_id=invalid_generation_id,
        )
        assert len(result.scores) == 10
        assert all(row.score == 50 and row.confidence == 0 for row in result.scores)
        await session.rollback()
        assert (
            await session.scalar(
                select(func.count())
                .select_from(ChildNeedScore)
                .where(ChildNeedScore.generation_id == invalid_generation_id)
            )
            == 0
        )

    async with sessions() as session:
        await session.execute(text("DROP TABLE alembic_version"))
        await session.commit()
