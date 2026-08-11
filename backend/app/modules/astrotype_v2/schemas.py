"""Pydantic contracts for Astrotype v2 deterministic and narrative boundaries."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class SectionThemeInputV2(BaseModel):
    """One theme exposed to a single section render input."""

    id: str
    title: str
    summary: str
    fact_keys: list[str]
    evidence_ids: list[str]
    weight: float
    confidence: float
    polarity: str | None = None
    fact_type: str | None = None


class SectionRenderInputV2(BaseModel):
    """Curated JSON input for one upper narrative report section."""

    contract_version: str = "section_render_input_v2"
    chart_id: uuid.UUID
    source_version: str
    section_id: str
    section_title: str
    section_purpose: str
    owned_themes: list[SectionThemeInputV2]
    reference_themes: list[SectionThemeInputV2]
    forbidden_theme_ids: list[str]
    evidence_ids: list[str]
    already_explained: dict[str, Any]
    style_contract: dict[str, Any]
    depth_contract: dict[str, Any]
    continuation_policy: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        """Return stable JSON-compatible payload for prompt building/persistence."""

        return self.model_dump(mode="json")


class ReportSegmentOutputV2(BaseModel):
    """Typed LLM response for one v2 report segment."""

    contract_version: str = "report_segment_output_v2"
    section_id: str
    title: str
    body: str
    covered_theme_ids: list[str]
    evidence_ids: list[str]
    continuation_complete: bool = True
    continuation_cursor: str | None = None
    notes: list[str] = Field(default_factory=list)


class NatalReportSectionV2(BaseModel):
    """Final user-facing narrative section assembled from one validated segment."""

    section_id: str
    title: str
    body: str
    covered_theme_ids: list[str]
    evidence_ids: list[str]
    source_segment_hash: str | None = None


class NatalReportV2(BaseModel):
    """Final v2 natal report contract with narrative and technical layers separated."""

    contract_version: str = "natal_report_v2"
    chart_id: uuid.UUID
    version: int
    status: str
    narrative_sections: list[NatalReportSectionV2]
    evidence_index: dict[str, dict[str, Any]]
    technical_basis: dict[str, Any]
    deterministic_payload: dict[str, Any]
    narrative_payload: dict[str, Any]
    assembled_payload: dict[str, Any]
