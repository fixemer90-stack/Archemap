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


@dataclass(frozen=True, slots=True)
class ScaleSemantics:
    zero: str
    hundred: str
    neutral: str = "balanced or insufficiently evidenced midpoint"


@dataclass(frozen=True, slots=True)
class ScoringRule:
    dimension: ParentStyleDimension
    contains: tuple[str, ...]
    signal_family: str
    weight: float
    time_sensitive: bool = False

    def matches(self, factor_key: str) -> bool:
        return all(token in factor_key for token in self.contains)


@dataclass(frozen=True, slots=True)
class ScoringPolicy:
    correlation_family_cap: float
    minimum_independent_families: int
    expected_independent_families: int


@dataclass(frozen=True, slots=True)
class DimensionEvidence:
    factor_key: str
    fact_id: UUID
    evidence_refs: tuple[str, ...]
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
    expected_family_count: int
    coverage: float
    agreement: float
    source_quality: float
    correlation_family_totals: tuple[tuple[str, float], ...]
    excluded_time_sensitive_refs: tuple[str, ...]


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
