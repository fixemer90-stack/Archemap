"""Additive, versioned ORM storage for target Career artifacts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import BaseModel
from app.modules.astrotype_v2 import models as _astrotype_v2_models  # noqa: F401
from app.modules.profiles import models as _profiles_models  # noqa: F401
from app.modules.users import models as _users_models  # noqa: F401

_CHART_FK = "astrotype_v2_natal_charts.id"
_PROFILE_FK = "career_profiles.id"


class CareerProfile(BaseModel):
    __tablename__ = "career_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_career_profiles_user_idempotency"),
        UniqueConstraint("generation_id", name="uq_career_profiles_generation"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person_profiles.id", ondelete="CASCADE"), index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHART_FK, ondelete="RESTRICT"), index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="questionnaire_draft", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    scoring_version: Mapped[str] = mapped_column(String(80), nullable=False)
    reference_version: Mapped[str] = mapped_column(String(80), nullable=False)
    questionnaire_version: Mapped[str] = mapped_column(String(80), nullable=False)


class CareerDimensionScore(BaseModel):
    __tablename__ = "career_dimension_scores"
    __table_args__ = (
        UniqueConstraint("career_profile_id", "dimension", name="uq_career_dimension_scores_profile_dimension"),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_career_dimension_scores_score"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_career_dimension_scores_confidence"),
    )

    career_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PROFILE_FK, ondelete="CASCADE"), index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHART_FK, ondelete="RESTRICT"), index=True
    )
    dimension: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(80), nullable=False)
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class CareerDimensionEvidence(BaseModel):
    __tablename__ = "career_dimension_evidence"
    __table_args__ = (
        UniqueConstraint("dimension_score_id", "source_type", "source_id", name="uq_career_dimension_evidence_source"),
        CheckConstraint("contribution >= -1 AND contribution <= 1", name="ck_career_dimension_evidence_contribution"),
    )

    dimension_score_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("career_dimension_scores.id", ondelete="CASCADE"), index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHART_FK, ondelete="RESTRICT"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    contribution: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class CareerQuestionnaireSession(BaseModel):
    __tablename__ = "career_questionnaire_sessions"
    __table_args__ = (
        UniqueConstraint("career_profile_id", "questionnaire_version", name="uq_career_questionnaire_profile_version"),
    )

    career_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PROFILE_FK, ondelete="CASCADE"), index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHART_FK, ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    questionnaire_version: Mapped[str] = mapped_column(String(80), nullable=False)
    context_version: Mapped[str] = mapped_column(String(80), nullable=False)
    consent_version: Mapped[str] = mapped_column(String(80), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CareerAnswer(BaseModel):
    __tablename__ = "career_answers"
    __table_args__ = (
        UniqueConstraint("questionnaire_session_id", "question_key", name="uq_career_answers_session_question"),
    )

    questionnaire_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("career_questionnaire_sessions.id", ondelete="CASCADE"), index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHART_FK, ondelete="RESTRICT"), index=True
    )
    question_key: Mapped[str] = mapped_column(String(100), nullable=False)
    answer: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    answer_version: Mapped[str] = mapped_column(String(80), nullable=False)


class CareerResolution(BaseModel):
    __tablename__ = "career_resolutions"
    __table_args__ = (
        UniqueConstraint("career_profile_id", "resolver_version", name="uq_career_resolutions_profile_version"),
    )

    career_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PROFILE_FK, ondelete="CASCADE"), index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHART_FK, ondelete="RESTRICT"), index=True
    )
    resolver_version: Mapped[str] = mapped_column(String(80), nullable=False)
    confirmed_traits: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    contradictions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    preferences: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    context_constraints: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    unresolved_ambiguities: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)


class CareerArchetypeScore(BaseModel):
    __tablename__ = "career_archetype_scores"
    __table_args__ = (
        UniqueConstraint("career_profile_id", "archetype_key", name="uq_career_archetype_profile_key"),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_career_archetype_score"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_career_archetype_confidence"),
    )

    career_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PROFILE_FK, ondelete="CASCADE"), index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHART_FK, ondelete="RESTRICT"), index=True
    )
    archetype_key: Mapped[str] = mapped_column(String(80), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reference_version: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)


class CareerEnvironmentAxis(BaseModel):
    __tablename__ = "career_environment_axes"
    __table_args__ = (
        UniqueConstraint("career_profile_id", "axis_key", name="uq_career_environment_profile_axis"),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_career_environment_score"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_career_environment_confidence"),
    )

    career_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PROFILE_FK, ondelete="CASCADE"), index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHART_FK, ondelete="RESTRICT"), index=True
    )
    axis_key: Mapped[str] = mapped_column(String(80), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reference_version: Mapped[str] = mapped_column(String(80), nullable=False)
    anti_environment_conditions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)


class CareerRoleMatch(BaseModel):
    __tablename__ = "career_role_matches"
    __table_args__ = (
        UniqueConstraint("career_profile_id", "role_family_key", name="uq_career_role_profile_family"),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_career_role_score"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_career_role_confidence"),
    )

    career_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PROFILE_FK, ondelete="CASCADE"), index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHART_FK, ondelete="RESTRICT"), index=True
    )
    role_family_key: Mapped[str] = mapped_column(String(100), nullable=False)
    match_category: Mapped[str] = mapped_column(String(30), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reference_version: Mapped[str] = mapped_column(String(80), nullable=False)
    reasons: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    tensions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    requirements: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)


class CareerPathStep(BaseModel):
    __tablename__ = "career_path_steps"
    __table_args__ = (UniqueConstraint("role_match_id", "step_order", name="uq_career_path_role_order"),)

    career_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PROFILE_FK, ondelete="CASCADE"), index=True
    )
    role_match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("career_role_matches.id", ondelete="CASCADE"), index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHART_FK, ondelete="RESTRICT"), index=True
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    node_key: Mapped[str] = mapped_column(String(100), nullable=False)
    transition_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_version: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class CareerInterpretationFact(BaseModel):
    __tablename__ = "career_interpretation_facts"
    __table_args__ = (
        UniqueConstraint("career_profile_id", "fact_key", "source_version", name="uq_career_fact_profile_key_version"),
    )

    career_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PROFILE_FK, ondelete="CASCADE"), index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHART_FK, ondelete="RESTRICT"), index=True
    )
    fact_key: Mapped[str] = mapped_column(String(140), nullable=False, index=True)
    section_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source_version: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)


class CareerSegmentGeneration(BaseModel):
    __tablename__ = "career_segment_generations"
    __table_args__ = (UniqueConstraint("generation_id", "section_key", name="uq_career_segment_generation_section"),)

    career_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PROFILE_FK, ondelete="CASCADE"), index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHART_FK, ondelete="RESTRICT"), index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    section_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    output_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class CareerReport(BaseModel):
    __tablename__ = "career_reports"
    __table_args__ = (
        UniqueConstraint("career_profile_id", "version", name="uq_career_reports_profile_version"),
        UniqueConstraint("career_profile_id", "idempotency_key", name="uq_career_reports_profile_idempotency"),
        UniqueConstraint("generation_id", name="uq_career_reports_generation"),
    )

    career_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_PROFILE_FK, ondelete="CASCADE"), index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_CHART_FK, ondelete="RESTRICT"), index=True
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="deterministic_ready", index=True)
    scoring_version: Mapped[str] = mapped_column(String(80), nullable=False)
    reference_version: Mapped[str] = mapped_column(String(80), nullable=False)
    questionnaire_version: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    deterministic_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    narrative_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    assembled_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
