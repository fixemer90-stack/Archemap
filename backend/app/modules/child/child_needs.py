"""Deterministic Child Needs scoring from one pinned immutable child chart."""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from math import isfinite
from typing import Any, cast
from uuid import UUID

from app.modules.child.birth_time_policy import (
    APPROXIMATE_SAMPLE_OFFSETS_MINUTES,
    APPROXIMATE_WINDOW_MINUTES,
    canonical_excluded_fact_families,
    resolve_birth_time_policy,
)
from app.modules.child.models import ChildChartVersion, ChildNeedScore
from app.modules.child.scoring.engine import score_dimensions
from app.modules.child.scoring.types import (
    ChildNeedDimension,
    DimensionEvidence,
    DimensionResult,
    ScoringEvidence,
    ScoringFact,
)
from app.reference_data.child.child_needs_v1 import (
    CHILD_NEEDS_POLICY,
    CHILD_NEEDS_REFERENCE_VERSION,
    CHILD_NEEDS_RULES,
    CHILD_NEEDS_SCALES,
    CHILD_NEEDS_SCORING_VERSION,
)

ChildNeedResult = DimensionResult[ChildNeedDimension]
_CHILD_NEED_ROW_NAMESPACE = uuid.UUID("41e1581b-b645-5d5f-b9c7-e88946f01d82")
_CHILD_FACT_NAMESPACE = uuid.UUID("548965fe-849d-5a13-a355-e1ed12577f64")
_CHILD_EVIDENCE_NAMESPACE = uuid.UUID("92590590-b68f-51ec-99f4-059d19ec7223")
_POLICY_VERSION = "child-birth-time-policy-v3"
_ELEMENTS = {
    "aries": "fire",
    "leo": "fire",
    "sagittarius": "fire",
    "taurus": "earth",
    "virgo": "earth",
    "capricorn": "earth",
    "gemini": "air",
    "libra": "air",
    "aquarius": "air",
    "cancer": "water",
    "scorpio": "water",
    "pisces": "water",
}
_MODALITIES = {
    "aries": "cardinal",
    "cancer": "cardinal",
    "libra": "cardinal",
    "capricorn": "cardinal",
    "taurus": "fixed",
    "leo": "fixed",
    "scorpio": "fixed",
    "aquarius": "fixed",
    "gemini": "mutable",
    "virgo": "mutable",
    "sagittarius": "mutable",
    "pisces": "mutable",
}


def score_child_needs(*, chart: ChildChartVersion) -> tuple[ChildNeedResult, ...]:
    """Return all canonical Child Needs dimensions from one pinned chart artifact."""

    facts, evidence, allow_time_sensitive = _facts_from_pinned_chart(chart)
    return score_dimensions(
        dimensions=tuple(ChildNeedDimension),
        facts=facts,
        evidence=evidence,
        rules=CHILD_NEEDS_RULES,
        scale_semantics=CHILD_NEEDS_SCALES,
        scoring_version=CHILD_NEEDS_SCORING_VERSION,
        policy=CHILD_NEEDS_POLICY,
        allow_time_sensitive=allow_time_sensitive,
    )


def build_child_need_rows(
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    child_chart_version_id: UUID,
    results: Sequence[ChildNeedResult],
) -> tuple[ChildNeedScore, ...]:
    """Build exactly ten immutable versioned rows without database side effects."""

    expected = tuple(ChildNeedDimension)
    if tuple(result.dimension for result in results) != expected:
        raise ValueError("Child Needs results must contain all canonical dimensions in order")
    if any(result.scoring_version != CHILD_NEEDS_SCORING_VERSION for result in results):
        raise ValueError("Child Needs results use an unsupported scoring version")

    return tuple(
        ChildNeedScore(
            id=uuid.uuid5(
                _CHILD_NEED_ROW_NAMESPACE,
                f"{child_profile_id}:{generation_id}:{child_chart_version_id}:{result.scoring_version}:{result.dimension.value}",
            ),
            child_profile_id=child_profile_id,
            child_chart_version_id=child_chart_version_id,
            generation_id=generation_id,
            dimension=result.dimension.value,
            score=result.score,
            confidence=result.confidence,
            scoring_version=result.scoring_version,
            evidence_refs=list(result.evidence_refs),
            breakdown={
                "reference_version": CHILD_NEEDS_REFERENCE_VERSION,
                "scale": {
                    "zero": result.scale.zero,
                    "hundred": result.scale.hundred,
                    "neutral": result.scale.neutral,
                },
                "supports": [_evidence_payload(item) for item in result.supports],
                "counters": [_evidence_payload(item) for item in result.counters],
                "missing_families": list(result.missing_families),
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
                "excluded_time_sensitive_refs": list(result.breakdown.excluded_time_sensitive_refs),
            },
        )
        for result in results
    )


def _facts_from_pinned_chart(
    chart: ChildChartVersion,
) -> tuple[tuple[ScoringFact, ...], tuple[ScoringEvidence, ...], bool]:
    payload = chart.calculation_payload
    if not isinstance(payload, dict) or not _valid_confidence_provenance(chart, payload):
        return (), (), False
    raw_positions = payload.get("planet_positions")
    raw_aspects = payload.get("aspects")
    if not isinstance(raw_positions, list) or not isinstance(raw_aspects, list):
        return (), (), False
    positions = _deduplicate_positions(raw_positions)
    aspects = _deduplicate_aspects(raw_aspects)
    if positions is None or aspects is None:
        return (), (), False

    stable_facts = _stable_fact_map(chart, payload)
    if stable_facts is None:
        return (), (), False
    exact = chart.birth_time_confidence == "exact"
    expected_sample_count = 5 if chart.birth_time_confidence == "approximate" else 3
    facts: list[ScoringFact] = []
    evidence: list[ScoringEvidence] = []
    signs: list[str] = []
    placement_sources: list[tuple[str, float]] = []

    for raw in positions:
        body = raw.get("body")
        sign = raw.get("sign")
        if not isinstance(body, str) or not body or not isinstance(sign, str) or sign.lower() not in _ELEMENTS:
            return (), (), False
        if chart.birth_time_confidence == "unknown" and body.strip().casefold() == "moon":
            continue
        stability_key = f"planet_sign:{body}"
        quality = (
            1.0
            if exact
            else _stable_quality(
                stable_facts,
                stability_key,
                expected_sample_count=expected_sample_count,
                expected_value=sign,
            )
        )
        if (
            chart.birth_time_confidence == "approximate"
            and body.strip().casefold() == "moon"
            and "stable_moon_sign" not in chart.allowed_fact_families
        ):
            quality = None
        if quality is None:
            continue
        house = raw.get("house_number") if exact else None
        if house is not None and (isinstance(house, bool) or not isinstance(house, int) or not 1 <= house <= 12):
            return (), (), False
        fact_key = f"placement:{body.lower()}:{sign.lower()}:" + (f"house_{house}" if house is not None else "no_house")
        fact, row = _fact_with_evidence(
            chart=chart,
            fact_key=fact_key,
            fact_type="placement",
            weight=1.0,
            confidence=quality,
            source_key=f"planet_positions:{body}",
        )
        facts.append(fact)
        evidence.append(row)
        signs.append(sign.lower())
        placement_sources.append((f"planet_positions:{body}", quality))

    for raw in aspects:
        body_a = raw.get("body_a")
        body_b = raw.get("body_b")
        code = raw.get("aspect_code")
        if not all(isinstance(value, str) and value for value in (body_a, body_b, code)):
            return (), (), False
        if chart.birth_time_confidence == "unknown" and any(
            cast(str, value).strip().casefold() == "moon" for value in (body_a, body_b)
        ):
            continue
        first, second = sorted((cast(str, body_a).lower(), cast(str, body_b).lower()))
        stability_key = (
            f"aspect:{min(cast(str, body_a), cast(str, body_b))}:{max(cast(str, body_a), cast(str, body_b))}:{code}"
        )
        quality = (
            1.0
            if exact
            else _stable_quality(
                stable_facts,
                stability_key,
                expected_sample_count=expected_sample_count,
                expected_value=True,
            )
        )
        if quality is None:
            continue
        fact_key = f"aspect:{first}:{second}:{cast(str, code).lower()}"
        fact, row = _fact_with_evidence(
            chart=chart,
            fact_key=fact_key,
            fact_type="aspect",
            weight=1.0,
            confidence=quality,
            source_key=f"aspects:{first}:{second}:{cast(str, code).lower()}",
        )
        facts.append(fact)
        evidence.append(row)

    if len(signs) >= 4:
        denominator = len(signs)
        for family, mapping in (("element", _ELEMENTS), ("modality", _MODALITIES)):
            counts = Counter(mapping[sign] for sign in signs)
            for name, count in sorted(counts.items()):
                fact_key = f"balance:{family}:{name}"
                fact = _scoring_fact(
                    chart=chart,
                    fact_key=fact_key,
                    fact_type="balance",
                    weight=count / denominator,
                    confidence=min(quality for _, quality in placement_sources),
                )
                facts.append(fact)
                evidence.extend(
                    _scoring_evidence(
                        chart=chart,
                        fact=fact,
                        fact_key=fact_key,
                        source_key=source_key,
                        source_quality=quality,
                    )
                    for source_key, quality in placement_sources
                )

    return tuple(facts), tuple(evidence), exact


def _valid_confidence_provenance(chart: ChildChartVersion, payload: dict[str, Any]) -> bool:
    if payload.get("contract_version") != _POLICY_VERSION:
        return False
    technical = payload.get("technical_reference")
    stability = payload.get("stability_evidence")
    if not isinstance(technical, dict) or not isinstance(stability, dict):
        return False
    if stability.get("policy_version") != _POLICY_VERSION:
        return False
    confidence = chart.birth_time_confidence
    try:
        policy = resolve_birth_time_policy(confidence)
    except ValueError:
        return False
    allowed = chart.allowed_fact_families
    if not isinstance(allowed, list) or allowed != list(policy.allowed_fact_families):
        return False
    if chart.uncertainty_reason != policy.uncertainty_reason:
        return False
    facts = stability.get("facts")
    if confidence == "exact":
        unstable_facts: tuple[str, ...] = ()
    elif not isinstance(facts, dict) or not all(
        isinstance(key, str) and isinstance(value, dict) and isinstance(value.get("stable"), bool)
        for key, value in facts.items()
    ):
        return False
    else:
        unstable_facts = tuple(sorted(key for key, value in facts.items() if value["stable"] is False))
    expected_exclusions = list(canonical_excluded_fact_families(policy, unstable_facts))
    persisted_exclusions = chart.excluded_fact_families
    payload_exclusions = payload.get("exclusions")
    if not _is_unique_string_list(persisted_exclusions) or persisted_exclusions != expected_exclusions:
        return False
    if not _is_unique_string_list(payload_exclusions) or payload_exclusions != expected_exclusions:
        return False
    birth_datetime = _parse_aware_datetime(technical.get("birth_datetime_utc"))
    if birth_datetime is None:
        return False
    marker = technical.get("birth_time_confidence")
    if marker is not None and marker != confidence:
        return False
    if confidence == "exact":
        return (
            technical.get("user_supplied_time") is True
            and technical.get("synthetic_noon") is False
            and stability.get("exact_input") is True
        )
    if confidence == "approximate":
        return (
            technical.get("user_supplied_time") is True
            and technical.get("synthetic_noon") is False
            and _valid_approximate_stability_proof(stability, birth_datetime)
        )
    if confidence == "unknown":
        return (
            technical.get("user_supplied_time") is False
            and technical.get("synthetic_noon") is True
            and _valid_unknown_stability_proof(stability, birth_datetime)
        )
    return False


def _stable_fact_map(chart: ChildChartVersion, payload: dict[str, Any]) -> dict[str, Any] | None:
    if chart.birth_time_confidence == "exact":
        return {}
    stability = payload.get("stability_evidence")
    if not isinstance(stability, dict) or not isinstance(stability.get("facts"), dict):
        return None
    return cast(dict[str, Any], stability["facts"])


def _valid_approximate_stability_proof(stability: dict[str, Any], center: datetime) -> bool:
    sample_datetimes = _parse_sample_datetimes(stability.get("sample_datetimes_utc"))
    expected = [center + timedelta(minutes=offset) for offset in APPROXIMATE_SAMPLE_OFFSETS_MINUTES]
    return (
        stability.get("window_minutes") == APPROXIMATE_WINDOW_MINUTES
        and stability.get("sample_offsets_minutes") == list(APPROXIMATE_SAMPLE_OFFSETS_MINUTES)
        and sample_datetimes == expected
    )


def _valid_unknown_stability_proof(stability: dict[str, Any], technical_reference: datetime) -> bool:
    sample_datetimes = _parse_sample_datetimes(stability.get("sample_datetimes_utc"))
    return (
        stability.get("window") == "local_birth_date"
        and sample_datetimes is not None
        and len(sample_datetimes) == 3
        and sample_datetimes[0] < sample_datetimes[1] < sample_datetimes[2]
        and sample_datetimes[1] == technical_reference
    )


def _stable_quality(
    facts: dict[str, Any],
    key: str,
    *,
    expected_sample_count: int,
    expected_value: object,
) -> float | None:
    value = facts.get(key)
    if not isinstance(value, dict) or value.get("stable") is not True:
        return None
    observed_values = value.get("observed_values")
    sample_count = value.get("sample_count")
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count != expected_sample_count
        or not isinstance(observed_values, list)
        or len(observed_values) != sample_count
        or any(item != expected_value for item in observed_values)
    ):
        return None
    quality = value.get("confidence")
    if isinstance(quality, bool) or not isinstance(quality, (int, float)):
        raise ValueError("stability confidence must be finite and within [0, 1]")
    numeric = float(quality)
    if not isfinite(numeric) or not 0.0 <= numeric <= 1.0:
        raise ValueError("stability confidence must be finite and within [0, 1]")
    if numeric != 1.0:
        return None
    return numeric


def _is_unique_string_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value))
    )


def _parse_aware_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _parse_sample_datetimes(value: object) -> list[datetime] | None:
    if not isinstance(value, list):
        return None
    parsed = [_parse_aware_datetime(item) for item in value]
    if any(item is None for item in parsed):
        return None
    return [cast(datetime, item) for item in parsed]


def _deduplicate_positions(values: list[object]) -> list[dict[str, Any]] | None:
    unique: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for value in values:
        if not isinstance(value, dict):
            return None
        body = value.get("body")
        if not isinstance(body, str) or not body.strip():
            return None
        canonical_body = body.strip().casefold()
        normalized = dict(value)
        normalized["body"] = canonical_body
        sign = normalized.get("sign")
        if isinstance(sign, str):
            normalized["sign"] = sign.strip().casefold()
        existing = unique.get(canonical_body)
        if existing is not None:
            if existing[1] != normalized:
                return None
            continue
        unique[canonical_body] = (value, normalized)
    return [unique[key][0] for key in sorted(unique)]


def _deduplicate_aspects(values: list[object]) -> list[dict[str, Any]] | None:
    unique: dict[tuple[str, str, str], tuple[dict[str, Any], dict[str, Any]]] = {}
    for value in values:
        if not isinstance(value, dict):
            return None
        body_a = value.get("body_a")
        body_b = value.get("body_b")
        code = value.get("aspect_code")
        if not all(isinstance(item, str) and item.strip() for item in (body_a, body_b, code)):
            return None
        first, second = sorted((cast(str, body_a).strip().casefold(), cast(str, body_b).strip().casefold()))
        canonical_code = cast(str, code).strip().casefold()
        key = (first, second, canonical_code)
        normalized = dict(value)
        normalized.update({"body_a": first, "body_b": second, "aspect_code": canonical_code})
        existing = unique.get(key)
        if existing is not None:
            if existing[1] != normalized:
                return None
            continue
        unique[key] = (value, normalized)
    return [unique[key][0] for key in sorted(unique)]


def _fact_with_evidence(
    *,
    chart: ChildChartVersion,
    fact_key: str,
    fact_type: str,
    weight: float,
    confidence: float,
    source_key: str,
) -> tuple[ScoringFact, ScoringEvidence]:
    fact = _scoring_fact(
        chart=chart,
        fact_key=fact_key,
        fact_type=fact_type,
        weight=weight,
        confidence=confidence,
    )
    return (
        fact,
        _scoring_evidence(
            chart=chart,
            fact=fact,
            fact_key=fact_key,
            source_key=source_key,
            source_quality=confidence,
        ),
    )


def _scoring_fact(
    *, chart: ChildChartVersion, fact_key: str, fact_type: str, weight: float, confidence: float
) -> ScoringFact:
    return ScoringFact(
        uuid.uuid5(_CHILD_FACT_NAMESPACE, f"{chart.id}:{fact_key}"),
        fact_key,
        fact_type,
        weight,
        confidence,
    )


def _scoring_evidence(
    *,
    chart: ChildChartVersion,
    fact: ScoringFact,
    fact_key: str,
    source_key: str,
    source_quality: float,
) -> ScoringEvidence:
    return ScoringEvidence(
        uuid.uuid5(_CHILD_EVIDENCE_NAMESPACE, f"{chart.id}:{source_key}:{fact_key}"),
        fact.id,
        chart.id,
        "child_chart_versions",
        chart.id,
        source_key,
        source_quality,
    )


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
