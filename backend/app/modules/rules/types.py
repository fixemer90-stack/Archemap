"""Rule engine types — dataclasses for rules, claims, evidence, and confidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConditionOp(str, Enum):
    """Condition operators for rule evaluation."""
    GTE = "gte"
    LTE = "lte"
    GT = "gt"
    LT = "lt"
    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"


@dataclass(frozen=True, slots=True)
class Condition:
    """A single condition in a rule."""
    fact: str
    op: ConditionOp
    value: Any
    value_upper: Any = None


@dataclass(frozen=True, slots=True)
class ConditionGroup:
    """A group of conditions with conjunction (all/any/not)."""
    conjunction: str  # "all", "any", "not"
    conditions: list[ConditionGroup | Condition]


@dataclass(frozen=True, slots=True)
class ConfidenceAdjustment:
    """Confidence delta triggered by a condition."""
    when: Condition
    delta: float


@dataclass(frozen=True, slots=True)
class EvidenceSpec:
    """Evidence template specification."""
    template_key: str
    show_basis_features: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ArchetypeRule:
    """A single archetype rule from YAML."""
    archetype_id: str
    name: str
    description: str
    conditions: ConditionGroup
    effects: dict[str, float]
    confidence_adjustments: list[ConfidenceAdjustment] = field(default_factory=list)
    counter_rules: list[str] = field(default_factory=list)
    evidence: EvidenceSpec | None = None


@dataclass(frozen=True, slots=True)
class RuleSet:
    """Complete ruleset for a vertical."""
    product: str
    version: str
    effective_from: str
    locale: str = "ru-RU"
    archetypes: list[ArchetypeRule] = field(default_factory=list)
    scoring: dict[str, Any] = field(default_factory=dict)
    confidence_config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuleEvaluation:
    """Result of evaluating a single rule."""
    rule_id: str
    archetype_id: str
    activated: bool
    match_score: float
    contributions: dict[str, float]
    confidence_delta: float = 0.0
    matched_facts: list[tuple[str, Any, Any]] = field(default_factory=list)
    unmatched_facts: list[tuple[str, Any, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ConfidenceResult:
    """Computed confidence with reason codes."""
    value: float
    label: str
    reason_codes: list[str]
    factors: dict[str, float]


@dataclass(frozen=True, slots=True)
class BasisItem:
    """Evidence basis item."""
    rule_id: str
    feature: str
    value: float
    contribution: float


@dataclass(slots=True)
class Claim:
    """Interpretive claim with evidence trail."""
    claim_id: str
    section: str
    archetype: str
    score: float
    confidence: ConfidenceResult
    message: str
    basis: list[BasisItem] = field(default_factory=list)
    counter_evidence: list[BasisItem] = field(default_factory=list)
    provenance: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class InterpretationResult:
    """Complete interpretation output."""
    product: str
    primary_archetype: str
    primary_score: float
    primary_confidence: ConfidenceResult
    claims: list[Claim] = field(default_factory=list)
    all_archetype_scores: dict[str, float] = field(default_factory=dict)
    quality_warning: str | None = None
    provenance: dict[str, str] = field(default_factory=dict)
