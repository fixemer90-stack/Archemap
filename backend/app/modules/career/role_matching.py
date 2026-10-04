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

ROLE_CATALOG_VERSION = "career-role-catalog-2"
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
        {
            CareerDimensionKey.SYSTEMS_THINKING: 0.35,
            CareerDimensionKey.ANALYTICAL_THINKING: 0.25,
            CareerDimensionKey.AUTONOMY: 0.20,
            CareerDimensionKey.LONG_TERM_FOCUS: 0.20,
        },
        {"operational_strategic": 0.6, "execution_ownership": 0.4},
        ("Архитектор решений", "Системный архитектор", "Ведущий инженер"),
        {"expert": 12, "expert_leadership": 8},
    ),
    "product": RoleFamilyDefinition(
        "product",
        {
            CareerDimensionKey.SYSTEMS_THINKING: 0.25,
            CareerDimensionKey.COMMUNICATION: 0.25,
            CareerDimensionKey.EXECUTION: 0.25,
            CareerDimensionKey.INNOVATION: 0.25,
        },
        {"operational_strategic": 0.5, "execution_ownership": 0.5},
        ("Менеджер продукта", "Руководитель продуктовых операций"),
        {"manager": 8, "entrepreneur": 6},
    ),
    "strategy": RoleFamilyDefinition(
        "strategy",
        {
            CareerDimensionKey.SYSTEMS_THINKING: 0.35,
            CareerDimensionKey.LONG_TERM_FOCUS: 0.30,
            CareerDimensionKey.ANALYTICAL_THINKING: 0.20,
            CareerDimensionKey.LEADERSHIP: 0.15,
        },
        {"operational_strategic": 1.0},
        ("Руководитель стратегии", "Корпоративный стратег"),
        {"expert_leadership": 8, "manager": 5},
    ),
    "analytics": RoleFamilyDefinition(
        "analytics",
        {
            CareerDimensionKey.ANALYTICAL_THINKING: 0.45,
            CareerDimensionKey.SYSTEMS_THINKING: 0.25,
            CareerDimensionKey.STRUCTURE: 0.20,
            CareerDimensionKey.EXECUTION: 0.10,
        },
        {"operational_strategic": 1.0},
        ("Аналитик данных", "Аналитик бизнес-показателей"),
        {"expert": 9},
    ),
    "consulting": RoleFamilyDefinition(
        "consulting",
        {
            CareerDimensionKey.ANALYTICAL_THINKING: 0.25,
            CareerDimensionKey.COMMUNICATION: 0.30,
            CareerDimensionKey.SYSTEMS_THINKING: 0.25,
            CareerDimensionKey.AUTONOMY: 0.20,
        },
        {"execution_ownership": 1.0},
        ("Консультант по управлению", "Независимый советник"),
        {"expert": 7, "expert_leadership": 5},
    ),
    "operations": RoleFamilyDefinition(
        "operations",
        {
            CareerDimensionKey.EXECUTION: 0.35,
            CareerDimensionKey.STRUCTURE: 0.30,
            CareerDimensionKey.LEADERSHIP: 0.20,
            CareerDimensionKey.SYSTEMS_THINKING: 0.15,
        },
        {"execution_ownership": 1.0},
        ("Руководитель операций", "Менеджер программ"),
        {"manager": 8},
    ),
    "research": RoleFamilyDefinition(
        "research",
        {
            CareerDimensionKey.ANALYTICAL_THINKING: 0.35,
            CareerDimensionKey.SYSTEMS_THINKING: 0.25,
            CareerDimensionKey.LONG_TERM_FOCUS: 0.25,
            CareerDimensionKey.INNOVATION: 0.15,
        },
        {"operational_strategic": 1.0},
        ("Научный сотрудник", "Исследователь пользовательского опыта"),
        {"expert": 10},
    ),
    "management": RoleFamilyDefinition(
        "management",
        {
            CareerDimensionKey.LEADERSHIP: 0.35,
            CareerDimensionKey.PEOPLE_ORIENTATION: 0.30,
            CareerDimensionKey.COMMUNICATION: 0.20,
            CareerDimensionKey.EXECUTION: 0.15,
        },
        {"expert_managerial": 0.7, "execution_ownership": 0.3},
        ("Руководитель инженерной команды", "Руководитель отдела"),
        {"manager": 32},
    ),
    "entrepreneurship": RoleFamilyDefinition(
        "entrepreneurship",
        {
            CareerDimensionKey.AUTONOMY: 0.25,
            CareerDimensionKey.RISK_TOLERANCE: 0.25,
            CareerDimensionKey.INNOVATION: 0.25,
            CareerDimensionKey.EXECUTION: 0.25,
        },
        {"predictable_experimental": 0.5, "execution_ownership": 0.5},
        ("Основатель проекта", "Создатель независимого бизнеса"),
        {"entrepreneur": 20},
    ),
    "visual_arts": RoleFamilyDefinition(
        "visual_arts",
        {
            CareerDimensionKey.CREATIVITY: 0.4,
            CareerDimensionKey.INNOVATION: 0.2,
            CareerDimensionKey.AUTONOMY: 0.2,
            CareerDimensionKey.EXECUTION: 0.2,
        },
        {"practical_abstract": -0.35, "one_off_flow": -0.65},
        ("Художник", "Иллюстратор", "Фотограф"),
        {"work_mode:practical": 5, "production_mode:one_off": 10, "audience:audience": 4},
    ),
    "word_and_media": RoleFamilyDefinition(
        "word_and_media",
        {
            CareerDimensionKey.COMMUNICATION: 0.35,
            CareerDimensionKey.CREATIVITY: 0.3,
            CareerDimensionKey.ANALYTICAL_THINKING: 0.2,
            CareerDimensionKey.AUTONOMY: 0.15,
        },
        {"behind_scenes_audience_stage": 0.35, "one_off_flow": -0.65},
        ("Редактор", "Журналист", "Сценарист"),
        {"audience:audience": 8, "production_mode:one_off": 5},
    ),
    "performing_arts": RoleFamilyDefinition(
        "performing_arts",
        {
            CareerDimensionKey.CREATIVITY: 0.35,
            CareerDimensionKey.COMMUNICATION: 0.3,
            CareerDimensionKey.PEOPLE_ORIENTATION: 0.2,
            CareerDimensionKey.EXECUTION: 0.15,
        },
        {"behind_scenes_audience_stage": 0.75, "one_off_flow": -0.25},
        ("Актёр", "Музыкант-исполнитель", "Танцовщик"),
        {"audience:stage": 14, "audience:audience": 7},
    ),
    "craft_and_manual_work": RoleFamilyDefinition(
        "craft_and_manual_work",
        {
            CareerDimensionKey.EXECUTION: 0.35,
            CareerDimensionKey.CREATIVITY: 0.25,
            CareerDimensionKey.STRUCTURE: 0.25,
            CareerDimensionKey.AUTONOMY: 0.15,
        },
        {"conceptual_hands_on": 0.7, "practical_abstract": -0.3},
        ("Столяр", "Керамист", "Портной"),
        {"work_mode:practical": 12, "hands_on:hands_on": 10, "production_mode:one_off": 5},
    ),
    "practical_technology": RoleFamilyDefinition(
        "practical_technology",
        {
            CareerDimensionKey.EXECUTION: 0.35,
            CareerDimensionKey.ANALYTICAL_THINKING: 0.25,
            CareerDimensionKey.STRUCTURE: 0.2,
            CareerDimensionKey.SYSTEMS_THINKING: 0.2,
        },
        {"conceptual_hands_on": 0.65, "client_system": 0.35},
        ("Электромеханик", "Техник по оборудованию", "Автомеханик"),
        {"work_mode:practical": 10, "hands_on:hands_on": 12, "service_focus:system": 5},
    ),
    "care_and_service": RoleFamilyDefinition(
        "care_and_service",
        {
            CareerDimensionKey.PEOPLE_ORIENTATION: 0.4,
            CareerDimensionKey.COMMUNICATION: 0.25,
            CareerDimensionKey.EXECUTION: 0.2,
            CareerDimensionKey.STRUCTURE: 0.15,
        },
        {"client_system": -0.7, "conceptual_hands_on": 0.3},
        ("Медицинская сестра", "Социальный работник", "Мастер бытового сервиса"),
        {"service_focus:client": 14, "work_mode:practical": 5},
    ),
    "land_and_nature": RoleFamilyDefinition(
        "land_and_nature",
        {
            CareerDimensionKey.EXECUTION: 0.35,
            CareerDimensionKey.LONG_TERM_FOCUS: 0.25,
            CareerDimensionKey.AUTONOMY: 0.2,
            CareerDimensionKey.SYSTEMS_THINKING: 0.2,
        },
        {"conceptual_hands_on": 0.55, "practical_abstract": -0.45},
        ("Агроном", "Садовник", "Специалист по лесному хозяйству"),
        {"work_mode:practical": 10, "hands_on:hands_on": 8, "service_focus:system": 4},
    ),
    "sales_and_field_work": RoleFamilyDefinition(
        "sales_and_field_work",
        {
            CareerDimensionKey.COMMUNICATION: 0.35,
            CareerDimensionKey.EXECUTION: 0.25,
            CareerDimensionKey.AUTONOMY: 0.2,
            CareerDimensionKey.RISK_TOLERANCE: 0.2,
        },
        {"client_system": -0.6, "behind_scenes_audience_stage": 0.4},
        ("Торговый представитель", "Агент по недвижимости", "Полевой консультант"),
        {"service_focus:client": 10, "audience:audience": 6, "production_mode:flow": 5},
    ),
}


def match_roles(
    *,
    dimensions: list[CareerDimensionResult],
    environment: WorkEnvironmentResult,
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
        absolute_weight = abs(weight)
        environment_weight += absolute_weight
        environment_score += (axis.score if weight >= 0 else 100 - axis.score) * absolute_weight
        environment_confidence += axis.confidence * absolute_weight
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
        (confidence_weighted + environment_confidence * 0.15) / confidence_denominator if confidence_denominator else 0
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
        role_family_key=definition.key,
        score=round(score, 2),
        confidence=round(confidence, 4),
        category=category,
        reasons=tuple(sorted(set(reasons))),
        tensions=tuple(sorted(set(tensions))),
        requirements=tuple(sorted(set(requirements))),
        profession_examples=definition.profession_examples,
    )


def build_role_match_rows(
    *,
    career_profile_id: UUID,
    chart_id: UUID,
    generation_id: UUID,
    matches: tuple[RoleMatchResult, ...] | list[RoleMatchResult],
) -> list[CareerRoleMatch]:
    return [
        CareerRoleMatch(
            id=uuid.uuid4(),
            career_profile_id=career_profile_id,
            chart_id=chart_id,
            generation_id=generation_id,
            role_family_key=item.role_family_key,
            match_category=item.category.value,
            score=item.score,
            confidence=item.confidence,
            reference_version=item.catalog_version,
            reasons=list(item.reasons),
            tensions=list(item.tensions),
            requirements=list(item.requirements),
        )
        for item in matches
    ]
