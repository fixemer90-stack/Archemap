from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import Table, UniqueConstraint

EXPECTED_TABLES = {
    "career_profiles",
    "career_dimension_scores",
    "career_dimension_evidence",
    "career_questionnaire_sessions",
    "career_answers",
    "career_resolutions",
    "career_archetype_scores",
    "career_environment_axes",
    "career_role_matches",
    "career_path_steps",
    "career_interpretation_facts",
    "career_segment_generations",
    "career_reports",
    "career_generations",
}
FOUNDATION_TABLES = EXPECTED_TABLES - {"career_generations"}
ROOT = Path(__file__).resolve().parents[3]


def test_domain_schemas_enforce_ranges_enums_evidence_and_versions() -> None:
    from app.modules.career.schemas import (
        CareerDimensionEvidenceCreate,
        CareerDimensionKey,
        CareerDimensionScoreCreate,
        EvidenceDirection,
    )

    evidence = CareerDimensionEvidenceCreate(
        source_type="natal_fact",
        source_id=uuid4(),
        contribution=0.18,
        direction=EvidenceDirection.SUPPORTS,
    )
    score = CareerDimensionScoreCreate(
        dimension=CareerDimensionKey.SYSTEMS_THINKING,
        score=91,
        confidence=0.84,
        scoring_version="career-mvp-1",
        evidence=[evidence],
    )
    assert score.score == 91
    assert score.confidence == 0.84

    for field, value in [("score", 101), ("confidence", 1.01)]:
        payload = {
            "dimension": "systems_thinking",
            "score": 91,
            "confidence": 0.84,
            "scoring_version": "career-mvp-1",
            "evidence": [evidence],
            field: value,
        }
        with pytest.raises(ValidationError):
            CareerDimensionScoreCreate.model_validate(payload)

    with pytest.raises(ValidationError):
        CareerDimensionScoreCreate(
            dimension=CareerDimensionKey.SYSTEMS_THINKING,
            score=50,
            confidence=0.5,
            scoring_version="career-mvp-1",
            evidence=[],
        )


def test_orm_declares_all_queryable_career_entities_and_chart_lineage() -> None:
    from app.modules.career import models

    mapped = {
        value.__table__.name: value
        for value in vars(models).values()
        if isinstance(value, type) and hasattr(value, "__table__") and value.__table__.name.startswith("career_")
    }
    assert set(mapped) == EXPECTED_TABLES
    for table_name, model in mapped.items():
        assert "chart_id" in model.__table__.columns, table_name

    assert "generation_id" in models.CareerProfile.__table__.columns
    assert "idempotency_key" in models.CareerProfile.__table__.columns
    assert "version" in models.CareerReport.__table__.columns
    assert "scoring_version" in models.CareerDimensionScore.__table__.columns
    assert "questionnaire_version" in models.CareerQuestionnaireSession.__table__.columns
    assert "resolver_version" in models.CareerResolution.__table__.columns
    assert "prompt_version" in models.CareerSegmentGeneration.__table__.columns
    generation = cast(Table, models.CareerGeneration.__table__)
    generation_columns = set(generation.columns.keys())
    assert {"user_id", "career_profile_id", "report_id", "source_report_id"} <= generation_columns
    assert {"operation", "idempotency_key", "status", "celery_task_id", "diagnostics"} <= generation_columns
    assert any(
        {column.name for column in constraint.columns} == {"user_id", "operation", "idempotency_key"}
        for constraint in generation.constraints
        if isinstance(constraint, UniqueConstraint)
    )


def test_migration_is_additive_reversible_and_preserves_legacy_tables() -> None:
    path = ROOT / "alembic" / "versions" / "e4f5a6b7c8d9_add_career_report_foundation.py"
    source = path.read_text(encoding="utf-8")
    for table in FOUNDATION_TABLES:
        assert f'"{table}"' in source
    upgrade = source.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]
    assert "drop_table" not in upgrade
    for legacy in ("reports", "chart_snapshots", "payments", "entitlements"):
        assert f'drop_table("{legacy}")' not in source

    spec = importlib.util.spec_from_file_location("career_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "d3e4f5a6b7c8"


def test_career_generation_migration_is_additive_and_reversible() -> None:
    path = ROOT / "alembic" / "versions" / "a6b7c8d9e0f1_add_career_generations.py"
    source = path.read_text(encoding="utf-8")
    assert '"career_generations"' in source
    assert '"user_id", "operation", "idempotency_key"' in source
    upgrade = source.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]
    assert "drop_table" not in upgrade
    spec = importlib.util.spec_from_file_location("career_generation_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "f5a6b7c8d9e0"


@pytest.mark.asyncio
async def test_repository_idempotency_ownership_and_immutable_report_history() -> None:
    from app.modules.career.models import CareerProfile, CareerReport
    from app.modules.career.repository import CareerRepository

    existing_profile = CareerProfile(
        user_id=uuid4(),
        profile_id=uuid4(),
        chart_id=uuid4(),
        generation_id=uuid4(),
        idempotency_key="create-1",
        status="queued",
        version=1,
        scoring_version="career-mvp-1",
        reference_version="career-ref-1",
        questionnaire_version="career-q-1",
    )
    existing_report = CareerReport(
        career_profile_id=existing_profile.id,
        chart_id=existing_profile.chart_id,
        generation_id=existing_profile.generation_id,
        idempotency_key="report-1",
        version=2,
        status="deterministic_ready",
        scoring_version="career-mvp-1",
        reference_version="career-ref-1",
        questionnaire_version="career-q-1",
        prompt_version="career-prompt-1",
    )
    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_profile)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_report)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_report)),
        ]
    )
    repository = CareerRepository(session)

    assert await repository.get_profile_by_idempotency_key(existing_profile.user_id, "create-1") is existing_profile
    assert await repository.get_report_for_user(existing_report.id, existing_profile.user_id) is existing_report
    assert await repository.get_latest_report(existing_profile.id) is existing_report

    statements = "\n".join(str(call.args[0]) for call in session.execute.await_args_list)
    assert "career_profiles.user_id" in statements
    assert "career_profiles.idempotency_key" in statements
    assert "career_reports.version DESC" in statements
    assert "JOIN career_profiles" in statements
