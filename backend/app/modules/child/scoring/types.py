"""Shared deterministic scoring contracts for Child Report engines."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class EvidenceDirection(StrEnum):
    SUPPORTS = "supports"
    COUNTERS = "counters"


class ParentStyleDimension(StrEnum):
    EMOTIONAL_RESPONSIVENESS = "emotional_responsiveness"
    STRUCTURE = "structure"
    CONTROL_TENDENCY = "control_tendency"
    FLEXIBILITY = "flexibility"
    COMMUNICATION_STYLE = "communication_style"
    PROTECTION = "protection"
    AUTONOMY_SUPPORT = "autonomy_support"
    CONSISTENCY = "consistency"


class ChildNeedDimension(StrEnum):
    REASSURANCE = "reassurance"
    PREDICTABILITY = "predictability"
    AUTONOMY = "autonomy"
    VERBAL_EXPLANATION = "verbal_explanation"
    PHYSICAL_SENSORY_CALM = "physical_sensory_calm"
    EXPLORATION = "exploration"
    RECOGNITION = "recognition"
    PERSONAL_SPACE = "personal_space"
    TRANSITION_TIME = "transition_time"
    VARIETY = "variety"


class InteractionDimension(StrEnum):
    EMOTIONAL_ATTUNEMENT = "emotional_attunement"
    BOUNDARY_FIT = "boundary_fit"
    AUTONOMY_BALANCE = "autonomy_balance"
    COMMUNICATION_FIT = "communication_fit"
    TEMPO_FIT = "tempo_fit"
    CONFLICT_PATTERN = "conflict_pattern"
    SOOTHING_COMPATIBILITY = "soothing_compatibility"
    LEARNING_INTERACTION = "learning_interaction"


class InteractionPattern(StrEnum):
    NATURAL_MATCH = "natural_match"
    MODERATE_TENSION = "moderate_tension"
    HIGH_ATTENTION = "high_attention"


@dataclass(frozen=True, slots=True)
class ScaleSemantics:
    zero: str
    hundred: str
    neutral: str = "balanced or insufficiently evidenced midpoint"


@dataclass(frozen=True, slots=True)
class ScoringRule[DimensionT: StrEnum]:
    dimension: DimensionT
    contains: tuple[str, ...]
    signal_family: str
    weight: float
    time_sensitive: bool = False

    def matches(self, factor_key: str) -> bool:
        return all(
            factor_key.rsplit(":", 1)[-1] == token if token.startswith("house_") else token in factor_key
            for token in self.contains
        )


@dataclass(frozen=True, slots=True)
class ScoringPolicy:
    correlation_family_cap: float
    minimum_independent_families: int
    expected_independent_families: int


@dataclass(frozen=True, slots=True)
class ScoringFact:
    id: UUID
    fact_key: str
    fact_type: str
    weight: float
    confidence: float


@dataclass(frozen=True, slots=True)
class ScoringEvidence:
    id: UUID
    fact_id: UUID
    chart_id: UUID
    source_table: str
    source_id: UUID | None
    source_key: str | None
    source_quality: float


@dataclass(frozen=True, slots=True)
class DimensionEvidence:
    factor_key: str
    fact_id: UUID
    evidence_refs: tuple[str, ...]
    lineage_refs: tuple[str, ...]
    correlation_family: str
    factor_value: float
    source_quality: float
    weight: float
    contribution: float
    direction: EvidenceDirection


@dataclass(frozen=True, slots=True)
class DimensionBreakdown:
    raw_delta: float
    independent_family_count: int
    required_family_count: int
    independent_lineage_count: int
    independent_lineage_refs: tuple[str, ...]
    required_lineage_count: int
    expected_family_count: int
    coverage: float
    agreement: float
    source_quality: float
    correlation_family_totals: tuple[tuple[str, float], ...]
    excluded_time_sensitive_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InteractionResult:
    dimension: InteractionDimension
    score: float
    confidence: float
    pattern: InteractionPattern
    scoring_version: str
    supports: tuple[DimensionEvidence, ...]
    counters: tuple[DimensionEvidence, ...]
    evidence_refs: tuple[str, ...]
    breakdown: DimensionBreakdown


@dataclass(frozen=True, slots=True)
class DimensionResult[DimensionT: StrEnum]:
    dimension: DimensionT
    score: float
    confidence: float
    scoring_version: str
    scale: ScaleSemantics
    supports: tuple[DimensionEvidence, ...]
    counters: tuple[DimensionEvidence, ...]
    missing_families: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    breakdown: DimensionBreakdown
