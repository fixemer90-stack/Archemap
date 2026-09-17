"""Deterministic resolver for Career capabilities and user preferences."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.modules.career.dimension_engine import CareerDimensionResult
from app.modules.career.models import CareerResolution
from app.modules.career.questionnaire import CareerQuestionnaireCompleted, PreferredTrack, RiskPreference
from app.modules.career.schemas import CareerDimensionKey

RESOLVER_VERSION = "career-resolver-1"


@dataclass(frozen=True)
class CareerContradiction:
    code: str
    dimension: CareerDimensionKey
    capability_score: float
    preference_key: str
    preference_value: Any
    scenario_keys: tuple[str, ...]


@dataclass(frozen=True)
class CareerProfileResolution:
    resolver_version: str
    confirmed_traits: tuple[str, ...]
    contradictions: tuple[CareerContradiction, ...]
    preferences: tuple[str, ...]
    context_constraints: tuple[str, ...]
    unresolved_ambiguities: tuple[str, ...]


def resolve_career_profile(
    *,
    dimensions: list[CareerDimensionResult],
    answers: CareerQuestionnaireCompleted,
) -> CareerProfileResolution:
    """Resolve application preferences without mutating deterministic capability scores."""
    by_dimension = {result.dimension: result for result in dimensions}
    confirmed: set[str] = set()
    contradictions: list[CareerContradiction] = []

    leadership = by_dimension.get(CareerDimensionKey.LEADERSHIP)
    if leadership is not None and leadership.score >= 70 and answers.leadership_responsibility >= 4:
        confirmed.add("leadership_capability")
    if leadership is not None and leadership.score >= 70 and answers.people_management_motivation <= 2:
        contradictions.append(
            CareerContradiction(
                code="leadership_without_people_management",
                dimension=CareerDimensionKey.LEADERSHIP,
                capability_score=leadership.score,
                preference_key="people_management_motivation",
                preference_value=answers.people_management_motivation,
                scenario_keys=("expert_leadership", "architect", "lead_specialist"),
            )
        )

    autonomy = by_dimension.get(CareerDimensionKey.AUTONOMY)
    if autonomy is not None and autonomy.score >= 70 and answers.autonomy_importance >= 4:
        confirmed.add("high_autonomy")
    elif autonomy is not None and autonomy.score >= 70 and answers.autonomy_importance <= 2:
        contradictions.append(
            CareerContradiction(
                code="autonomy_capability_with_structure_preference",
                dimension=CareerDimensionKey.AUTONOMY,
                capability_score=autonomy.score,
                preference_key="autonomy_importance",
                preference_value=answers.autonomy_importance,
                scenario_keys=("bounded_autonomy",),
            )
        )

    risk = by_dimension.get(CareerDimensionKey.RISK_TOLERANCE)
    if risk is not None and risk.score >= 70 and answers.risk_preference is RiskPreference.STABLE:
        contradictions.append(
            CareerContradiction(
                code="risk_capability_with_stability_preference",
                dimension=CareerDimensionKey.RISK_TOLERANCE,
                capability_score=risk.score,
                preference_key="risk_preference",
                preference_value=answers.risk_preference.value,
                scenario_keys=("controlled_experimentation",),
            )
        )

    preferences = {
        answers.preferred_track.value,
        f"risk:{answers.risk_preference.value}",
        f"people_management:{_level(answers.people_management_motivation)}",
        f"collaboration:{_level(answers.collaboration_preference)}",
    }
    if answers.preferred_track is PreferredTrack.EXPERT and leadership is not None and leadership.score >= 70:
        preferences.add("expert_leadership")

    ambiguities = {f"low_confidence:{result.dimension.value}" for result in dimensions if result.confidence < 0.5}
    if answers.preferred_track is PreferredTrack.UNKNOWN:
        ambiguities.add("preferred_track:unknown")

    return CareerProfileResolution(
        resolver_version=RESOLVER_VERSION,
        confirmed_traits=tuple(sorted(confirmed)),
        contradictions=tuple(sorted(contradictions, key=lambda item: item.code)),
        preferences=tuple(sorted(preferences)),
        context_constraints=(
            f"experience:{_experience_band(answers.experience_years)}",
            "current_activity:provided",
            "change_goal:provided",
            "constraints:provided",
        ),
        unresolved_ambiguities=tuple(sorted(ambiguities)),
    )


def build_resolution_row(
    *,
    career_profile_id: UUID,
    chart_id: UUID,
    resolution: CareerProfileResolution,
) -> CareerResolution:
    """Build a persisted resolver row without forwarding raw free text."""
    return CareerResolution(
        career_profile_id=career_profile_id,
        chart_id=chart_id,
        resolver_version=resolution.resolver_version,
        confirmed_traits=list(resolution.confirmed_traits),
        contradictions=[
            {
                "code": item.code,
                "dimension": item.dimension.value,
                "capability_score": item.capability_score,
                "preference_key": item.preference_key,
                "preference_value": item.preference_value,
                "scenario_keys": list(item.scenario_keys),
            }
            for item in resolution.contradictions
        ],
        preferences=list(resolution.preferences),
        context_constraints=list(resolution.context_constraints),
        unresolved_ambiguities=list(resolution.unresolved_ambiguities),
    )


def _level(value: int) -> str:
    if value <= 2:
        return "low"
    if value >= 4:
        return "high"
    return "medium"


def _experience_band(years: int) -> str:
    if years < 2:
        return "entry"
    if years < 5:
        return "mid"
    return "senior"
