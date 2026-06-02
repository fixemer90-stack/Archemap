"""Reports module — Pydantic schemas for API requests/responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class GenerateReportRequest(BaseModel):
    """Request to generate a report."""

    profile_id: str = Field(..., description="Person profile UUID")
    product: str = Field("self", description="Vertical: self, love, child, career")
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


class ArchetypeResponse(BaseModel):
    """Archetype info."""

    primary: str
    score: float
    confidence: ConfidenceResponse


class ChartSummaryResponse(BaseModel):
    """Chart summary for report."""

    planets: list[dict[str, Any]]
    houses: list[dict[str, Any]]
    aspects: list[dict[str, Any]]
    elements: dict[str, float]
    modalities: dict[str, float]


class ReportDataResponse(BaseModel):
    """Full report data."""

    product: str
    archetype: ArchetypeResponse
    claims: list[ClaimResponse]
    all_archetype_scores: dict[str, float]
    chart: ChartSummaryResponse
    quality_warning: str | None
    provenance: dict[str, str]


class ReportResponse(BaseModel):
    """Single report response."""

    id: UUID
    profile_id: UUID
    product: str
    version: int
    status: str
    mode: str
    archetype: str | None
    score: float | None
    confidence: float | None
    pdf_url: str | None
    pdf_generated: bool
    report_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    """Paginated report list."""

    items: list[ReportResponse]
    total: int
    limit: int
    offset: int


class ReportVersionResponse(BaseModel):
    """Report version response."""

    id: UUID
    report_id: UUID
    version: int
    report_data: dict[str, Any]
    pdf_url: str | None
    diff_summary: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportVersionListResponse(BaseModel):
    """List of report versions."""

    items: list[ReportVersionResponse]
