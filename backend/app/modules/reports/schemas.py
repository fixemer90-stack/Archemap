"""Reports module — Pydantic schemas for API requests/responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.report_narratives.models import ReportNarrative
from app.modules.report_narratives.schemas import NarrativeStageArtifact, NarrativeStageProgress
from app.modules.reports.models import Report


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


class NarrativeResponse(BaseModel):
    """Persisted narrative payload and generation metadata."""

    id: UUID
    report_id: UUID
    product: str
    prompt_version: str
    model_provider: str
    model_name: str
    status: str
    title: str | None = None
    hero: dict[str, Any] | None = None
    dominants: list[dict[str, Any]] = Field(default_factory=list)
    inner_mechanism: dict[str, Any] | None = None
    house_scenarios: list[dict[str, Any]] = Field(default_factory=list)
    calibration_questions: list[dict[str, Any]] = Field(default_factory=list)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    failure_modes: list[dict[str, Any]] = Field(default_factory=list)
    maturity_levels: dict[str, Any] | None = None
    sections: list[dict[str, Any]] = Field(default_factory=list)
    career_cta: dict[str, Any] | None = None
    content: dict[str, Any] | None = None
    stage_progress: NarrativeStageProgress | None = None
    stage_artifacts: list[NarrativeStageArtifact] = Field(default_factory=list)
    error_message: str | None = None
    generation_started_at: datetime | None = None
    generation_finished_at: datetime | None = None
    generation_attempts: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
    narrative: NarrativeResponse | None = None
    narrative_progress: NarrativeStageProgress | None = None
    narrative_stage_artifacts: list[NarrativeStageArtifact] = Field(default_factory=list)
    error_message: str | None = None
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


def build_narrative_response(narrative: ReportNarrative) -> NarrativeResponse:
    """Serialize a persisted narrative row into API response shape."""
    content = narrative.content or {}
    staged_progress_payload = content.get("stage_progress") if isinstance(content, dict) else None
    raw_stage_artifacts_payload = content.get("stage_artifacts") if isinstance(content, dict) else []
    staged_artifacts_payload = raw_stage_artifacts_payload if isinstance(raw_stage_artifacts_payload, list) else []
    stage_progress = (
        NarrativeStageProgress.model_validate(staged_progress_payload)
        if isinstance(staged_progress_payload, dict)
        else None
    )
    stage_artifacts = [
        NarrativeStageArtifact.model_validate(item)
        for item in staged_artifacts_payload
        if isinstance(item, dict)
    ]
    return NarrativeResponse(
        id=narrative.id,
        report_id=narrative.report_id,
        product=narrative.product,
        prompt_version=narrative.prompt_version,
        model_provider=narrative.model_provider,
        model_name=narrative.model_name,
        status=narrative.status,
        title=content.get("title"),
        hero=content.get("hero"),
        dominants=content.get("dominants", []),
        inner_mechanism=content.get("inner_mechanism"),
        house_scenarios=content.get("house_scenarios", []),
        calibration_questions=content.get("calibration_questions", []),
        contradictions=content.get("contradictions", []),
        failure_modes=content.get("failure_modes", []),
        maturity_levels=content.get("maturity_levels"),
        sections=content.get("sections", []),
        career_cta=content.get("career_cta"),
        content=content or None,
        stage_progress=stage_progress,
        stage_artifacts=stage_artifacts,
        error_message=narrative.error_message,
        generation_started_at=narrative.generation_started_at,
        generation_finished_at=narrative.generation_finished_at,
        generation_attempts=narrative.generation_attempts,
        created_at=narrative.created_at,
        updated_at=narrative.updated_at,
    )


def build_report_response(report: Report, narrative: ReportNarrative | None = None) -> ReportResponse:
    """Serialize a report together with its latest narrative state."""
    serialized_narrative = build_narrative_response(narrative) if narrative is not None else None
    return ReportResponse(
        id=report.id,
        profile_id=report.profile_id,
        product=report.product,
        version=report.version,
        status=report.status,
        mode=report.mode,
        archetype=report.archetype,
        score=report.score,
        confidence=report.confidence,
        pdf_url=report.pdf_url,
        pdf_generated=report.pdf_generated,
        report_data=report.report_data,
        narrative=serialized_narrative,
        narrative_progress=serialized_narrative.stage_progress if serialized_narrative is not None else None,
        narrative_stage_artifacts=(
            serialized_narrative.stage_artifacts if serialized_narrative is not None else []
        ),
        error_message=report.error_message,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )
