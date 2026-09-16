"""Strict persisted-domain DTOs for Career report calculation."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class CareerDimensionKey(StrEnum):
    LEADERSHIP = "leadership"
    ANALYTICAL_THINKING = "analytical_thinking"
    SYSTEMS_THINKING = "systems_thinking"
    COMMUNICATION = "communication"
    CREATIVITY = "creativity"
    STRUCTURE = "structure"
    AUTONOMY = "autonomy"
    RISK_TOLERANCE = "risk_tolerance"
    PEOPLE_ORIENTATION = "people_orientation"
    INNOVATION = "innovation"
    LONG_TERM_FOCUS = "long_term_focus"
    EXECUTION = "execution"


class EvidenceDirection(StrEnum):
    SUPPORTS = "supports"
    COUNTERS = "counters"
    MISSING = "missing"


class CareerLifecycleStatus(StrEnum):
    QUESTIONNAIRE_DRAFT = "questionnaire_draft"
    QUESTIONNAIRE_COMPLETED = "questionnaire_completed"
    QUEUED = "queued"
    CALCULATING_DIMENSIONS = "calculating_dimensions"
    DETERMINISTIC_READY = "deterministic_ready"
    GENERATING_SECTIONS = "generating_sections"
    READY = "ready"
    NARRATIVE_FAILED = "narrative_failed"
    FAILED = "failed"


class QuestionnaireStatus(StrEnum):
    DRAFT = "draft"
    COMPLETED = "completed"


class MatchCategory(StrEnum):
    STRONG_MATCH = "strong_match"
    POSSIBLE_MATCH = "possible_match"
    CONTEXT_DEPENDENT = "context_dependent"


class SegmentStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class CareerDimensionEvidenceCreate(BaseModel):
    source_type: str = Field(min_length=1, max_length=80)
    source_id: UUID
    contribution: float = Field(ge=-1, le=1)
    direction: EvidenceDirection


class CareerDimensionScoreCreate(BaseModel):
    dimension: CareerDimensionKey
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    scoring_version: str = Field(min_length=1, max_length=80)
    evidence: list[CareerDimensionEvidenceCreate] = Field(min_length=1)


class CareerArtifactVersions(BaseModel):
    scoring_version: str = Field(min_length=1, max_length=80)
    reference_version: str = Field(min_length=1, max_length=80)
    questionnaire_version: str = Field(min_length=1, max_length=80)
    resolver_version: str | None = Field(default=None, min_length=1, max_length=80)
    prompt_version: str | None = Field(default=None, min_length=1, max_length=80)
    model_version: str | None = Field(default=None, min_length=1, max_length=120)
