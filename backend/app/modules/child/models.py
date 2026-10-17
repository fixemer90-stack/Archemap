"""Additive, versioned ORM storage for Child Report artifacts."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import BaseModel
from app.modules.astrotype_v2 import models as _astrotype_v2_models  # noqa: F401
from app.modules.profiles import models as _profiles_models  # noqa: F401
from app.modules.users import models as _users_models  # noqa: F401

_USER_FK = "users.id"
_PARENT_PROFILE_FK = "person_profiles.id"
_PARENT_CHART_FK = "astrotype_v2_natal_charts.id"
_CHILD_PROFILE_FK = "child_profiles.id"
_CHILD_CHART_FK = "child_chart_versions.id"
_AGE_SNAPSHOT_FK = "child_age_snapshots.id"
_REPORT_FK = "child_reports.id"


class ChildProfile(BaseModel):
    __tablename__ = "child_profiles"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "idempotency_key", name="uq_child_profiles_owner_idempotency"),
        UniqueConstraint("id", "owner_user_id", name="uq_child_profiles_id_owner"),
        CheckConstraint(
            "status IN ('active', 'archived', 'deletion_pending')",
            name="ck_child_profiles_status",
        ),
        CheckConstraint(
            "birth_time_confidence IN ('exact', 'approximate', 'unknown')",
            name="ck_child_profiles_birth_time_confidence",
        ),
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_USER_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    parent_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PARENT_PROFILE_FK, ondelete="RESTRICT"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(40), nullable=False)
    child_gender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    birth_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    birth_time_confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    birth_place: Mapped[str] = mapped_column(String(300), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)
    caregiver_context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    birth_data_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChildChartVersion(BaseModel):
    __tablename__ = "child_chart_versions"
    __table_args__ = (
        UniqueConstraint("child_profile_id", "version", name="uq_child_chart_versions_profile_version"),
        UniqueConstraint("child_profile_id", "id", name="uq_child_chart_versions_profile_id"),
        UniqueConstraint(
            "child_profile_id",
            "engine_version",
            "input_hash",
            name="uq_child_chart_versions_profile_engine_input",
        ),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(80), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    birth_time_confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    allowed_fact_families: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    excluded_fact_families: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    uncertainty_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculation_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ChildAgeSnapshot(BaseModel):
    __tablename__ = "child_age_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "child_profile_id",
            "as_of_date",
            "age_rules_version",
            "input_hash",
            name="uq_child_age_snapshots_profile_date_rules_input",
        ),
        UniqueConstraint("child_profile_id", "id", name="uq_child_age_snapshots_profile_id"),
        CheckConstraint("age_years >= 0", name="ck_child_age_snapshots_years"),
        CheckConstraint("age_months >= 0", name="ck_child_age_snapshots_months"),
        CheckConstraint("age_days >= 0", name="ck_child_age_snapshots_days"),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    age_years: Mapped[int] = mapped_column(Integer, nullable=False)
    age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    age_days: Mapped[int] = mapped_column(Integer, nullable=False)
    age_stage: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    age_rules_version: Mapped[str] = mapped_column(String(80), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class ChildParentStyleScore(BaseModel):
    __tablename__ = "child_parent_style_scores"
    __table_args__ = (
        UniqueConstraint(
            "generation_id",
            "dimension",
            "scoring_version",
            name="uq_child_parent_style_generation_dimension_version",
        ),
        ForeignKeyConstraint(
            ["child_profile_id", "generation_id", "parent_chart_id"],
            [
                "child_generations.child_profile_id",
                "child_generations.generation_id",
                "child_generations.parent_chart_id",
            ],
            name="fk_child_parent_style_generation_lineage",
            ondelete="CASCADE",
        ),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_child_parent_style_score"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_child_parent_style_confidence"),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    parent_chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PARENT_CHART_FK, ondelete="RESTRICT"), nullable=False, index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(80), nullable=False)
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)


class ChildNeedScore(BaseModel):
    __tablename__ = "child_need_scores"
    __table_args__ = (
        UniqueConstraint("generation_id", "dimension", name="uq_child_need_generation_dimension"),
        ForeignKeyConstraint(
            ["child_profile_id", "child_chart_version_id"],
            ["child_chart_versions.child_profile_id", "child_chart_versions.id"],
            name="fk_child_need_chart_lineage",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["child_profile_id", "generation_id", "child_chart_version_id"],
            [
                "child_generations.child_profile_id",
                "child_generations.generation_id",
                "child_generations.child_chart_version_id",
            ],
            name="fk_child_need_generation_lineage",
            ondelete="CASCADE",
        ),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_child_need_score"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_child_need_confidence"),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    child_chart_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_CHART_FK, ondelete="RESTRICT"), nullable=False, index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(80), nullable=False)
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)


class ChildSynastryEvidence(BaseModel):
    __tablename__ = "child_synastry_evidence"
    __table_args__ = (
        UniqueConstraint("generation_id", "source_key", name="uq_child_synastry_generation_source"),
        ForeignKeyConstraint(
            ["child_profile_id", "child_chart_version_id"],
            ["child_chart_versions.child_profile_id", "child_chart_versions.id"],
            name="fk_child_synastry_chart_lineage",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["child_profile_id", "generation_id", "parent_chart_id", "child_chart_version_id"],
            [
                "child_generations.child_profile_id",
                "child_generations.generation_id",
                "child_generations.parent_chart_id",
                "child_generations.child_chart_version_id",
            ],
            name="fk_child_synastry_generation_lineage",
            ondelete="CASCADE",
        ),
        CheckConstraint("contribution >= -1 AND contribution <= 1", name="ck_child_synastry_contribution"),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    parent_chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PARENT_CHART_FK, ondelete="RESTRICT"), nullable=False, index=True
    )
    child_chart_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_CHART_FK, ondelete="RESTRICT"), nullable=False, index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False)
    contribution: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ChildInteractionScore(BaseModel):
    __tablename__ = "child_interaction_scores"
    __table_args__ = (
        UniqueConstraint("generation_id", "dimension", name="uq_child_interaction_generation_dimension"),
        ForeignKeyConstraint(
            ["child_profile_id", "generation_id"],
            ["child_generations.child_profile_id", "child_generations.generation_id"],
            name="fk_child_interaction_generation_lineage",
            ondelete="CASCADE",
        ),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_child_interaction_score"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_child_interaction_confidence"),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    dimension: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    pattern: Mapped[str] = mapped_column(String(60), nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ChildQuestionnaireSession(BaseModel):
    __tablename__ = "child_questionnaire_sessions"
    __table_args__ = (
        UniqueConstraint("child_profile_id", "questionnaire_version", name="uq_child_questionnaire_profile_version"),
        UniqueConstraint("child_profile_id", "id", name="uq_child_questionnaire_profile_id"),
        UniqueConstraint(
            "child_profile_id",
            "completion_idempotency_key",
            name="uq_child_questionnaire_completion_idempotency",
        ),
        ForeignKeyConstraint(
            ["child_profile_id", "age_snapshot_id"],
            ["child_age_snapshots.child_profile_id", "child_age_snapshots.id"],
            name="fk_child_questionnaire_age_lineage",
            ondelete="RESTRICT",
        ),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    age_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_AGE_SNAPSHOT_FK, ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    questionnaire_version: Mapped[str] = mapped_column(String(80), nullable=False)
    context_version: Mapped[str] = mapped_column(String(80), nullable=False)
    consent_version: Mapped[str] = mapped_column(String(80), nullable=False)
    completion_idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    answers_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChildAnswer(BaseModel):
    __tablename__ = "child_answers"
    __table_args__ = (
        UniqueConstraint("questionnaire_session_id", "question_key", name="uq_child_answers_session_question"),
        ForeignKeyConstraint(
            ["child_profile_id", "questionnaire_session_id"],
            ["child_questionnaire_sessions.child_profile_id", "child_questionnaire_sessions.id"],
            name="fk_child_answers_session_lineage",
            ondelete="CASCADE",
        ),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    questionnaire_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("child_questionnaire_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_key: Mapped[str] = mapped_column(String(100), nullable=False)
    answer: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    answer_version: Mapped[str] = mapped_column(String(80), nullable=False)


class ChildContextResolution(BaseModel):
    __tablename__ = "child_context_resolutions"
    __table_args__ = (
        UniqueConstraint("generation_id", "resolver_version", name="uq_child_context_generation_version"),
        ForeignKeyConstraint(
            ["child_profile_id", "generation_id"],
            ["child_generations.child_profile_id", "child_generations.generation_id"],
            name="fk_child_context_generation_lineage",
            ondelete="CASCADE",
        ),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    resolver_version: Mapped[str] = mapped_column(String(80), nullable=False)
    natural_strengths: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    potential_friction: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    compensation_areas: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    age_relevant_guidance: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    confirmations: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    contradictions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    unresolved_ambiguities: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)


class ChildGuidanceFacts(BaseModel):
    __tablename__ = "child_guidance_facts"
    __table_args__ = (
        UniqueConstraint("generation_id", "contract_version", name="uq_child_guidance_generation_contract"),
        ForeignKeyConstraint(
            ["child_profile_id", "generation_id"],
            ["child_generations.child_profile_id", "child_generations.generation_id"],
            name="fk_child_guidance_generation_lineage",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["child_profile_id", "age_snapshot_id"],
            ["child_age_snapshots.child_profile_id", "child_age_snapshots.id"],
            name="fk_child_guidance_age_lineage",
            ondelete="RESTRICT",
        ),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    age_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_AGE_SNAPSHOT_FK, ondelete="RESTRICT"), nullable=False, index=True
    )
    contract_version: Mapped[str] = mapped_column(String(80), nullable=False)
    core_report_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    evidence_registry: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ChildSegmentGeneration(BaseModel):
    __tablename__ = "child_segment_generations"
    __table_args__ = (
        UniqueConstraint("generation_id", "section_key", name="uq_child_segment_generation_section"),
        ForeignKeyConstraint(
            ["child_profile_id", "generation_id"],
            ["child_generations.child_profile_id", "child_generations.generation_id"],
            name="fk_child_segment_generation_lineage",
            ondelete="CASCADE",
        ),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    section_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    diagnostics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ChildReport(BaseModel):
    __tablename__ = "child_reports"
    __table_args__ = (
        UniqueConstraint("child_profile_id", "version", name="uq_child_reports_profile_version"),
        UniqueConstraint("generation_id", name="uq_child_reports_generation"),
        UniqueConstraint("child_profile_id", "id", name="uq_child_reports_profile_id"),
        UniqueConstraint("child_profile_id", "idempotency_key", name="uq_child_reports_profile_idempotency"),
        ForeignKeyConstraint(
            ["child_profile_id", "child_chart_version_id"],
            ["child_chart_versions.child_profile_id", "child_chart_versions.id"],
            name="fk_child_reports_chart_lineage",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["child_profile_id", "generation_id", "parent_chart_id", "child_chart_version_id"],
            [
                "child_generations.child_profile_id",
                "child_generations.generation_id",
                "child_generations.parent_chart_id",
                "child_generations.child_chart_version_id",
            ],
            name="fk_child_reports_generation_lineage",
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    parent_chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PARENT_CHART_FK, ondelete="RESTRICT"), nullable=False, index=True
    )
    child_chart_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_CHART_FK, ondelete="RESTRICT"), nullable=False, index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    scoring_version: Mapped[str] = mapped_column(String(80), nullable=False)
    reference_version: Mapped[str] = mapped_column(String(80), nullable=False)
    questionnaire_version: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    report_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    presentation_manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ChildReportAgeGuidance(BaseModel):
    __tablename__ = "child_report_age_guidance"
    __table_args__ = (
        UniqueConstraint(
            "report_id", "age_snapshot_id", "version", name="uq_child_age_guidance_report_snapshot_version"
        ),
        UniqueConstraint("child_profile_id", "idempotency_key", name="uq_child_age_guidance_profile_idempotency"),
        ForeignKeyConstraint(
            ["child_profile_id", "report_id"],
            ["child_reports.child_profile_id", "child_reports.id"],
            name="fk_child_age_guidance_report_lineage",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["child_profile_id", "age_snapshot_id"],
            ["child_age_snapshots.child_profile_id", "child_age_snapshots.id"],
            name="fk_child_age_guidance_age_lineage",
            ondelete="RESTRICT",
        ),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_REPORT_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    age_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_AGE_SNAPSHOT_FK, ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    rules_version: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ChildGeneration(BaseModel):
    __tablename__ = "child_generations"
    __table_args__ = (
        UniqueConstraint("generation_id", name="uq_child_generations_generation"),
        UniqueConstraint("child_profile_id", "generation_id", name="uq_child_generations_profile_generation"),
        UniqueConstraint(
            "child_profile_id",
            "generation_id",
            "parent_chart_id",
            name="uq_child_generations_profile_generation_parent_chart",
        ),
        UniqueConstraint(
            "child_profile_id",
            "generation_id",
            "child_chart_version_id",
            name="uq_child_generations_profile_generation_child_chart",
        ),
        UniqueConstraint(
            "child_profile_id",
            "generation_id",
            "parent_chart_id",
            "child_chart_version_id",
            name="uq_child_generations_complete_lineage",
        ),
        UniqueConstraint(
            "owner_user_id",
            "operation",
            "idempotency_key",
            name="uq_child_generations_owner_operation_idempotency",
        ),
        ForeignKeyConstraint(
            ["child_profile_id", "owner_user_id"],
            ["child_profiles.id", "child_profiles.owner_user_id"],
            name="fk_child_generations_owner_lineage",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["child_profile_id", "child_chart_version_id"],
            ["child_chart_versions.child_profile_id", "child_chart_versions.id"],
            name="fk_child_generations_chart_lineage",
            ondelete="RESTRICT",
        ),
    )

    child_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_PROFILE_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_USER_FK, ondelete="CASCADE"), nullable=False, index=True
    )
    parent_chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PARENT_CHART_FK, ondelete="RESTRICT"), nullable=False, index=True
    )
    child_chart_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHILD_CHART_FK, ondelete="RESTRICT"), nullable=False, index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="queued", index=True)
    report_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    source_report_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    diagnostics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ImmutableChildArtifactError(RuntimeError):
    """Raised when append-only child data is updated or deleted outside privacy purge."""


IMMUTABLE_CHILD_ARTIFACT_MODELS = (
    ChildChartVersion,
    ChildAgeSnapshot,
    ChildParentStyleScore,
    ChildNeedScore,
    ChildSynastryEvidence,
    ChildInteractionScore,
    ChildAnswer,
    ChildContextResolution,
    ChildGuidanceFacts,
    ChildReport,
    ChildReportAgeGuidance,
)

CHILD_DOMAIN_ARTIFACT_MODELS = (
    ChildChartVersion,
    ChildAgeSnapshot,
    ChildParentStyleScore,
    ChildNeedScore,
    ChildSynastryEvidence,
    ChildInteractionScore,
    ChildQuestionnaireSession,
    ChildAnswer,
    ChildContextResolution,
    ChildGuidanceFacts,
    ChildSegmentGeneration,
    ChildReport,
    ChildReportAgeGuidance,
    ChildGeneration,
)


def _reject_immutable_artifact_mutation(*_: object) -> None:
    raise ImmutableChildArtifactError("Child artifact is append-only; create a new version instead")


for _immutable_model in IMMUTABLE_CHILD_ARTIFACT_MODELS:
    event.listen(_immutable_model, "before_update", _reject_immutable_artifact_mutation)
    event.listen(_immutable_model, "before_delete", _reject_immutable_artifact_mutation)
