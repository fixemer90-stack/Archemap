"""Pure deterministic Career factor and dimension scoring engine."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from uuid import UUID

from app.modules.astrotype_v2.models import NatalFact
from app.modules.career.factor_catalog import (
    CAREER_SCORING_VERSION,
    CORRELATION_FAMILY_CAP,
    EXPECTED_INDEPENDENT_FAMILIES,
    FACTOR_RULES,
    MIN_INDEPENDENT_FAMILIES,
)
from app.modules.career.schemas import CareerDimensionKey, EvidenceDirection


@dataclass(frozen=True)
class CareerFactor:
    factor_key: str
    source_type: str
    source_id: UUID
    correlation_family: str
    value: float
    quality: float


@dataclass(frozen=True)
class DimensionEvidence:
    factor_key: str
    source_type: str
    source_id: UUID
    correlation_family: str
    factor_value: float
    source_quality: float
    weight: float
    contribution: float
    direction: EvidenceDirection


@dataclass(frozen=True)
class CareerDimensionResult:
    dimension: CareerDimensionKey
    score: float
    confidence: float
    scoring_version: str
    evidence: tuple[DimensionEvidence, ...]


def score_career_dimensions(facts: Sequence[NatalFact]) -> tuple[CareerDimensionResult, ...]:
    """Score all MVP dimensions from persisted deterministic natal facts."""
    factors = tuple(sorted((_factor_from_fact(fact) for fact in facts), key=_factor_sort_key))
    return tuple(_score_dimension(dimension, factors) for dimension in sorted(CareerDimensionKey, key=str))


def _factor_from_fact(fact: NatalFact) -> CareerFactor:
    if fact.id is None:
        raise ValueError("Persisted natal fact must have an id")
    return CareerFactor(
        factor_key=fact.fact_key,
        source_type="natal_fact",
        source_id=fact.id,
        correlation_family=_correlation_family(fact.fact_key, fact.fact_type),
        value=_clamp(float(fact.weight), -1.0, 1.0),
        quality=_clamp(float(fact.confidence), 0.0, 1.0),
    )


def _score_dimension(
    dimension: CareerDimensionKey,
    factors: Sequence[CareerFactor],
) -> CareerDimensionResult:
    evidence = [
        DimensionEvidence(
            factor_key=factor.factor_key,
            source_type=factor.source_type,
            source_id=factor.source_id,
            correlation_family=factor.correlation_family,
            factor_value=factor.value,
            source_quality=factor.quality,
            weight=rule.weight,
            contribution=factor.value * rule.weight,
            direction=_direction(factor.value * rule.weight),
        )
        for factor in factors
        for rule in FACTOR_RULES
        if rule.dimension is dimension and rule.matches(factor.factor_key)
    ]
    capped = _cap_correlated_evidence(evidence)
    families = {item.correlation_family for item in capped if item.contribution != 0}
    raw_score = _clamp(sum(item.contribution for item in capped), -1.0, 1.0)
    score = 50.0 if len(families) < MIN_INDEPENDENT_FAMILIES else round(50.0 + raw_score * 50.0, 2)
    confidence = _confidence(capped, len(families))
    ordered = tuple(sorted(capped, key=lambda item: (-abs(item.contribution), item.factor_key, str(item.source_id))))
    return CareerDimensionResult(
        dimension=dimension,
        score=score,
        confidence=confidence,
        scoring_version=CAREER_SCORING_VERSION,
        evidence=ordered,
    )


def _cap_correlated_evidence(evidence: Sequence[DimensionEvidence]) -> list[DimensionEvidence]:
    by_family: dict[str, list[DimensionEvidence]] = defaultdict(list)
    for item in evidence:
        by_family[item.correlation_family].append(item)

    capped: list[DimensionEvidence] = []
    for family in sorted(by_family):
        items = by_family[family]
        total = sum(item.contribution for item in items)
        capped_total = _clamp(total, -CORRELATION_FAMILY_CAP, CORRELATION_FAMILY_CAP)
        scale = capped_total / total if total else 0.0
        capped.extend(replace(item, contribution=item.contribution * scale) for item in items)
    return capped


def _confidence(evidence: Sequence[DimensionEvidence], family_count: int) -> float:
    if family_count < MIN_INDEPENDENT_FAMILIES:
        return 0.0
    positive = sum(item.contribution for item in evidence if item.contribution > 0)
    negative = abs(sum(item.contribution for item in evidence if item.contribution < 0))
    total = positive + negative
    if total == 0:
        return 0.0
    agreement = max(positive, negative) / total
    coverage = min(1.0, family_count / EXPECTED_INDEPENDENT_FAMILIES)
    quality = sum(abs(item.contribution) * item.source_quality for item in evidence) / total
    return round(_clamp(coverage * agreement * quality, 0.0, 1.0), 4)


def _direction(contribution: float) -> EvidenceDirection:
    if contribution > 0:
        return EvidenceDirection.SUPPORTS
    if contribution < 0:
        return EvidenceDirection.COUNTERS
    return EvidenceDirection.MISSING


def _correlation_family(factor_key: str, fact_type: str) -> str:
    parts = factor_key.split(":")
    if fact_type == "placement" and len(parts) >= 2:
        return f"planet:{parts[1]}"
    if fact_type == "aspect" and len(parts) >= 3:
        return f"aspect:{parts[1]}:{parts[2]}"
    if fact_type == "balance" and len(parts) >= 2:
        return f"balance:{parts[1]}"
    if fact_type == "pattern" and len(parts) >= 2:
        return f"pattern:{parts[1]}"
    return f"{fact_type}:{factor_key}"


def _factor_sort_key(factor: CareerFactor) -> tuple[str, str]:
    return factor.factor_key, str(factor.source_id)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
