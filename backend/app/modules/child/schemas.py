"""Validated domain contracts for persisted Child Report artifacts."""

from __future__ import annotations

from datetime import date, time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class BirthTimeConfidence(StrEnum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"


class ChildLifecycleStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETION_PENDING = "deletion_pending"


class ChildProfileCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    relationship_type: str = Field(min_length=1, max_length=40)
    child_gender: str | None = Field(default=None, max_length=30)
    birth_date: date
    birth_time: time | None = None
    birth_time_confidence: BirthTimeConfidence
    birth_place: str = Field(min_length=1, max_length=300)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = Field(min_length=1, max_length=80)
    caregiver_context: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1, max_length=120)
    status: ChildLifecycleStatus = ChildLifecycleStatus.ACTIVE

    @model_validator(mode="after")
    def validate_birth_time_contract(self) -> ChildProfileCreate:
        if self.birth_time_confidence is BirthTimeConfidence.UNKNOWN and self.birth_time is not None:
            raise ValueError("birth_time must be omitted when confidence is unknown")
        if self.birth_time_confidence is not BirthTimeConfidence.UNKNOWN and self.birth_time is None:
            raise ValueError("birth_time is required for exact or approximate confidence")
        return self


class ChildDimensionScoreCreate(BaseModel):
    dimension: str = Field(min_length=1, max_length=80)
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    scoring_version: str = Field(min_length=1, max_length=80)
    evidence_refs: list[str] = Field(min_length=1)
    breakdown: dict[str, Any] = Field(default_factory=dict)
