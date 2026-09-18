"""Deterministic role-family matching for Career reports."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from app.modules.career.dimension_engine import CareerDimensionResult
from app.modules.career.environment_engine import EnvironmentAxis, WorkEnvironmentResult
from app.modules.career.models import CareerRoleMatch
from app.modules.career.profile_resolver import CareerProfileResolution
from app.modules.career.schemas import CareerDimensionKey, MatchCategory

ROLE_CATALOG_VERSION = "career-role-catalog-1"
STRONG_MATCH_THRESHOLD = 75
POSSIBLE_MATCH_THRESHOLD = 60


@dataclass(frozen=True)
class RoleFamilyDefinition:
    key: str
    weights: dict[CareerDimensionKey, float]
    environment_axes: dict[str, float]
    profession_examples: tuple[str, ...]
    preference_boosts: dict[str, float]


@dataclass(frozen=True)
class RoleMatchResult:
    role_family_key: str
    score: float
    confidence: float
    category: MatchCategory
    reasons: tuple[str, ...]
    tensions: tuple[str, ...]
    requirements: tuple[str, ...]
    profession_examples: tuple[str, ...]
    catalog_version: str = ROLE_CATALOG_VERSION


ROLE_CATALOG: dict[str, RoleFamilyDefinition] = {
    "architecture": RoleFamilyDefinition(
        "architecture",
        {CareerDimensionKey.SYSTEMS_THINKING: 0.35, CareerDimensionKey.ANALYTICAL_THINKING: 0.25,
         CareerDimensionKey.AUTONOMY: 0.20, CareerDimensionKey.LONG_TERM_FOCUS: 0.20},
        {"operational_strategic": 0.6, "execution_ownership": 0.4},
        ("Solution Architect", "Systems Architect", "Lead Engineer"),
        {"expert": 12, "expert_leadership": 8},
    ),
    "product": RoleFamilyDefinition(
        "product",
        {CareerDimensionKey.SYSTEMS_THINKING: 0.25, CareerDimensionKey.COMMUNICATION: 0.25,
         CareerDimensionKey.EXECUTION: 0.25, CareerDimensionKey.INNOVATION: 0.25},
        {"operational_strategic": 0.5, "execution_ownership": 0.5},
        ("Product Manager", "Product Operations Lead"),
        {"manager": 8, "entrepreneur": 6},
    ),
    "strategy": RoleFamilyDefinition(
        "strategy",
        {CareerDimensionKey.SYSTEMS_THINKING: 0.35, CareerDimensionKey.LONG_TERM_FOCUS: 0.30,
         CareerDimensionKey.ANALYTICAL_THINKING: 0.20, CareerDimensionKey.LEADERSHIP: 0.15},
        {"operational_strategic": 1.0},
        ("Strategy Lead", "Corporate Strategist"),
        {"expert_leadership": 8, "manager": 5},
    ),
    "analytics": RoleFamilyDefinition(
        "analytics",
        {CareerDimensionKey.ANALYTICAL_THINKING: 0.45, CareerDimensionKey.SYSTEMS_THINKING: 0.25,
         CareerDimensionKey.STRUCTURE: 0.20, CareerDimensionKey.EXECUTION: 0.10},
        {"operational_strategic": 1.0},
        ("Data Analyst", "Business Intelligence Analyst"),
        {"expert": 9},
    ),
    "consulting": RoleFamilyDefinition(
        "consulting",
        {CareerDimensionKey.ANALYTICAL_THINKING: 0.25, CareerDimensionKey.COMMUNICATION: 0.30,
         CareerDimensionKey.SYSTEMS_THINKING: 0.25, CareerDimensionKey.AUTONOMY: 0.20},
        {"execution_ownership": 1.0},
        ("Management Consultant", "Independent Advisor"),
        {"expert": 7, "expert_leadership": 5},
    ),
    "operations": RoleFamilyDefinition(
        "operations",
        {CareerDimensionKey.EXECUTION: 0.35, CareerDimensionKey.STRUCTURE: 0.30,
         CareerDimensionKey.LEADERSHIP: 0.20, CareerDimensionKey.SYSTEMS_THINKING: 0.15},
        {"execution_ownership": 1.0},
        ("Operations Lead", "Program Manager"),
        {"manager": 8},
    ),
    "research": RoleFamilyDefinition(
        "research",
        {CareerDimensionKey.ANALYTICAL_THINKING: 0.35, CareerDimensionKey.SYSTEMS_THINKING: 0.25,
         CareerDimensionKey.LONG_TERM_FOCUS: 0.25, CareerDimensionKey.INNOVATION: 0.15},
        {"operational_strategic": 1.0},
        ("Research Scientist", "UX Researcher"),
        {"expert": 10},
    ),
    "management": RoleFamilyDefinition(
        "management",
        {CareerDimensionKey.LEADERSHIP: 0.35, CareerDimensionKey.PEOPLE_ORIENTATION: 0.30,
         CareerDimensionKey.COMMUNICATION: 0.20, CareerDimensionKey.EXECUTION: 0.15},
        {"expert_managerial": 0.7, "execution_ownership": 0.3},
        ("Engineering Manager", "Department Head"),
        {"manager": 32},
    ),
    "entrepreneurship": RoleFamilyDefinition(
        "entrepreneurship",
        {CareerDimensionKey.AUTONOMY: 0.25, CareerDimensionKey.RISK_TOLERANCE: 0.25,
         CareerDimensionKey.INNOVATION: 0.25, CareerDimensionKey.EXECUTION: 0.25},
        {"predictable_experimental": 0.5, "execution_ownership": 0.5},
        ("Founder", "Independent Venture Builder"),
        {"entrepreneur": 20},
    ),
}


def match_roles(
    *, dimensions: list[CareerDimensionResult], environment: WorkEnvironmentResult,
    resolution: CareerProfileResolution,
) -> tuple[RoleMatchResult, ...]:
    """Rank role families from dimensions, environment, and explicit preferences."""
    by_dimension = {item.dimension: item for item in dimensions}
    axes = {item.key: item for item in environment.axes}
    preferences = set(resolution.preferences)
    results = [_match_one(item, by_dimension, axes, preferences, resolution) for item in ROLE_CATALOG.values()]
    return tuple(sorted(results, key=lambda item: (-item.score, item.role_family_key)))


def _match_one(
    definition: RoleFamilyDefinition,
    dimensions: dict[CareerDimensionKey, CareerDimensionResult],
    axes: dict[str, EnvironmentAxis],
    preferences: set[str],
    resolution: CareerProfileResolution,
) -> RoleMatchResult:
    score = 0.0
    confidence_weighted = 0.0
    reasons: list[str] = []
    tensions: list[str] = []
    requirements: list[str] = []
    present_weight = 0.0
    for key, weight in definition.weights.items():
        result = dimensions.get(key)
        if result is None:
            score += 50 * weight
            requirements.append(f"evidence:missing_{key.value}")
            continue
        present_weight += weight
        score += result.score * weight
        confidence_weighted += result.confidence * weight
        if result.score >= 65:
            reasons.append(f"dimension:{key.value}")
        elif result.score <= 45:
            tensions.append(f"dimension:{key.value}")

    environment_score = 0.0
    environment_confidence = 0.0
    environment_weight = 0.0
    for axis_key, weight in definition.environment_axes.items():
        axis = axes.get(axis_key)
        if axis is None:
            requirements.append(f"evidence:missing_environment_{axis_key}")
            continue
        environment_weight += weight
        environment_score += axis.score * weight
        environment_confidence += axis.confidence * weight
        reasons.append(f"environment:{axis_key}")
    if environment_weight:
        score = score * 0.85 + (environment_score / environment_weight) * 0.15

    for preference, boost in definition.preference_boosts.items():
        if preference in preferences:
            score += boost
            reasons.append(f"preference:{preference}")

    if "people_management:low" in preferences and definition.key == "management":
        score -= 25
        tensions.append("preference:low_people_management")
    if "risk:stable" in preferences and definition.key == "entrepreneurship":
        score -= 15
        tensions.append("preference:stable_risk")

    context = set(resolution.context_constraints)
    if not any(item.startswith("experience:") for item in context):
        requirements.append("context:current_experience_missing")
    if not any(item.startswith("goal:") or item == "change_goal:provided" for item in context):
        requirements.append("context:goal_missing")

    confidence_denominator = present_weight + environment_weight * 0.15
    confidence = (
        (confidence_weighted + environment_confidence * 0.15) / confidence_denominator
        if confidence_denominator
        else 0
    )
    confidence = max(0.0, min(1.0, confidence))
    score = max(0.0, min(100.0, score))
    if confidence < 0.5 or any(item.startswith("evidence:") for item in requirements):
        category = MatchCategory.CONTEXT_DEPENDENT
    elif score >= STRONG_MATCH_THRESHOLD:
        category = MatchCategory.STRONG_MATCH
    elif score >= POSSIBLE_MATCH_THRESHOLD:
        category = MatchCategory.POSSIBLE_MATCH
    else:
        category = MatchCategory.CONTEXT_DEPENDENT
    if not tensions:
        tensions.append("tension:context_fit_requires_validation")
    if not requirements:
        requirements.append("context:validate_against_real_role_scope")
    return RoleMatchResult(
        role_family_key=definition.key, score=round(score, 2), confidence=round(confidence, 4),
        category=category, reasons=tuple(sorted(set(reasons))), tensions=tuple(sorted(set(tensions))),
        requirements=tuple(sorted(set(requirements))), profession_examples=definition.profession_examples,
    )


def build_role_match_rows(*, career_profile_id: UUID, chart_id: UUID,
                          matches: tuple[RoleMatchResult, ...] | list[RoleMatchResult]) -> list[CareerRoleMatch]:
    return [CareerRoleMatch(
        id=uuid.uuid4(), career_profile_id=career_profile_id, chart_id=chart_id,
        role_family_key=item.role_family_key, match_category=item.category.value,
        score=item.score, confidence=item.confidence, reference_version=item.catalog_version,
        reasons=list(item.reasons), tensions=list(item.tensions), requirements=list(item.requirements),
    ) for item in matches]
