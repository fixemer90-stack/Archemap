"""Pure reusable deterministic dimension scoring for Child Report."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import replace

from app.modules.astrotype_v2.models import NatalFact, NatalFactEvidence
from app.modules.child.scoring.types import (
    DimensionBreakdown,
    DimensionEvidence,
    DimensionResult,
    EvidenceDirection,
    ParentStyleDimension,
    ScaleSemantics,
    ScoringPolicy,
    ScoringRule,
)


def score_dimensions(
    *,
    dimensions: Sequence[ParentStyleDimension],
    facts: Sequence[NatalFact],
    evidence: Sequence[NatalFactEvidence],
    rules: Sequence[ScoringRule],
    scale_semantics: dict[ParentStyleDimension, ScaleSemantics],
    scoring_version: str,
    policy: ScoringPolicy,
    allow_time_sensitive: bool,
) -> tuple[DimensionResult[ParentStyleDimension], ...]:
    """Score canonical dimensions from persisted facts and source links only."""

    evidence_by_fact = _validated_evidence(facts=facts, evidence=evidence)
    ordered_facts = sorted(facts, key=lambda fact: (fact.fact_key, str(fact.id)))
    return tuple(
        _score_dimension(
            dimension=dimension,
            facts=ordered_facts,
            evidence_by_fact=evidence_by_fact,
            rules=rules,
            scale=scale_semantics[dimension],
            scoring_version=scoring_version,
            policy=policy,
            allow_time_sensitive=allow_time_sensitive,
        )
        for dimension in dimensions
    )


def _validated_evidence(
    *,
    facts: Sequence[NatalFact],
    evidence: Sequence[NatalFactEvidence],
) -> dict[object, tuple[NatalFactEvidence, ...]]:
    fact_ids = {fact.id for fact in facts}
    chart_ids = {fact.chart_id for fact in facts}
    if None in fact_ids:
        raise ValueError("Persisted natal facts must have ids")
    if len(chart_ids) > 1:
        raise ValueError("All natal facts must belong to one parent chart")

    grouped: dict[object, list[NatalFactEvidence]] = defaultdict(list)
    for row in evidence:
        if row.id is None:
            raise ValueError("Persisted natal fact evidence must have ids")
        if row.fact_id not in fact_ids:
            raise ValueError("Natal fact evidence references a fact outside the input set")
        if chart_ids and row.chart_id not in chart_ids:
            raise ValueError("Natal fact evidence belongs to another chart")
        grouped[row.fact_id].append(row)
    return {
        fact_id: tuple(sorted(rows, key=lambda row: (row.source_table, row.source_key or "", str(row.id))))
        for fact_id, rows in grouped.items()
    }


def _score_dimension(
    *,
    dimension: ParentStyleDimension,
    facts: Sequence[NatalFact],
    evidence_by_fact: dict[object, tuple[NatalFactEvidence, ...]],
    rules: Sequence[ScoringRule],
    scale: ScaleSemantics,
    scoring_version: str,
    policy: ScoringPolicy,
    allow_time_sensitive: bool,
) -> DimensionResult[ParentStyleDimension]:
    dimension_rules = tuple(rule for rule in rules if rule.dimension is dimension)
    matched: list[DimensionEvidence] = []
    excluded_refs: set[str] = set()

    for fact in facts:
        source_rows = evidence_by_fact.get(fact.id, ())
        if not source_rows:
            continue
        refs = tuple(f"natal_fact:{fact.id}:evidence:{row.id}" for row in source_rows)
        for rule in dimension_rules:
            if not rule.matches(fact.fact_key):
                continue
            if (_fact_is_time_sensitive(fact) or rule.time_sensitive) and not allow_time_sensitive:
                excluded_refs.update(refs)
                continue
            contribution = _clamp(float(fact.weight), -1.0, 1.0) * rule.weight
            quality = _source_quality(fact, source_rows)
            matched.append(
                DimensionEvidence(
                    factor_key=fact.fact_key,
                    fact_id=fact.id,
                    evidence_refs=refs,
                    correlation_family=rule.signal_family,
                    factor_value=_clamp(float(fact.weight), -1.0, 1.0),
                    source_quality=quality,
                    weight=rule.weight,
                    contribution=contribution,
                    direction=(EvidenceDirection.SUPPORTS if contribution >= 0 else EvidenceDirection.COUNTERS),
                )
            )

    capped = _cap_correlated(matched, policy.correlation_family_cap)
    active_families = {item.correlation_family for item in capped if item.contribution != 0}
    raw_delta = _clamp(sum(item.contribution for item in capped), -1.0, 1.0)
    enough_evidence = len(active_families) >= policy.minimum_independent_families
    score = round(50.0 + raw_delta * 50.0, 2) if enough_evidence else 50.0
    coverage, agreement, source_quality, confidence = _confidence(capped, len(active_families), policy)
    if not enough_evidence:
        confidence = 0.0

    ordered = tuple(sorted(capped, key=_evidence_sort_key))
    supports = tuple(item for item in ordered if item.contribution >= 0)
    counters = tuple(item for item in ordered if item.contribution < 0)
    expected_families = {rule.signal_family for rule in dimension_rules}
    family_totals = tuple(
        (family, round(sum(item.contribution for item in ordered if item.correlation_family == family), 6))
        for family in sorted(active_families)
    )
    evidence_refs = tuple(sorted({ref for item in ordered for ref in item.evidence_refs}))

    return DimensionResult(
        dimension=dimension,
        score=_clamp(score, 0.0, 100.0),
        confidence=confidence,
        scoring_version=scoring_version,
        scale=scale,
        supports=supports,
        counters=counters,
        missing_families=tuple(sorted(expected_families - active_families)),
        evidence_refs=evidence_refs,
        breakdown=DimensionBreakdown(
            raw_delta=round(raw_delta, 6),
            independent_family_count=len(active_families),
            required_family_count=policy.minimum_independent_families,
            expected_family_count=policy.expected_independent_families,
            coverage=coverage,
            agreement=agreement,
            source_quality=source_quality,
            correlation_family_totals=family_totals,
            excluded_time_sensitive_refs=tuple(sorted(excluded_refs)),
        ),
    )


def _cap_correlated(evidence: Sequence[DimensionEvidence], cap: float) -> list[DimensionEvidence]:
    grouped: dict[str, list[DimensionEvidence]] = defaultdict(list)
    for item in evidence:
        grouped[item.correlation_family].append(item)

    capped: list[DimensionEvidence] = []
    for family in sorted(grouped):
        items = grouped[family]
        total = sum(item.contribution for item in items)
        capped_total = _clamp(total, -cap, cap)
        scale = capped_total / total if total else 0.0
        capped.extend(replace(item, contribution=item.contribution * scale) for item in items)
    return capped


def _confidence(
    evidence: Sequence[DimensionEvidence],
    family_count: int,
    policy: ScoringPolicy,
) -> tuple[float, float, float, float]:
    positive = sum(item.contribution for item in evidence if item.contribution > 0)
    negative = abs(sum(item.contribution for item in evidence if item.contribution < 0))
    total = positive + negative
    coverage = round(min(1.0, family_count / policy.expected_independent_families), 4)
    if total == 0:
        return coverage, 0.0, 0.0, 0.0
    agreement = round(max(positive, negative) / total, 4)
    source_quality = round(sum(abs(item.contribution) * item.source_quality for item in evidence) / total, 4)
    confidence = round(_clamp(coverage * agreement * source_quality, 0.0, 1.0), 4)
    return coverage, agreement, source_quality, confidence


def _source_quality(fact: NatalFact, evidence: Sequence[NatalFactEvidence]) -> float:
    evidence_quality = sum(_clamp(float(row.payload.get("source_quality", 1.0)), 0.0, 1.0) for row in evidence) / len(
        evidence
    )
    return round(_clamp(float(fact.confidence), 0.0, 1.0) * evidence_quality, 4)


def _fact_is_time_sensitive(fact: NatalFact) -> bool:
    key = fact.fact_key.lower()
    if fact.fact_type in {"house", "angle", "angularity"}:
        return True
    return any(token in key for token in ("ascendant", ":asc:", ":mc:", "midheaven"))


def _evidence_sort_key(item: DimensionEvidence) -> tuple[float, str, str, str]:
    return (-abs(item.contribution), item.factor_key, item.correlation_family, str(item.fact_id))


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
