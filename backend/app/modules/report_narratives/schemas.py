"""Pydantic schemas for structured report narratives."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

SelfSectionId = Literal[
    "main_formula",
    "world_perception",
    "emotions_and_communication",
    "strengths",
    "vulnerabilities",
    "relationships",
    "sexuality",
    "development",
]

SupportedProduct = Literal["self", "career", "love"]
SupportedLanguage = Literal["ru"]
BirthTimeQuality = Literal["exact", "approximate", "unknown"]


class NarrativeProfile(BaseModel):
    """Compact profile summary passed to the narrative layer."""

    name: str = Field(..., min_length=1, max_length=120)
    birth_date: date
    birth_time_quality: BirthTimeQuality
    birth_place: str = Field(..., min_length=1, max_length=300)


class CalculationQuality(BaseModel):
    """Deterministic calculation quality metadata."""

    has_exact_birth_time: bool
    has_known_birth_time: bool
    quality_label: str = Field(..., min_length=1, max_length=200)
    warning: str | None = Field(default=None, max_length=500)


class AstroFact(BaseModel):
    """Narrative-safe deterministic fact."""

    id: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=300)
    meaning: str = Field(..., min_length=1, max_length=1000)


class AspectFact(BaseModel):
    """Deterministic aspect summary for narrative input."""

    id: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=300)
    orb: str = Field(..., min_length=1, max_length=50)
    meaning: str = Field(..., min_length=1, max_length=1000)


class SocionicsSummary(BaseModel):
    """Short socionics summary prepared by the deterministic engine."""

    type: str = Field(..., min_length=1, max_length=20)
    type_ru: str = Field(..., min_length=1, max_length=20)
    confidence_label: str = Field(..., min_length=1, max_length=50)
    explanation: str = Field(..., min_length=1, max_length=500)


class ArchetypeSummary(BaseModel):
    """Short archetype summary prepared by the deterministic engine."""

    primary: str = Field(..., min_length=1, max_length=100)
    confidence_label: str = Field(..., min_length=1, max_length=50)
    explanation: str = Field(..., min_length=1, max_length=500)


class EvidenceBackedClaim(BaseModel):
    """Claim that must be backed by deterministic evidence IDs."""

    id: str = Field(..., min_length=1, max_length=120)
    claim: str = Field(..., min_length=1, max_length=1500)
    evidence_ids: list[str] = Field(..., min_length=1)


class DominantInsight(BaseModel):
    """Top-level chart/narrative dominant backed by deterministic evidence."""

    id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=1500)
    evidence_ids: list[str] = Field(..., min_length=1)


class MechanismStep(BaseModel):
    """One step in the user's inner psychological mechanism."""

    id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=1500)
    evidence_ids: list[str] = Field(..., min_length=1)


class InnerMechanism(BaseModel):
    """Step-by-step behavioral mechanism inferred from deterministic evidence."""

    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., min_length=1, max_length=1500)
    steps: list[MechanismStep] = Field(..., min_length=3, max_length=5)


class ProductBoundaries(BaseModel):
    """Product-level storytelling boundaries passed into the prompt."""

    career_policy: str = Field(..., min_length=1, max_length=1000)
    allowed_sections: list[SelfSectionId] = Field(..., min_length=1)


class NarrativeInput(BaseModel):
    """Curated DTO used as the only LLM input source."""

    product: SupportedProduct
    language: SupportedLanguage
    profile: NarrativeProfile
    calculation_quality: CalculationQuality
    key_facts: list[AstroFact]
    key_aspects: list[AspectFact]
    dominants: list[DominantInsight] = Field(..., min_length=1)
    inner_mechanism: InnerMechanism
    socionics: SocionicsSummary
    archetype: ArchetypeSummary
    strengths: list[EvidenceBackedClaim]
    risks: list[EvidenceBackedClaim]
    relationship_patterns: list[EvidenceBackedClaim]
    sexuality_patterns: list[EvidenceBackedClaim]
    development_recommendations: list[EvidenceBackedClaim]
    product_boundaries: ProductBoundaries


class EvidenceNote(BaseModel):
    """Visible narrative claim with evidence references."""

    claim: str = Field(..., min_length=1, max_length=1500)
    fact_ids: list[str] = Field(..., min_length=1)


class HeroSection(BaseModel):
    """Hero/intro block for the narrative report."""

    id: Literal["hero"]
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=4000)
    bullets: list[str] = Field(default_factory=list)
    evidence_notes: list[EvidenceNote] = Field(default_factory=list)


class NarrativeSection(BaseModel):
    """A named narrative section in the self report."""

    id: SelfSectionId
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=4000)
    bullets: list[str] = Field(default_factory=list)
    evidence_notes: list[EvidenceNote] = Field(default_factory=list)


class CareerCTA(BaseModel):
    """Career upsell block required in Self narrative."""

    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=1500)
    bullets: list[str] = Field(default_factory=list)
    button_label: str = Field(..., min_length=1, max_length=100)


class SelfNarrative(BaseModel):
    """Structured JSON output generated for a Self report."""

    title: str = Field(..., min_length=1, max_length=200)
    hero: HeroSection
    dominants: list[DominantInsight] = Field(..., min_length=1)
    inner_mechanism: InnerMechanism
    sections: list[NarrativeSection] = Field(..., min_length=1)
    career_cta: CareerCTA
    final_summary: str = Field(..., min_length=1, max_length=2000)
