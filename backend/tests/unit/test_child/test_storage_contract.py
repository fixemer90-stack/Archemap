from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import Table, UniqueConstraint

EXPECTED_TABLES = {
    "child_profiles",
    "child_chart_versions",
    "child_age_snapshots",
    "child_parent_style_scores",
    "child_need_scores",
    "child_synastry_evidence",
    "child_interaction_scores",
    "child_questionnaire_sessions",
    "child_answers",
    "child_context_resolutions",
    "child_guidance_facts",
    "child_segment_generations",
    "child_reports",
    "child_report_age_guidance",
    "child_generations",
}
ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "alembic" / "versions" / "a2b3c4d5e6f7_add_child_report_foundation.py"
AGE_SNAPSHOT_MIGRATION = ROOT / "alembic" / "versions" / "b3c4d5e6f7a8_include_age_snapshot_input_hash.py"


def test_child_domain_schemas_enforce_birth_time_score_and_lineage_contracts() -> None:
    from app.modules.child.schemas import (
        BirthTimeConfidence,
        ChildDimensionScoreCreate,
        ChildLifecycleStatus,
        ChildProfileCreate,
    )

    profile = ChildProfileCreate(
        display_name="Миша",
        relationship_type="son",
        child_gender="male",
        birth_date=date(2021, 5, 12),
        birth_time=None,
        birth_time_confidence=BirthTimeConfidence.UNKNOWN,
        birth_place="Москва",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        caregiver_context={"primary_caregiver": True},
        idempotency_key="child-create-1",
    )
    assert profile.birth_time_confidence is BirthTimeConfidence.UNKNOWN
    assert profile.status is ChildLifecycleStatus.ACTIVE

    score = ChildDimensionScoreCreate(
        dimension="autonomy_balance",
        score=64,
        confidence=0.78,
        scoring_version="child-interaction-mvp-1",
        evidence_refs=["synastry:1", "parent-style:2"],
    )
    assert score.score == 64

    for field, value in (("score", 101), ("confidence", 1.01)):
        payload = score.model_dump()
        payload[field] = value
        with pytest.raises(ValidationError):
            ChildDimensionScoreCreate.model_validate(payload)

    with pytest.raises(ValidationError):
        ChildDimensionScoreCreate(
            dimension="autonomy_balance",
            score=50,
            confidence=0.5,
            scoring_version="child-interaction-mvp-1",
            evidence_refs=[],
        )


def test_orm_declares_isolated_child_entities_and_complete_lineage() -> None:
    from app.modules.child import models

    mapped = {
        value.__table__.name: value
        for value in vars(models).values()
        if isinstance(value, type) and hasattr(value, "__table__") and value.__table__.name.startswith("child_")
    }
    assert set(mapped) == EXPECTED_TABLES

    profile = cast(Table, models.ChildProfile.__table__)
    assert {
        "owner_user_id",
        "parent_profile_id",
        "display_name",
        "birth_date",
        "birth_time",
        "birth_time_confidence",
        "caregiver_context",
        "birth_data_hash",
        "idempotency_key",
        "status",
        "version",
    } <= set(profile.columns.keys())
    assert any(
        {column.name for column in constraint.columns} == {"owner_user_id", "idempotency_key"}
        for constraint in profile.constraints
        if isinstance(constraint, UniqueConstraint)
    )

    for table_name, model in mapped.items():
        if table_name != "child_profiles":
            assert "child_profile_id" in model.__table__.columns, table_name

    generation = cast(Table, models.ChildGeneration.__table__)
    assert {
        "owner_user_id",
        "child_profile_id",
        "parent_chart_id",
        "child_chart_version_id",
        "generation_id",
        "operation",
        "idempotency_key",
        "status",
    } <= set(generation.columns.keys())
    assert any(
        {column.name for column in constraint.columns} == {"owner_user_id", "operation", "idempotency_key"}
        for constraint in generation.constraints
        if isinstance(constraint, UniqueConstraint)
    )

    report = cast(Table, models.ChildReport.__table__)
    assert {
        "generation_id",
        "parent_chart_id",
        "child_chart_version_id",
        "version",
        "status",
        "report_payload",
        "presentation_manifest",
    } <= set(report.columns.keys())
    assert any(
        {column.name for column in constraint.columns} == {"child_profile_id", "version"}
        for constraint in report.constraints
        if isinstance(constraint, UniqueConstraint)
    )

    age_guidance = cast(Table, models.ChildReportAgeGuidance.__table__)
    assert {"report_id", "age_snapshot_id", "version", "payload"} <= set(age_guidance.columns.keys())

    age_snapshot = cast(Table, models.ChildAgeSnapshot.__table__)
    assert any(
        {column.name for column in constraint.columns}
        == {"child_profile_id", "as_of_date", "age_rules_version", "input_hash"}
        for constraint in age_snapshot.constraints
        if isinstance(constraint, UniqueConstraint)
    )


def test_child_foundation_migration_is_additive_reversible_and_legacy_safe() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    for table in EXPECTED_TABLES:
        assert table in source

    upgrade = source.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]
    assert "drop_table" not in upgrade
    for protected in (
        "users",
        "person_profiles",
        "reports",
        "payments",
        "entitlements",
        "astrotype_v2_natal_charts",
        "career_profiles",
    ):
        assert f'drop_table("{protected}")' not in source
        assert f'alter_column("{protected}"' not in source

    spec = importlib.util.spec_from_file_location("child_foundation_migration", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "f1a2b3c4d5e6"


def test_age_snapshot_constraint_fix_is_a_separate_reversible_migration() -> None:
    source = AGE_SNAPSHOT_MIGRATION.read_text(encoding="utf-8")
    assert 'down_revision: str | None = "a2b3c4d5e6f7"' in source
    assert "uq_child_age_snapshots_profile_date_rules_input" in source
    assert '["child_profile_id", "as_of_date", "age_rules_version", "input_hash"]' in source
    assert "def downgrade()" in source


@pytest.mark.asyncio
async def test_repository_queries_are_owner_and_child_scoped() -> None:
    from app.modules.child.models import ChildProfile, ChildReport
    from app.modules.child.repository import ChildRepository

    owner_id = uuid4()
    child = ChildProfile(
        owner_user_id=owner_id,
        parent_profile_id=uuid4(),
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
        caregiver_context={},
        birth_data_hash="a" * 64,
        idempotency_key="child-create-1",
        status="active",
        version=1,
    )
    report = ChildReport(
        child_profile_id=child.id,
        parent_chart_id=uuid4(),
        child_chart_version_id=uuid4(),
        generation_id=uuid4(),
        idempotency_key="report-create-1",
        version=2,
        status="deterministic_ready",
        scoring_version="child-scoring-1",
        reference_version="child-reference-1",
        questionnaire_version="child-questionnaire-1",
        prompt_version="child-prompt-1",
        report_payload={},
        presentation_manifest={},
    )
    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=child)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[child])))),
            MagicMock(scalar_one_or_none=MagicMock(return_value=report)),
        ]
    )
    session.scalar = AsyncMock(return_value=report.id)
    repository = ChildRepository(session)

    assert await repository.get_child_for_owner(child_id=child.id, owner_user_id=owner_id) is child
    assert await repository.list_children_for_owner(owner_user_id=owner_id) == [child]
    assert await repository.get_latest_report(child_profile_id=child.id, owner_user_id=owner_id) is report
    assert await repository.get_owned_report_id(report_id=report.id, owner_user_id=owner_id) == report.id

    statements = "\n".join(str(call.args[0]) for call in session.execute.await_args_list)
    assert "child_profiles.owner_user_id" in statements
    assert "child_profiles.status !=" in statements
    assert "child_reports.version DESC" in statements
    scalar_statement = str(session.scalar.await_args.args[0])
    assert "JOIN child_profiles" in scalar_statement
    assert "child_profiles.owner_user_id" in scalar_statement


@pytest.mark.asyncio
async def test_repository_child_creation_is_idempotent_and_rejects_cross_target_reuse() -> None:
    from app.modules.child.models import ChildProfile
    from app.modules.child.repository import ChildIdempotencyTargetMismatchError, ChildRepository

    owner_id = uuid4()
    parent_profile_id = uuid4()
    existing = ChildProfile(
        owner_user_id=owner_id,
        parent_profile_id=parent_profile_id,
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
        caregiver_context={},
        birth_data_hash="a" * 64,
        idempotency_key="child-create-1",
        status="active",
        version=1,
    )
    session = MagicMock()
    session.scalar = AsyncMock(return_value=parent_profile_id)
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing)),
        ]
    )
    repository = ChildRepository(session)

    replay = await repository.create_child_idempotently(
        owner_user_id=owner_id,
        parent_profile_id=parent_profile_id,
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
        caregiver_context={},
        birth_data_hash="a" * 64,
        idempotency_key="child-create-1",
    )
    assert replay.created is False
    assert replay.child is existing

    with pytest.raises(ChildIdempotencyTargetMismatchError):
        await repository.create_child_idempotently(
            owner_user_id=owner_id,
            parent_profile_id=parent_profile_id,
            display_name="Другой ребёнок",
            relationship_type="child",
            child_gender=None,
            birth_date=date(2020, 1, 1),
            birth_time=None,
            birth_time_confidence="unknown",
            birth_place="Казань",
            latitude=55.7963,
            longitude=49.1088,
            timezone="Europe/Moscow",
            caregiver_context={},
            birth_data_hash="b" * 64,
            idempotency_key="child-create-1",
        )

    source = (ROOT / "app" / "modules" / "child" / "repository.py").read_text(encoding="utf-8")
    assert "on_conflict_do_nothing" in source
    assert "uq_child_profiles_owner_idempotency" in source


def test_child_repository_imports_only_child_and_v2_storage_boundaries() -> None:
    source = (ROOT / "app" / "modules" / "child" / "repository.py").read_text(encoding="utf-8")

    assert "app.modules.child" in source
    assert "app.modules.career" not in source
    assert "app.modules.reports" not in source
    assert "ChartSnapshot" not in source
