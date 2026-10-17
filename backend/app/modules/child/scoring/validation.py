"""Semantic validation for persisted deterministic dimension breakdowns."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Any, cast
from uuid import UUID

from app.modules.child.scoring.types import ScaleSemantics, ScoringPolicy, ScoringRule

_EVIDENCE_KEYS = {
    "factor_key",
    "fact_id",
    "evidence_refs",
    "lineage_refs",
    "correlation_family",
    "factor_value",
    "source_quality",
    "weight",
    "contribution",
    "direction",
}


@dataclass(frozen=True, slots=True)
class PersistedBreakdownSemantics:
    evidence_refs: tuple[str, ...]
    score: float
    confidence: float


def validate_dimension_breakdown[DimensionT: StrEnum](
    breakdown: object,
    *,
    dimension: DimensionT,
    reference_version: str,
    scales: dict[DimensionT, ScaleSemantics],
    rules: Sequence[ScoringRule[DimensionT]],
    policy: ScoringPolicy,
) -> PersistedBreakdownSemantics | None:
    if not isinstance(breakdown, dict):
        return None
    required_keys = {
        "reference_version",
        "scale",
        "supports",
        "counters",
        "missing_families",
        "confidence_components",
        "raw_delta",
        "independent_family_count",
        "required_family_count",
        "independent_lineage_count",
        "independent_lineage_refs",
        "required_lineage_count",
        "expected_family_count",
        "correlation_family_totals",
        "excluded_time_sensitive_refs",
    }
    if breakdown.keys() != required_keys or breakdown["reference_version"] != reference_version:
        return None
    expected_scale = scales[dimension]
    if breakdown["scale"] != {
        "zero": expected_scale.zero,
        "hundred": expected_scale.hundred,
        "neutral": expected_scale.neutral,
    }:
        return None
    supports = breakdown["supports"]
    counters = breakdown["counters"]
    if not isinstance(supports, list) or not all(_valid_evidence(item, direction="supports") for item in supports):
        return None
    if not isinstance(counters, list) or not all(_valid_evidence(item, direction="counters") for item in counters):
        return None
    for key in ("missing_families", "independent_lineage_refs", "excluded_time_sensitive_refs"):
        if not _is_unique_string_list(breakdown[key], allow_empty=True):
            return None
    confidence_components = breakdown["confidence_components"]
    if not isinstance(confidence_components, dict) or not all(
        _is_finite_number(confidence_components.get(key), minimum=0.0, maximum=1.0)
        for key in ("coverage", "agreement", "source_quality")
    ):
        return None
    if not _is_finite_number(breakdown["raw_delta"], minimum=-1.0, maximum=1.0):
        return None
    count_keys = (
        "independent_family_count",
        "required_family_count",
        "independent_lineage_count",
        "required_lineage_count",
        "expected_family_count",
    )
    if not all(_is_nonnegative_int(breakdown[key]) for key in count_keys):
        return None
    if (
        breakdown["required_family_count"] != policy.minimum_independent_families
        or breakdown["required_lineage_count"] != policy.minimum_independent_families
        or breakdown["expected_family_count"] != policy.expected_independent_families
    ):
        return None

    evidence_items = cast(list[dict[str, Any]], [*supports, *counters])
    if not _evidence_matches_rules(
        evidence_items,
        dimension=dimension,
        rules=rules,
        correlation_family_cap=policy.correlation_family_cap,
    ):
        return None
    evidence_refs = tuple(sorted({ref for item in evidence_items for ref in cast(list[str], item["evidence_refs"])}))
    active_items = [item for item in evidence_items if float(item["contribution"]) != 0.0]
    active_families = {cast(str, item["correlation_family"]) for item in active_items}
    active_lineage_refs = tuple(sorted({ref for item in active_items for ref in cast(list[str], item["lineage_refs"])}))
    family_contributions: dict[str, float] = defaultdict(float)
    for item in active_items:
        family_contributions[cast(str, item["correlation_family"])] += float(item["contribution"])

    totals = breakdown["correlation_family_totals"]
    if not isinstance(totals, list):
        return None
    persisted_family_totals: dict[str, float] = {}
    for total in totals:
        if (
            not isinstance(total, dict)
            or not isinstance(total.get("family"), str)
            or not total["family"]
            or not _is_finite_number(total.get("contribution"), minimum=-1.0, maximum=1.0)
        ):
            return None
        family = cast(str, total["family"])
        if family in persisted_family_totals:
            return None
        persisted_family_totals[family] = float(total["contribution"])

    independent_family_count = cast(int, breakdown["independent_family_count"])
    independent_lineage_count = cast(int, breakdown["independent_lineage_count"])
    independent_lineage_refs = cast(list[str], breakdown["independent_lineage_refs"])
    if (
        independent_family_count != len(active_families)
        or independent_lineage_count != len(active_lineage_refs)
        or independent_lineage_refs != list(active_lineage_refs)
        or set(persisted_family_totals) != active_families
        or any(
            not _numbers_close(persisted_family_totals[family], round(contribution, 6), tolerance=1e-6)
            for family, contribution in family_contributions.items()
        )
    ):
        return None

    expected_families = {rule.signal_family for rule in rules if rule.dimension is dimension}
    if breakdown["missing_families"] != sorted(expected_families - active_families):
        return None

    contribution_sum = sum(float(item["contribution"]) for item in evidence_items)
    unrounded_raw_delta = max(-1.0, min(1.0, contribution_sum))
    if not _numbers_close(breakdown["raw_delta"], round(unrounded_raw_delta, 6), tolerance=1e-6):
        return None

    positive = sum(float(item["contribution"]) for item in evidence_items if float(item["contribution"]) > 0)
    negative = abs(sum(float(item["contribution"]) for item in evidence_items if float(item["contribution"]) < 0))
    total = positive + negative
    coverage = round(min(1.0, independent_family_count / policy.expected_independent_families), 4)
    if total == 0:
        agreement = 0.0
        source_quality = 0.0
    else:
        agreement = round(max(positive, negative) / total, 4)
        source_quality = round(
            sum(abs(float(item["contribution"])) * float(item["source_quality"]) for item in evidence_items) / total,
            4,
        )
    if any(
        not _numbers_close(confidence_components[key], expected, tolerance=1e-4)
        for key, expected in (
            ("coverage", coverage),
            ("agreement", agreement),
            ("source_quality", source_quality),
        )
    ):
        return None

    enough = (
        independent_family_count >= policy.minimum_independent_families
        and independent_lineage_count >= policy.minimum_independent_families
    )
    score = round(50.0 + unrounded_raw_delta * 50.0, 2) if enough else 50.0
    confidence = round(max(0.0, min(1.0, coverage * agreement * source_quality)), 4) if enough else 0.0
    return PersistedBreakdownSemantics(evidence_refs=evidence_refs, score=score, confidence=confidence)


def _valid_evidence(value: object, *, direction: str) -> bool:
    if not isinstance(value, dict) or value.keys() != _EVIDENCE_KEYS:
        return False
    if not all(isinstance(value[key], str) and value[key] for key in ("factor_key", "fact_id", "correlation_family")):
        return False
    try:
        UUID(value["fact_id"])
    except (TypeError, ValueError, AttributeError):
        return False
    if not _is_unique_string_list(value["evidence_refs"], allow_empty=False):
        return False
    if not _is_unique_string_list(value["lineage_refs"], allow_empty=False):
        return False
    if not _is_finite_number(value["factor_value"], minimum=0.0, maximum=1.0):
        return False
    if not _is_finite_number(value["source_quality"], minimum=0.0, maximum=1.0):
        return False
    if not _is_finite_number(value["weight"], minimum=-1.0, maximum=1.0):
        return False
    if not _is_finite_number(value["contribution"], minimum=-1.0, maximum=1.0):
        return False
    contribution = float(value["contribution"])
    return value["direction"] == direction and (contribution >= 0 if direction == "supports" else contribution < 0)


def _evidence_matches_rules[DimensionT: StrEnum](
    evidence_items: Sequence[dict[str, Any]],
    *,
    dimension: DimensionT,
    rules: Sequence[ScoringRule[DimensionT]],
    correlation_family_cap: float,
) -> bool:
    uncapped_by_family: dict[str, list[tuple[dict[str, Any], float]]] = defaultdict(list)
    for item in evidence_items:
        factor_key = cast(str, item["factor_key"])
        family = cast(str, item["correlation_family"])
        weight = float(item["weight"])
        matching = [
            rule
            for rule in rules
            if rule.dimension is dimension
            and rule.signal_family == family
            and rule.matches(factor_key)
            and _numbers_close(weight, rule.weight, tolerance=1e-9)
        ]
        if len(matching) != 1:
            return False
        uncapped_by_family[family].append((item, float(item["factor_value"]) * weight))

    for family_items in uncapped_by_family.values():
        total = sum(raw for _, raw in family_items)
        capped_total = max(-correlation_family_cap, min(correlation_family_cap, total))
        scale = capped_total / total if total else 0.0
        if any(not _numbers_close(item["contribution"], raw * scale, tolerance=1e-9) for item, raw in family_items):
            return False
    return True


def _is_finite_number(value: object, *, minimum: float, maximum: float) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and isfinite(float(value))
        and minimum <= float(value) <= maximum
    )


def _is_nonnegative_int(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _is_unique_string_list(value: object, *, allow_empty: bool) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value))
    )


def _numbers_close(value: object, expected: float, *, tolerance: float) -> bool:
    return (
        _is_finite_number(value, minimum=-1.0, maximum=100.0)
        and abs(float(cast(int | float, value)) - expected) <= tolerance
    )
