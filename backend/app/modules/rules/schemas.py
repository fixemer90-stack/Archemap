"""Rules module schemas — Pydantic models for API requests/responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class InterpretRequest(BaseModel):
    """Request to interpret a chart."""

    profile_id: str = Field(..., description="Person profile UUID")
    product: str = Field("self", description="Vertical: self, love, child, career")
    ruleset_version: str = Field("v1", description="Ruleset version tag")
    locale: str = Field("ru-RU", description="Locale for templates")
    mode: str = Field("full", description="full or preview")


class ConfidenceResponse(BaseModel):
    """Confidence assessment."""

    value: float
    label: str
    reason_codes: list[str]


class BasisItemResponse(BaseModel):
    """Evidence basis item."""

    rule_id: str
    feature: str
    value: float
    contribution: float


class ClaimResponse(BaseModel):
    """Interpretive claim with evidence."""

    claim_id: str
    section: str
    archetype: str
    score: float
    confidence: ConfidenceResponse
    message: str
    basis: list[BasisItemResponse]
    counter_evidence: list[BasisItemResponse]
    provenance: dict[str, str]


class InterpretResponse(BaseModel):
    """Full interpretation response."""

    product: str
    primary_archetype: str
    primary_score: float
    primary_confidence: ConfidenceResponse
    claims: list[ClaimResponse]
    all_archetype_scores: dict[str, float]
    quality_warning: str | None
    provenance: dict[str, str]


class RuleSetInfo(BaseModel):
    """Available ruleset info."""

    product: str
    version: str
    path: str
