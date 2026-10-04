"""Typed Career narrative section input and output contracts."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CareerSectionRenderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = "career_section_render_input_v2"
    profile_id: UUID
    chart_id: UUID
    section_key: str
    section_title: str
    section_purpose: str
    owned_fact_keys: list[str] = Field(min_length=1)
    owned_facts: list[dict[str, Any]] = Field(min_length=1)
    reference_facts: list[dict[str, Any]]
    required_reference_fact_keys: list[str] = Field(default_factory=list)
    forbidden_fact_keys: list[str]
    style_contract: dict[str, Any]
    continuation_policy: dict[str, Any]


class CareerNarrativeClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    fact_keys: list[str] = Field(min_length=1)
    conditional: bool


class CareerSegmentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = "career_segment_output_v2"
    section_key: str
    title: str
    body: str = Field(min_length=1)
    cited_fact_keys: list[str] = Field(min_length=1)
    claims: list[CareerNarrativeClaim] = Field(min_length=1)
    continuation_complete: bool = True
    continuation_cursor: str | None = None
