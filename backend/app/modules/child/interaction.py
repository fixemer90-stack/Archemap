"""Deterministic eight-dimension parent-child interaction engine."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import replace
from math import isfinite
from typing import cast
from uuid import UUID

from app.modules.child.models import (
    ChildInteractionScore,
    ChildNeedScore,
    ChildParentStyleScore,
    ChildSynastryEvidence,
)
from app.modules.child.scoring.types import (
    ChildNeedDimension,
    DimensionBreakdown,
    DimensionEvidence,
    EvidenceDirection,
    InteractionDimension,
    InteractionPattern,
    InteractionResult,
    ParentStyleDimension,
)
from app.reference_data.child.child_needs_v1 import CHILD_NEEDS_REFERENCE_VERSION, CHILD_NEEDS_SCORING_VERSION
from app.reference_data.child.interaction_v1 import (
    CORRELATION_FAMILY_CAP,
    EXPECTED_INDEPENDENT_FAMILIES,
    FIT_RULES,
    INTERACTION_REFERENCE_VERSION,
    INTERACTION_SCORING_VERSION,
    MINIMUM_INDEPENDENT_FAMILIES,
    SATURN_DIMENSION_CAP,
)
from app.reference_data.child.parent_style_v1 import PARENT_STYLE_REFERENCE_VERSION, PARENT_STYLE_SCORING_VERSION

_INTERACTION_FACT_NAMESPACE = uuid.UUID("04785822-ed8b-505f-8051-c8ce978a437e")
_INTERACTION_ROW_NAMESPACE = uuid.UUID("d156b116-30af-5c5b-a911-0c91bd91f230")
_INTERACTION_FAMILY_NAMESPACE = uuid.UUID("58851186-cb43-5d50-a292-a37030e77365")


def score_interactions(
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    parent_chart_id: UUID,
    child_chart_version_id: UUID,
    parent_scores: Sequence[ChildParentStyleScore],
    child_need_scores: Sequence[ChildNeedScore],
    synastry_evidence: Sequence[ChildSynastryEvidence],
) -> tuple[InteractionResult, ...]:
    """Combine current persisted parent/child profiles with pair-bound synastry only."""

    parent = _validate_parent_scores(parent_scores, child_profile_id, generation_id, parent_chart_id)
    child = _validate_child_scores(child_need_scores, child_profile_id, generation_id, child_chart_version_id)
    pair = _validate_synastry(
        synastry_evidence,
        child_profile_id=child_profile_id,
        generation_id=generation_id,
        parent_chart_id=parent_chart_id,
        child_chart_version_id=child_chart_version_id,
    )
    by_dimension: dict[InteractionDimension, list[DimensionEvidence]] = defaultdict(list)
    pair_key = f"{child_profile_id}:{generation_id}:{parent_chart_id}:{child_chart_version_id}"

    for rule in FIT_RULES:
        parent_row = parent[rule.parent_dimension]
        child_row = child[rule.child_dimension]
        child_value = 100.0 - child_row.score if rule.invert_child else child_row.score
        fit = max(0.0, min(1.0, 1.0 - abs(parent_row.score - child_value) / 100.0))
        quality = min(parent_row.confidence, child_row.confidence)
        contribution = (fit - 0.5) * 2.0 * rule.weight * quality
        fact_key = f"fit:{rule.parent_dimension.value}:{rule.child_dimension.value}"
        fact_id = uuid.uuid5(_INTERACTION_FACT_NAMESPACE, f"{pair_key}:{fact_key}:{rule.dimension.value}")
        lineages = tuple(
            sorted(
                set(
                    (
                        *_score_lineages(parent_row, PARENT_STYLE_REFERENCE_VERSION),
                        *_score_lineages(child_row, CHILD_NEEDS_REFERENCE_VERSION),
                    )
                )
            )
        )
        by_dimension[rule.dimension].append(
            DimensionEvidence(
                factor_key=fact_key,
                fact_id=fact_id,
                evidence_refs=(
                    f"child_parent_style_scores:{parent_row.id}",
                    f"child_need_scores:{child_row.id}",
                ),
                lineage_refs=lineages,
                correlation_family=rule.signal_family,
                factor_value=round(fit, 6),
                source_quality=round(quality, 4),
                weight=rule.weight,
                contribution=contribution,
                direction=EvidenceDirection.SUPPORTS if contribution >= 0 else EvidenceDirection.COUNTERS,
            )
        )

    for row in pair:
        dimensions = cast(list[str], row.payload["dimensions"])
        family = cast(str, row.payload["correlation_family"])
        strength = float(cast(int | float, row.payload["strength"]))
        for dimension_value in dimensions:
            dimension = InteractionDimension(dimension_value)
            fact_id = uuid.uuid5(_INTERACTION_FACT_NAMESPACE, f"{pair_key}:{row.source_key}:{dimension.value}")
            by_dimension[dimension].append(
                DimensionEvidence(
                    factor_key=row.source_key,
                    fact_id=fact_id,
                    evidence_refs=(f"child_synastry_evidence:{row.id}",),
                    lineage_refs=(
                        cast(str, row.payload["parent_source_ref"]),
                        cast(str, row.payload["child_source_ref"]),
                    ),
                    correlation_family=family,
                    factor_value=strength,
                    source_quality=1.0,
                    weight=abs(row.contribution),
                    contribution=row.contribution,
                    direction=EvidenceDirection.SUPPORTS if row.contribution >= 0 else EvidenceDirection.COUNTERS,
                )
            )

    return tuple(_score_dimension(dimension, by_dimension[dimension]) for dimension in InteractionDimension)


def build_interaction_rows(
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    parent_chart_id: UUID,
    child_chart_version_id: UUID,
    results: Sequence[InteractionResult],
) -> tuple[ChildInteractionScore, ...]:
    """Build deterministic immutable current-version rows for one exact pair lineage."""

    if tuple(result.dimension for result in results) != tuple(InteractionDimension):
        raise ValueError("Interaction results must contain all canonical dimensions in order")
    if any(result.scoring_version != INTERACTION_SCORING_VERSION for result in results):
        raise ValueError("Interaction results use an unsupported scoring version")
    pair = f"{child_profile_id}:{generation_id}:{parent_chart_id}:{child_chart_version_id}"
    return tuple(
        ChildInteractionScore(
            id=uuid.uuid5(
                _INTERACTION_ROW_NAMESPACE,
                f"{pair}:{result.scoring_version}:{result.dimension.value}",
            ),
            child_profile_id=child_profile_id,
            parent_chart_id=parent_chart_id,
            child_chart_version_id=child_chart_version_id,
            generation_id=generation_id,
            dimension=result.dimension.value,
            score=result.score,
            confidence=result.confidence,
            pattern=result.pattern.value,
            scoring_version=result.scoring_version,
            evidence_refs=list(result.evidence_refs),
            breakdown={
                "reference_version": INTERACTION_REFERENCE_VERSION,
                "parent_style_scoring_version": PARENT_STYLE_SCORING_VERSION,
                "child_needs_scoring_version": CHILD_NEEDS_SCORING_VERSION,
                "pair_lineage": {
                    "child_profile_id": str(child_profile_id),
                    "generation_id": str(generation_id),
                    "parent_chart_id": str(parent_chart_id),
                    "child_chart_version_id": str(child_chart_version_id),
                },
                "supports": [_evidence_payload(item) for item in result.supports],
                "counters": [_evidence_payload(item) for item in result.counters],
                "confidence_components": {
                    "coverage": result.breakdown.coverage,
                    "agreement": result.breakdown.agreement,
                    "source_quality": result.breakdown.source_quality,
                },
                "raw_delta": result.breakdown.raw_delta,
                "independent_family_count": result.breakdown.independent_family_count,
                "required_family_count": result.breakdown.required_family_count,
                "independent_lineage_count": result.breakdown.independent_lineage_count,
                "independent_lineage_refs": list(result.breakdown.independent_lineage_refs),
                "required_lineage_count": result.breakdown.required_lineage_count,
                "expected_family_count": result.breakdown.expected_family_count,
                "correlation_family_totals": [
                    {"family": family, "contribution": contribution}
                    for family, contribution in result.breakdown.correlation_family_totals
                ],
            },
        )
        for result in results
    )


def _score_dimension(dimension: InteractionDimension, evidence: Sequence[DimensionEvidence]) -> InteractionResult:
    active = _canonicalize_fit_families([item for item in evidence if item.contribution != 0.0])
    capped = [item for item in _cap_correlated(active) if item.contribution != 0.0]
    families = {item.correlation_family for item in capped}
    lineages = {ref for item in capped if item.contribution != 0.0 for ref in item.lineage_refs}
    has_fit_signal = any(family.startswith("fit:") for family in families)
    enough = (
        has_fit_signal
        and len(families) >= MINIMUM_INDEPENDENT_FAMILIES
        and len(lineages) >= MINIMUM_INDEPENDENT_FAMILIES
    )
    raw_delta = max(-1.0, min(1.0, sum(item.contribution for item in capped)))
    score = round(50.0 + raw_delta * 50.0, 2) if enough else 50.0
    positive = sum(item.contribution for item in capped if item.contribution > 0)
    negative = abs(sum(item.contribution for item in capped if item.contribution < 0))
    total = positive + negative
    coverage = round(min(1.0, len(families) / EXPECTED_INDEPENDENT_FAMILIES), 4)
    agreement = round(max(positive, negative) / total, 4) if total else 0.0
    source_quality = (
        round(sum(abs(item.contribution) * item.source_quality for item in capped) / total, 4) if total else 0.0
    )
    confidence = round(coverage * agreement * source_quality, 4) if enough else 0.0
    ordered = tuple(sorted(capped, key=lambda item: (-abs(item.contribution), item.factor_key, str(item.fact_id))))
    supports = tuple(item for item in ordered if item.contribution >= 0)
    counters = tuple(item for item in ordered if item.contribution < 0)
    refs = tuple(sorted({ref for item in ordered for ref in item.evidence_refs}))
    family_totals = tuple(
        (family, round(sum(item.contribution for item in ordered if item.correlation_family == family), 6))
        for family in sorted(families)
    )
    return InteractionResult(
        dimension=dimension,
        score=score,
        confidence=confidence,
        pattern=_pattern(score),
        scoring_version=INTERACTION_SCORING_VERSION,
        supports=supports,
        counters=counters,
        evidence_refs=refs,
        breakdown=DimensionBreakdown(
            raw_delta=round(raw_delta, 6),
            independent_family_count=len(families),
            required_family_count=MINIMUM_INDEPENDENT_FAMILIES,
            independent_lineage_count=len(lineages),
            independent_lineage_refs=tuple(sorted(lineages)),
            required_lineage_count=MINIMUM_INDEPENDENT_FAMILIES,
            expected_family_count=EXPECTED_INDEPENDENT_FAMILIES,
            coverage=coverage,
            agreement=agreement,
            source_quality=source_quality,
            correlation_family_totals=family_totals,
            excluded_time_sensitive_refs=(),
        ),
    )


def _cap_correlated(evidence: Sequence[DimensionEvidence]) -> list[DimensionEvidence]:
    grouped: dict[str, list[DimensionEvidence]] = defaultdict(list)
    for item in evidence:
        grouped[item.correlation_family].append(item)
    capped: list[DimensionEvidence] = []
    for family in sorted(grouped):
        items = grouped[family]
        total = sum(item.contribution for item in items)
        cap = SATURN_DIMENSION_CAP if family == "pair:saturn-pressure" else CORRELATION_FAMILY_CAP
        bounded = max(-cap, min(cap, total))
        scale = bounded / total if total else 0.0
        capped.extend(replace(item, contribution=item.contribution * scale) for item in items)
    return capped


def _canonicalize_fit_families(evidence: Sequence[DimensionEvidence]) -> list[DimensionEvidence]:
    pair_evidence = [item for item in evidence if not item.correlation_family.startswith("fit:")]
    fit_evidence = [item for item in evidence if item.correlation_family.startswith("fit:")]
    deduplicated: dict[tuple[str, ...], DimensionEvidence] = {}
    for item in fit_evidence:
        identity = tuple(sorted(set(item.lineage_refs)))
        existing = deduplicated.get(identity)
        if existing is None or (-abs(item.contribution), item.factor_key, str(item.fact_id)) < (
            -abs(existing.contribution),
            existing.factor_key,
            str(existing.fact_id),
        ):
            deduplicated[identity] = item
    items = list(deduplicated.values())
    groups: list[set[int]] = []
    for index, item in enumerate(items):
        overlapping = {
            group_index
            for group_index, group in enumerate(groups)
            if any(set(items[member].lineage_refs) & set(item.lineage_refs) for member in group)
        }
        if not overlapping:
            groups.append({index})
            continue
        merged = {index}
        for group_index in sorted(overlapping, reverse=True):
            merged.update(groups.pop(group_index))
        groups.append(merged)
    canonical: list[DimensionEvidence] = []
    for group in groups:
        refs = sorted({ref for index in group for ref in items[index].lineage_refs})
        family = f"fit:lineage:{uuid.uuid5(_INTERACTION_FAMILY_NAMESPACE, '|'.join(refs))}"
        canonical.extend(replace(items[index], correlation_family=family) for index in sorted(group))
    return [*pair_evidence, *canonical]


def _score_lineages(row: ChildParentStyleScore | ChildNeedScore, reference_version: str) -> tuple[str, ...]:
    breakdown = row.breakdown
    if not isinstance(breakdown, dict) or breakdown.get("reference_version") != reference_version:
        raise ValueError("Score breakdown version is invalid")
    refs: set[str] = set()
    for key in ("supports", "counters"):
        leaves = breakdown.get(key)
        if not isinstance(leaves, list):
            raise ValueError("Score breakdown evidence is malformed")
        for leaf in leaves:
            if not isinstance(leaf, dict):
                raise ValueError("Score breakdown evidence is malformed")
            lineage_refs = leaf.get("lineage_refs")
            if (
                not isinstance(lineage_refs, list)
                or not lineage_refs
                or any(not isinstance(ref, str) or not ref for ref in lineage_refs)
                or len(lineage_refs) != len(set(lineage_refs))
            ):
                raise ValueError("Score breakdown lineage is malformed")
            refs.update(lineage_refs)
    if not refs:
        raise ValueError("Score breakdown has no underlying lineage")
    return tuple(sorted(refs))


def _validate_parent_scores(
    rows: Sequence[ChildParentStyleScore], child_profile_id: UUID, generation_id: UUID, parent_chart_id: UUID
) -> dict[ParentStyleDimension, ChildParentStyleScore]:
    expected = tuple(ParentStyleDimension)
    indexed = {ParentStyleDimension(row.dimension): row for row in rows}
    if set(indexed) != set(expected) or len(rows) != len(expected):
        raise ValueError("Parent Style inputs must contain current canonical dimensions")
    canonical = {dimension: indexed[dimension] for dimension in expected}
    for dimension, row in canonical.items():
        if (
            row.child_profile_id != child_profile_id
            or row.generation_id != generation_id
            or row.parent_chart_id != parent_chart_id
            or row.scoring_version != PARENT_STYLE_SCORING_VERSION
        ):
            raise ValueError(f"Parent Style lineage mismatch for {dimension.value}")
        _score_value(row.score)
        _confidence_value(row.confidence)
    return canonical


def _validate_child_scores(
    rows: Sequence[ChildNeedScore], child_profile_id: UUID, generation_id: UUID, child_chart_version_id: UUID
) -> dict[ChildNeedDimension, ChildNeedScore]:
    expected = tuple(ChildNeedDimension)
    indexed = {ChildNeedDimension(row.dimension): row for row in rows}
    if set(indexed) != set(expected) or len(rows) != len(expected):
        raise ValueError("Child Needs inputs must contain current canonical dimensions")
    canonical = {dimension: indexed[dimension] for dimension in expected}
    for dimension, row in canonical.items():
        if (
            row.child_profile_id != child_profile_id
            or row.generation_id != generation_id
            or row.child_chart_version_id != child_chart_version_id
            or row.scoring_version != CHILD_NEEDS_SCORING_VERSION
        ):
            raise ValueError(f"Child Needs lineage mismatch for {dimension.value}")
        _score_value(row.score)
        _confidence_value(row.confidence)
    return canonical


def _validate_synastry(
    rows: Sequence[ChildSynastryEvidence],
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    parent_chart_id: UUID,
    child_chart_version_id: UUID,
) -> tuple[ChildSynastryEvidence, ...]:
    unique: dict[str, ChildSynastryEvidence] = {}
    for row in rows:
        if (
            row.child_profile_id != child_profile_id
            or row.generation_id != generation_id
            or row.parent_chart_id != parent_chart_id
            or row.child_chart_version_id != child_chart_version_id
        ):
            raise ValueError("Synastry evidence lineage mismatch")
        if not isfinite(row.contribution) or not -1.0 <= row.contribution <= 1.0:
            raise ValueError("Synastry contribution must be finite and within range")
        if row.direction != ("supports" if row.contribution >= 0 else "counters"):
            raise ValueError("Synastry direction is incoherent")
        required = {
            "reference_version",
            "correlation_family",
            "factor_label",
            "dimensions",
            "strength",
            "parent_source_ref",
            "child_source_ref",
        }
        if not isinstance(row.payload, dict) or not required <= row.payload.keys():
            raise ValueError("Synastry payload is malformed")
        if row.payload["reference_version"] != "child-synastry-reference-1":
            raise ValueError("Synastry reference version mismatch")
        _confidence_value(row.payload["strength"])
        if row.source_key in unique:
            raise ValueError("Duplicate synastry source ownership")
        unique[row.source_key] = row
    return tuple(unique[key] for key in sorted(unique))


def _score_value(value: object) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(float(value))
        or not 0 <= value <= 100
    ):
        raise ValueError("score must be finite and within range")
    return float(value)


def _confidence_value(value: object) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(float(value))
        or not 0 <= value <= 1
    ):
        raise ValueError("confidence must be finite and within range")
    return float(value)


def _pattern(score: float) -> InteractionPattern:
    if score >= 60.0:
        return InteractionPattern.NATURAL_MATCH
    if score >= 35.0:
        return InteractionPattern.MODERATE_TENSION
    return InteractionPattern.HIGH_ATTENTION


def _evidence_payload(item: DimensionEvidence) -> dict[str, object]:
    return {
        "factor_key": item.factor_key,
        "fact_id": str(item.fact_id),
        "evidence_refs": list(item.evidence_refs),
        "lineage_refs": list(item.lineage_refs),
        "correlation_family": item.correlation_family,
        "factor_value": item.factor_value,
        "source_quality": item.source_quality,
        "weight": item.weight,
        "contribution": item.contribution,
        "direction": item.direction.value,
    }
