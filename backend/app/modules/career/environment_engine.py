"""Deterministic work-environment axes and conditional risk conditions."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.career.dimension_engine import CareerDimensionResult
from app.modules.career.models import CareerEnvironmentAxis
from app.modules.career.profile_resolver import CareerProfileResolution
from app.modules.career.schemas import CareerDimensionKey

ENVIRONMENT_SCORING_VERSION = "career-environment-1"


@dataclass(frozen=True)
class EnvironmentAxis:
    key: str
    score: float
    confidence: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class WorkEnvironmentResult:
    scoring_version: str
    axes: tuple[EnvironmentAxis, ...]
    preferred_conditions: tuple[str, ...]
    risk_conditions: tuple[str, ...]


_AXIS_WEIGHTS: dict[str, dict[CareerDimensionKey, float]] = {
    "structured_flexible": {CareerDimensionKey.STRUCTURE: -0.7, CareerDimensionKey.CREATIVITY: 0.3},
    "stable_dynamic": {CareerDimensionKey.RISK_TOLERANCE: 0.5, CareerDimensionKey.INNOVATION: 0.5},
    "individual_collaborative": {CareerDimensionKey.PEOPLE_ORIENTATION: 0.7, CareerDimensionKey.COMMUNICATION: 0.3},
    "expert_managerial": {CareerDimensionKey.LEADERSHIP: 0.5, CareerDimensionKey.PEOPLE_ORIENTATION: 0.5},
    "operational_strategic": {CareerDimensionKey.SYSTEMS_THINKING: 0.5, CareerDimensionKey.LONG_TERM_FOCUS: 0.5},
    "predictable_experimental": {CareerDimensionKey.INNOVATION: 0.6, CareerDimensionKey.RISK_TOLERANCE: 0.4},
    "supportive_competitive": {CareerDimensionKey.LEADERSHIP: 0.4, CareerDimensionKey.RISK_TOLERANCE: 0.6},
    "small_team_large_organization": {CareerDimensionKey.PEOPLE_ORIENTATION: 0.5, CareerDimensionKey.STRUCTURE: 0.5},
    "local_global": {CareerDimensionKey.COMMUNICATION: 0.4, CareerDimensionKey.LONG_TERM_FOCUS: 0.6},
    "execution_ownership": {CareerDimensionKey.AUTONOMY: 0.6, CareerDimensionKey.LEADERSHIP: 0.4},
}


def score_work_environment(
    *,
    dimensions: list[CareerDimensionResult],
    resolution: CareerProfileResolution,
) -> WorkEnvironmentResult:
    by_dimension = {item.dimension: item for item in dimensions}
    axes = tuple(_score_axis(key, weights, by_dimension) for key, weights in _AXIS_WEIGHTS.items())
    scores = {item.dimension: item.score for item in dimensions}
    preferences = set(resolution.preferences)

    preferred: set[str] = set()
    risks: set[str] = set()
    if scores.get(CareerDimensionKey.AUTONOMY, 50) >= 70:
        preferred.add("condition:clear_decision_authority")
        risks.add("condition:micromanagement_requires_explicit_decision_boundaries")
    if scores.get(CareerDimensionKey.STRUCTURE, 50) >= 70:
        preferred.add("condition:clear_process_and_responsibility")
        risks.add("condition:chaotic_priorities_require_stabilizing_process")
    if scores.get(CareerDimensionKey.RISK_TOLERANCE, 50) <= 40 or "risk:stable" in preferences:
        preferred.add("condition:bounded_change_and_visible_risk")
        risks.add("condition:high_uncertainty_requires_staged_experiments")
    if scores.get(CareerDimensionKey.PEOPLE_ORIENTATION, 50) <= 40 or "people_management:low" in preferences:
        preferred.add("condition:expert_contribution_without_constant_people_management")
        risks.add("condition:communication_heavy_role_requires_protected_focus_time")
    if "manager" in preferences:
        preferred.add("condition:team_direction_and_people_development")
    if "expert" in preferences:
        preferred.add("condition:deep_expertise_and_domain_ownership")

    return WorkEnvironmentResult(
        scoring_version=ENVIRONMENT_SCORING_VERSION,
        axes=axes,
        preferred_conditions=tuple(sorted(preferred)),
        risk_conditions=tuple(sorted(risks)),
    )


def _score_axis(
    key: str,
    weights: dict[CareerDimensionKey, float],
    dimensions: dict[CareerDimensionKey, CareerDimensionResult],
) -> EnvironmentAxis:
    weighted_delta = 0.0
    confidence_weight = 0.0
    evidence: list[str] = []
    total_weight = sum(abs(weight) for weight in weights.values())
    for dimension, weight in weights.items():
        result = dimensions.get(dimension)
        score = result.score if result is not None else 50.0
        weighted_delta += (score - 50.0) * weight
        if result is not None:
            confidence_weight += result.confidence * abs(weight)
            evidence.append(dimension.value)
    return EnvironmentAxis(
        key=key,
        score=round(max(0.0, min(100.0, 50.0 + weighted_delta)), 2),
        confidence=round(confidence_weight / total_weight, 4),
        evidence=tuple(sorted(evidence)),
    )


def build_environment_rows(
    *,
    career_profile_id: UUID,
    chart_id: UUID,
    result: WorkEnvironmentResult,
) -> list[CareerEnvironmentAxis]:
    return [
        CareerEnvironmentAxis(
            career_profile_id=career_profile_id,
            chart_id=chart_id,
            axis_key=axis.key,
            score=axis.score,
            confidence=axis.confidence,
            reference_version=result.scoring_version,
            anti_environment_conditions=list(result.risk_conditions),
        )
        for axis in result.axes
    ]
