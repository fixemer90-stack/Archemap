"""Side-effect-free adapters from scored dimensions to Career ORM rows."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.modules.career.dimension_engine import CareerDimensionResult
from app.modules.career.models import CareerDimensionEvidence, CareerDimensionScore


def build_dimension_rows(
    *,
    career_profile_id: uuid.UUID,
    chart_id: uuid.UUID,
    results: Sequence[CareerDimensionResult],
) -> tuple[list[CareerDimensionScore], list[CareerDimensionEvidence]]:
    """Build independently queryable score/evidence rows with preassigned IDs."""
    scores: list[CareerDimensionScore] = []
    evidence_rows: list[CareerDimensionEvidence] = []

    for result in results:
        score_id = uuid.uuid4()
        scores.append(
            CareerDimensionScore(
                id=score_id,
                career_profile_id=career_profile_id,
                chart_id=chart_id,
                dimension=result.dimension.value,
                score=result.score,
                confidence=result.confidence,
                scoring_version=result.scoring_version,
                breakdown={
                    "evidence_count": len(result.evidence),
                    "correlation_families": sorted({item.correlation_family for item in result.evidence}),
                },
            )
        )
        evidence_rows.extend(
            CareerDimensionEvidence(
                dimension_score_id=score_id,
                chart_id=chart_id,
                source_type=item.source_type,
                source_id=item.source_id,
                contribution=item.contribution,
                direction=item.direction.value,
                payload={
                    "factor_key": item.factor_key,
                    "correlation_family": item.correlation_family,
                    "factor_value": item.factor_value,
                    "source_quality": item.source_quality,
                    "weight": item.weight,
                },
            )
            for item in result.evidence
        )

    return scores, evidence_rows
