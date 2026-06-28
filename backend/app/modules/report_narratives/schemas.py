"""Pydantic schemas for structured report narratives."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

DeepSynthesisSectionTarget = Literal[
    "main_formula",
    "world_perception",
    "emotions_and_communication",
    "strengths",
    "vulnerabilities",
    "relationships",
    "sexuality",
    "development",
]

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


class HouseScenario(BaseModel):
    """Life-scenario interpretation of an important house placement."""

    id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=200)
    placement: str = Field(..., min_length=1, max_length=300)
    need: str = Field(..., min_length=1, max_length=1000)
    manifestation: str = Field(..., min_length=1, max_length=1500)
    shadow: str = Field(..., min_length=1, max_length=1500)
    mature_expression: str = Field(..., min_length=1, max_length=1500)
    evidence_ids: list[str] = Field(..., min_length=1)
    evidence_notes: list[EvidenceNote] = Field(default_factory=list)


class CalibrationQuestion(BaseModel):
    """Question that helps the user verify whether a deep pattern fits lived experience."""

    id: str = Field(..., min_length=1, max_length=120)
    question: str = Field(..., min_length=1, max_length=500)
    evidence_ids: list[str] = Field(..., min_length=1)
    answer_type: Literal["yes_no", "scale_1_5", "free_text"]


class ContradictionInsight(BaseModel):
    """Central internal contradiction with a mature form of integration."""

    id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=200)
    tension: str = Field(..., min_length=1, max_length=1500)
    manifestation: str = Field(..., min_length=1, max_length=1500)
    mature_expression: str = Field(..., min_length=1, max_length=1500)
    evidence_ids: list[str] = Field(..., min_length=1)
    evidence_notes: list[EvidenceNote] = Field(default_factory=list)


class FailureMode(BaseModel):
    """Concrete behavioral failure mode with a supportive reframe."""

    id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=200)
    trigger: str = Field(..., min_length=1, max_length=1000)
    manifestation: str = Field(..., min_length=1, max_length=1500)
    supportive_reframe: str = Field(..., min_length=1, max_length=1500)
    evidence_ids: list[str] = Field(..., min_length=1)
    evidence_notes: list[EvidenceNote] = Field(default_factory=list)


class MaturityBand(BaseModel):
    """One maturity band for the same core pattern."""

    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=1500)
    evidence_ids: list[str] = Field(..., min_length=1)
    evidence_notes: list[EvidenceNote] = Field(default_factory=list)


class MaturityLevels(BaseModel):
    """Low / medium / high expression levels for the report's core pattern."""

    low: MaturityBand
    medium: MaturityBand
    high: MaturityBand


class ProductBoundaries(BaseModel):
    """Product-level storytelling boundaries passed into the prompt."""

    career_policy: str = Field(..., min_length=1, max_length=1000)
    allowed_sections: list[SelfSectionId] = Field(..., min_length=1)


class RankedAspect(BaseModel):
    """Deterministically ranked aspect used by staged narrative planning."""

    id: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=300)
    weight: float
    evidence_ids: list[str] = Field(..., min_length=1)
    section_targets: list[DeepSynthesisSectionTarget] = Field(..., min_length=1)


class AspectPattern(BaseModel):
    """Cluster of related aspects expressed as one chart pattern."""

    id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=200)
    aspect_ids: list[str] = Field(default_factory=list)
    planets: list[str] = Field(default_factory=list)
    pattern_type: Literal["support", "tension", "mixed", "integration"]
    psychological_mechanism: str = Field(..., min_length=1, max_length=1500)
    life_manifestation: str = Field(..., min_length=1, max_length=1500)
    risk: str = Field(..., min_length=1, max_length=1500)
    mature_expression: str = Field(..., min_length=1, max_length=1500)
    section_targets: list[DeepSynthesisSectionTarget] = Field(..., min_length=1)
    evidence_ids: list[str] = Field(..., min_length=1)
    weight: float


class HouseAxisPattern(BaseModel):
    """Deterministic life-axis pattern derived from house emphasis."""

    id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=200)
    axis: str = Field(..., min_length=1, max_length=300)
    mechanism: str = Field(..., min_length=1, max_length=1500)
    manifestation: str = Field(..., min_length=1, max_length=1500)
    evidence_ids: list[str] = Field(..., min_length=1)
    section_targets: list[DeepSynthesisSectionTarget] = Field(..., min_length=1)


class PlanetRole(BaseModel):
    """Narrative role assigned to a key planet placement."""

    id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=200)
    function: str = Field(..., min_length=1, max_length=1500)
    influence: str = Field(..., min_length=1, max_length=1500)
    section_targets: list[DeepSynthesisSectionTarget] = Field(..., min_length=1)
    evidence_ids: list[str] = Field(..., min_length=1)


class ChartDynamic(BaseModel):
    """Central dynamic explaining tension and compensation in the chart."""

    id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=200)
    mechanism: str = Field(..., min_length=1, max_length=1500)
    tension: str = Field(..., min_length=1, max_length=1500)
    compensation: str = Field(..., min_length=1, max_length=1500)
    section_targets: list[DeepSynthesisSectionTarget] = Field(..., min_length=1)
    evidence_ids: list[str] = Field(..., min_length=1)


class CalibrationHypothesis(BaseModel):
    """Evidence-backed hypothesis for future user calibration."""

    id: str = Field(..., min_length=1, max_length=120)
    hypothesis: str = Field(..., min_length=1, max_length=500)
    answer_type: Literal["yes_no", "scale_1_5", "free_text"]
    evidence_ids: list[str] = Field(..., min_length=1)


class DeepNatalSynthesis(BaseModel):
    """Deterministic pre-LLM synthesis layer for the staged narrative pipeline."""

    contract_version: str = Field(..., min_length=1, max_length=100)
    source_chart_snapshot_id: str = Field(..., min_length=1, max_length=200)
    evidence_map: dict[str, AstroFact | AspectFact] = Field(default_factory=dict)
    ranked_aspects: list[RankedAspect] = Field(default_factory=list)
    aspect_patterns: list[AspectPattern] = Field(default_factory=list)
    house_axis_patterns: list[HouseAxisPattern] = Field(default_factory=list)
    planet_roles: list[PlanetRole] = Field(default_factory=list)
    chart_dynamics: list[ChartDynamic] = Field(default_factory=list)
    contradictions: list[ContradictionInsight] = Field(default_factory=list)
    maturity_levels: MaturityLevels
    calibration_hypotheses: list[CalibrationHypothesis] = Field(default_factory=list)


class NarrativeInput(BaseModel):
    """Curated DTO used as the only LLM input source."""

    product: SupportedProduct
    language: SupportedLanguage
    profile: NarrativeProfile
    calculation_quality: CalculationQuality
    key_facts: list[AstroFact]
    key_aspects: list[AspectFact]
    deep_natal_synthesis: DeepNatalSynthesis | None = None
    dominants: list[DominantInsight] = Field(..., min_length=1)
    inner_mechanism: InnerMechanism
    house_scenarios: list[HouseScenario] = Field(default_factory=list)
    calibration_questions: list[CalibrationQuestion] = Field(..., min_length=5, max_length=7)
    contradictions: list[ContradictionInsight] = Field(..., min_length=3, max_length=5)
    failure_modes: list[FailureMode] = Field(..., min_length=3, max_length=5)
    maturity_levels: MaturityLevels
    socionics: SocionicsSummary
    archetype: ArchetypeSummary
    strengths: list[EvidenceBackedClaim]
    risks: list[EvidenceBackedClaim]
    relationship_patterns: list[EvidenceBackedClaim]
    sexuality_patterns: list[EvidenceBackedClaim]
    development_recommendations: list[EvidenceBackedClaim]
    product_boundaries: ProductBoundaries


class EvidenceNote(BaseModel):
    """Visible narrative claim with evidence references and optional limitation."""

    claim: str = Field(..., min_length=1, max_length=1500)
    fact_ids: list[str] = Field(..., min_length=1)
    interpretation: str | None = Field(default=None, max_length=1500)
    limitation: str | None = Field(default=None, max_length=1500)
    limitation_fact_ids: list[str] = Field(default_factory=list)


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
    house_scenarios: list[HouseScenario] = Field(..., min_length=1)
    calibration_questions: list[CalibrationQuestion] = Field(..., min_length=5, max_length=7)
    contradictions: list[ContradictionInsight] = Field(..., min_length=3, max_length=5)
    failure_modes: list[FailureMode] = Field(..., min_length=3, max_length=5)
    maturity_levels: MaturityLevels
    sections: list[NarrativeSection] = Field(..., min_length=1)
    career_cta: CareerCTA
    final_summary: str = Field(..., min_length=1, max_length=2000)
