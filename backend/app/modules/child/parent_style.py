"""Deterministic Parent Style scoring facade."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from uuid import UUID

from app.modules.astrotype_v2.models import NatalChart, NatalFact, NatalFactEvidence
from app.modules.child.models import ChildParentStyleScore
from app.modules.child.scoring.engine import score_dimensions
from app.modules.child.scoring.types import DimensionResult, ParentStyleDimension
from app.reference_data.child.parent_style_v1 import (
    PARENT_STYLE_POLICY,
    PARENT_STYLE_REFERENCE_VERSION,
    PARENT_STYLE_RULES,
    PARENT_STYLE_SCALES,
    PARENT_STYLE_SCORING_VERSION,
)

ParentStyleResult = DimensionResult[ParentStyleDimension]
_PARENT_STYLE_ROW_NAMESPACE = uuid.UUID("23d0a5f6-d950-5f54-86a7-b40743f92032")


def score_parent_style(
    *,
    chart: NatalChart,
    facts: Sequence[NatalFact],
    evidence: Sequence[NatalFactEvidence],
) -> tuple[ParentStyleResult, ...]:
    """Return all canonical Parent Style dimensions from persisted v2 evidence."""

    if any(fact.chart_id != chart.id for fact in facts):
        raise ValueError("Parent natal facts must belong to the supplied parent chart")
    if any(row.chart_id != chart.id for row in evidence):
        raise ValueError("Parent natal fact evidence must belong to the supplied parent chart")
    return score_dimensions(
        dimensions=tuple(ParentStyleDimension),
        facts=facts,
        evidence=evidence,
        rules=PARENT_STYLE_RULES,
        scale_semantics=PARENT_STYLE_SCALES,
        scoring_version=PARENT_STYLE_SCORING_VERSION,
        policy=PARENT_STYLE_POLICY,
        allow_time_sensitive=_has_exact_timing_proof(chart),
    )


def build_parent_style_rows(
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    parent_chart_id: UUID,
    results: Sequence[ParentStyleResult],
) -> tuple[ChildParentStyleScore, ...]:
    """Build immutable ORM score rows without database side effects."""

    expected_dimensions = tuple(ParentStyleDimension)
    actual_dimensions = tuple(result.dimension for result in results)
    if actual_dimensions != expected_dimensions:
        raise ValueError("Parent Style results must contain all canonical dimensions in order")
    if any(result.scoring_version != PARENT_STYLE_SCORING_VERSION for result in results):
        raise ValueError("Parent Style results use an unsupported scoring version")

    rows: list[ChildParentStyleScore] = []
    for result in results:
        rows.append(
            ChildParentStyleScore(
                id=uuid.uuid5(
                    _PARENT_STYLE_ROW_NAMESPACE,
                    f"{child_profile_id}:{generation_id}:{parent_chart_id}:{result.scoring_version}:{result.dimension.value}",
                ),
                child_profile_id=child_profile_id,
                generation_id=generation_id,
                parent_chart_id=parent_chart_id,
                dimension=result.dimension.value,
                score=result.score,
                confidence=result.confidence,
                scoring_version=result.scoring_version,
                evidence_refs=list(result.evidence_refs),
                breakdown={
                    "reference_version": PARENT_STYLE_REFERENCE_VERSION,
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
        )
    return tuple(rows)


def _evidence_payload(item: object) -> dict[str, object]:
    from app.modules.child.scoring.types import DimensionEvidence

    if not isinstance(item, DimensionEvidence):
        raise TypeError("Expected deterministic dimension evidence")
    return {
        "factor_key": item.factor_key,
        "fact_id": str(item.fact_id),
        "evidence_refs": list(item.evidence_refs),
        "lineage_refs": list(item.lineage_refs),
        "correlation_family": item.correlation_family,
        "factor_value": item.factor_value,
        "source_quality": item.source_quality,
        "weight": item.weight,
        "contribution": round(item.contribution, 6),
        "direction": item.direction.value,
    }


def _has_exact_timing_proof(chart: NatalChart) -> bool:
    payload = chart.calculation_payload if isinstance(chart.calculation_payload, dict) else {}
    recognized_keys = ("birth_time_proof", "technical_reference")
    present_blocks = [payload[key] for key in recognized_keys if key in payload]
    if any(not isinstance(block, dict) for block in present_blocks):
        return False
    proofs = [block for block in present_blocks if isinstance(block, dict)]
    if not proofs:
        return False
    return all(
        proof.get("user_supplied_time") is True
        and proof.get("synthetic_noon") is False
        and (proof.get("birth_time_confidence") or proof.get("confidence")) == "exact"
        for proof in proofs
    )
