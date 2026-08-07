"""Astrotype v2 bounded-context models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import BaseModel
from app.modules.profiles import models as _profiles_models  # noqa: F401 - register person_profiles metadata
from app.modules.users import models as _users_models  # noqa: F401 - register users metadata


class AspectDefinition(BaseModel):
    """Canonical definition of an astrological aspect used by v2."""

    __tablename__ = "astrotype_v2_aspect_definitions"
    __table_args__ = (UniqueConstraint("code", name="uq_astrotype_v2_aspect_definitions_code"),)

    code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    angle_degrees: Mapped[float] = mapped_column(Float, nullable=False)
    default_orb_degrees: Mapped[float] = mapped_column(Float, nullable=False)
    major: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class AspectPairInterpretation(BaseModel):
    """Deterministic reference interpretation for a planet-pair aspect."""

    __tablename__ = "astrotype_v2_aspect_pair_interpretations"
    __table_args__ = (
        UniqueConstraint(
            "aspect_code",
            "planet_a",
            "planet_b",
            "locale",
            "source_version",
            name="uq_astrotype_v2_aspect_pair_interpretation",
        ),
    )

    aspect_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    planet_a: Mapped[str] = mapped_column(String(40), nullable=False)
    planet_b: Mapped[str] = mapped_column(String(40), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="ru")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    source_version: Mapped[str] = mapped_column(String(40), nullable=False, default="v2.0")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


class NatalChart(BaseModel):
    """V2 normalized chart root keyed by existing platform user/profile."""

    __tablename__ = "astrotype_v2_natal_charts"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "engine_version",
            "input_hash",
            name="uq_astrotype_v2_natal_charts_profile_engine_input",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    engine_version: Mapped[str] = mapped_column(String(40), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    birth_datetime_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    house_system: Mapped[str] = mapped_column(String(10), nullable=False, default="P")
    calculation_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class NatalPlanetPosition(BaseModel):
    """One normalized planet/body position within a v2 natal chart."""

    __tablename__ = "astrotype_v2_natal_planet_positions"
    __table_args__ = (UniqueConstraint("chart_id", "body", name="uq_astrotype_v2_natal_planet_positions_chart_body"),)

    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(String(40), nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    sign: Mapped[str] = mapped_column(String(20), nullable=False)
    sign_degree: Mapped[float] = mapped_column(Float, nullable=False)
    house_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retrograde: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class NatalHouse(BaseModel):
    """One normalized house cusp within a v2 natal chart."""

    __tablename__ = "astrotype_v2_natal_houses"
    __table_args__ = (UniqueConstraint("chart_id", "house_number", name="uq_astrotype_v2_natal_houses_chart_house"),)

    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    house_number: Mapped[int] = mapped_column(Integer, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    sign: Mapped[str] = mapped_column(String(20), nullable=False)


class NatalAspect(BaseModel):
    """One normalized aspect within a v2 natal chart."""

    __tablename__ = "astrotype_v2_natal_aspects"
    __table_args__ = (
        UniqueConstraint(
            "chart_id",
            "body_a",
            "body_b",
            "aspect_code",
            name="uq_astrotype_v2_natal_aspects_chart_pair_code",
        ),
    )

    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body_a: Mapped[str] = mapped_column(String(40), nullable=False)
    body_b: Mapped[str] = mapped_column(String(40), nullable=False)
    aspect_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    angle_degrees: Mapped[float] = mapped_column(Float, nullable=False)
    orb_degrees: Mapped[float] = mapped_column(Float, nullable=False)
    applying: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    strength: Mapped[float | None] = mapped_column(Float, nullable=True)


class NatalChartBalance(BaseModel):
    """Aggregate deterministic balance metric for a v2 natal chart."""

    __tablename__ = "astrotype_v2_natal_chart_balances"
    __table_args__ = (
        UniqueConstraint("chart_id", "category", "key", name="uq_astrotype_v2_natal_chart_balances_chart_key"),
    )

    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    key: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)


class NatalChartPattern(BaseModel):
    """Detected deterministic natal chart pattern."""

    __tablename__ = "astrotype_v2_natal_chart_patterns"

    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pattern_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class NatalFact(BaseModel):
    """One deterministic natal fact used by v2 synthesis/report generation."""

    __tablename__ = "astrotype_v2_natal_facts"
    __table_args__ = (
        UniqueConstraint(
            "chart_id",
            "fact_key",
            "source_version",
            name="uq_astrotype_v2_natal_facts_chart_key_version",
        ),
    )

    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fact_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    polarity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    section_hint: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source_version: Mapped[str] = mapped_column(String(40), nullable=False, default="v2.0")


class NatalFactEvidence(BaseModel):
    """Source-row link explaining which deterministic chart entity supports a fact."""

    __tablename__ = "astrotype_v2_natal_fact_evidence"
    __table_args__ = (
        UniqueConstraint("fact_id", "source_table", "source_id", name="uq_astrotype_v2_natal_fact_evidence_source"),
    )

    fact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_facts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_table: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class NatalSynthesis(BaseModel):
    """Deterministic synthesis derived from v2 natal facts before LLM generation."""

    __tablename__ = "astrotype_v2_natal_syntheses"
    __table_args__ = (
        UniqueConstraint("chart_id", "source_version", name="uq_astrotype_v2_natal_syntheses_chart_version"),
    )

    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ready", index=True)
    facts_version: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source_version: Mapped[str] = mapped_column(String(40), nullable=False, default="v2.0")


class ReportOutline(BaseModel):
    """Deterministic outline and section plan for a v2 natal report."""

    __tablename__ = "astrotype_v2_report_outlines"
    __table_args__ = (
        UniqueConstraint("chart_id", "source_version", name="uq_astrotype_v2_report_outlines_chart_version"),
    )

    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ready", index=True)
    outline: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    section_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    source_version: Mapped[str] = mapped_column(String(40), nullable=False, default="v2.0")


class ReportSegmentGeneration(BaseModel):
    """LLM generation artifact for one report section/segment."""

    __tablename__ = "astrotype_v2_report_segment_generations"
    __table_args__ = (
        UniqueConstraint("outline_id", "section_key", name="uq_astrotype_v2_report_segments_outline_section"),
    )

    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    outline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("astrotype_v2_report_outlines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", index=True)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class NatalInfographicData(BaseModel):
    """Deterministic calculation-layer view-model data for the canonical v2 sample UI."""

    __tablename__ = "astrotype_v2_natal_infographic_data"
    __table_args__ = (
        UniqueConstraint("chart_id", "source_version", name="uq_astrotype_v2_natal_infographic_data_chart_version"),
    )

    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ready", index=True)
    calculation_layer: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source_version: Mapped[str] = mapped_column(String(40), nullable=False, default="v2.0")


class NatalReport(BaseModel):
    """Versioned v2 report artifact with deterministic and narrative payloads separated."""

    __tablename__ = "astrotype_v2_natal_reports"
    __table_args__ = (UniqueConstraint("chart_id", "version", name="uq_astrotype_v2_natal_reports_chart_version"),)

    chart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    synthesis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("astrotype_v2_natal_syntheses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    outline_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("astrotype_v2_report_outlines.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    infographic_data_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("astrotype_v2_natal_infographic_data.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="deterministic_ready", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    deterministic_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    narrative_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    assembled_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
