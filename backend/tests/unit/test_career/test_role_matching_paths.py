from __future__ import annotations

import uuid

from app.modules.career.career_paths import (
    CAREER_PATH_GRAPH_VERSION,
    build_career_path_rows,
    build_career_paths,
)
from app.modules.career.dimension_engine import CareerDimensionResult
from app.modules.career.environment_engine import EnvironmentAxis, WorkEnvironmentResult
from app.modules.career.profile_resolver import CareerProfileResolution
from app.modules.career.role_matching import (
    POSSIBLE_MATCH_THRESHOLD,
    ROLE_CATALOG,
    ROLE_CATALOG_VERSION,
    STRONG_MATCH_THRESHOLD,
    build_role_match_rows,
    match_roles,
)
from app.modules.career.schemas import CareerDimensionKey, MatchCategory


def _dimension(key: CareerDimensionKey, score: float, confidence: float = 0.9) -> CareerDimensionResult:
    return CareerDimensionResult(
        dimension=key,
        score=score,
        confidence=confidence,
        scoring_version="career-mvp-1",
        evidence=(),
    )


def _environment() -> WorkEnvironmentResult:
    return WorkEnvironmentResult(
        scoring_version="career-environment-1",
        axes=(
            EnvironmentAxis("expert_managerial", 45, 0.9, ("leadership", "people_orientation")),
            EnvironmentAxis("operational_strategic", 88, 0.9, ("systems_thinking", "long_term_focus")),
            EnvironmentAxis("execution_ownership", 84, 0.9, ("autonomy", "leadership")),
        ),
        preferred_conditions=("condition:deep_expertise_and_domain_ownership",),
        risk_conditions=("condition:micromanagement_requires_explicit_decision_boundaries",),
    )


def _resolution(*preferences: str, context: tuple[str, ...] = ()) -> CareerProfileResolution:
    return CareerProfileResolution(
        resolver_version="career-resolver-1",
        confirmed_traits=(),
        contradictions=(),
        preferences=preferences,
        context_constraints=context,
        unresolved_ambiguities=(),
    )


def _dimensions() -> list[CareerDimensionResult]:
    return [
        _dimension(CareerDimensionKey.SYSTEMS_THINKING, 92),
        _dimension(CareerDimensionKey.ANALYTICAL_THINKING, 88),
        _dimension(CareerDimensionKey.AUTONOMY, 84),
        _dimension(CareerDimensionKey.LONG_TERM_FOCUS, 82),
        _dimension(CareerDimensionKey.COMMUNICATION, 74),
        _dimension(CareerDimensionKey.LEADERSHIP, 80),
        _dimension(CareerDimensionKey.PEOPLE_ORIENTATION, 42),
        _dimension(CareerDimensionKey.RISK_TOLERANCE, 38),
        _dimension(CareerDimensionKey.EXECUTION, 72),
        _dimension(CareerDimensionKey.INNOVATION, 76),
        _dimension(CareerDimensionKey.STRUCTURE, 78),
    ]


def test_role_catalog_and_categories_are_versioned_and_fixed() -> None:
    required = {
        "architecture",
        "product",
        "strategy",
        "analytics",
        "consulting",
        "operations",
        "research",
        "management",
        "entrepreneurship",
    }
    assert required <= set(ROLE_CATALOG)
    assert ROLE_CATALOG_VERSION == "career-role-catalog-1"
    assert STRONG_MATCH_THRESHOLD == 75
    assert POSSIBLE_MATCH_THRESHOLD == 60


def test_role_matching_is_explainable_and_uses_preferences_and_environment() -> None:
    expert = match_roles(
        dimensions=_dimensions(),
        environment=_environment(),
        resolution=_resolution("expert", "expert_leadership", context=("experience:senior",)),
    )
    manager = match_roles(
        dimensions=_dimensions(),
        environment=_environment(),
        resolution=_resolution("manager", context=("experience:senior",)),
    )

    assert expert[0].role_family_key == "architecture"
    assert manager[0].role_family_key == "management"
    assert expert[0].category is MatchCategory.STRONG_MATCH
    assert expert[0].reasons
    assert expert[0].tensions
    assert expert[0].requirements
    assert expert[0].confidence > 0
    assert expert[0].catalog_version == ROLE_CATALOG_VERSION
    assert expert[0].profession_examples
    assert all("guarantee" not in text.lower() for item in expert for text in item.requirements)


def test_low_evidence_and_unmet_constraints_make_match_context_dependent() -> None:
    matches = match_roles(
        dimensions=[_dimension(CareerDimensionKey.SYSTEMS_THINKING, 95, confidence=0.35)],
        environment=WorkEnvironmentResult("career-environment-1", (), (), ()),
        resolution=_resolution("manager"),
    )

    assert matches[0].category is MatchCategory.CONTEXT_DEPENDENT
    assert matches[0].confidence < 0.5
    assert "context:current_experience_missing" in matches[0].requirements
    assert any(item.startswith("evidence:") for item in matches[0].requirements)


def test_same_scores_with_different_preferences_produce_different_graph_paths() -> None:
    expert_matches = match_roles(
        dimensions=_dimensions(),
        environment=_environment(),
        resolution=_resolution("expert", context=("experience:senior", "goal:independent_practice")),
    )
    manager_matches = match_roles(
        dimensions=_dimensions(),
        environment=_environment(),
        resolution=_resolution("manager", context=("experience:senior", "goal:team_leadership")),
    )

    expert_paths = build_career_paths(
        matches=expert_matches,
        resolution=_resolution("expert", context=("experience:senior", "goal:independent_practice")),
    )
    manager_paths = build_career_paths(
        matches=manager_matches,
        resolution=_resolution("manager", context=("experience:senior", "goal:team_leadership")),
    )

    assert 2 <= len(expert_paths) <= 3
    assert 2 <= len(manager_paths) <= 3
    assert expert_paths[0].steps != manager_paths[0].steps
    assert all(path.graph_version == CAREER_PATH_GRAPH_VERSION for path in (*expert_paths, *manager_paths))
    assert all(step.transition_key for path in expert_paths for step in path.steps[1:])
    assert not any(path.role_family_key == "entrepreneurship" for path in expert_paths)


def test_manager_expert_leader_and_entrepreneur_preferences_diverge_on_same_scores() -> None:
    expert = match_roles(
        dimensions=_dimensions(),
        environment=_environment(),
        resolution=_resolution("expert", "expert_leadership", context=("experience:senior",)),
    )
    manager = match_roles(
        dimensions=_dimensions(),
        environment=_environment(),
        resolution=_resolution("manager", context=("experience:senior",)),
    )
    entrepreneur = match_roles(
        dimensions=_dimensions(),
        environment=_environment(),
        resolution=_resolution("entrepreneur", context=("experience:senior",)),
    )

    assert expert[0].role_family_key == "architecture"
    assert manager[0].role_family_key == "management"
    assert entrepreneur[0].role_family_key == "entrepreneurship"


def test_missing_context_produces_archetypal_paths_with_explicit_limitations() -> None:
    matches = match_roles(
        dimensions=_dimensions(),
        environment=_environment(),
        resolution=_resolution("expert"),
    )
    paths = build_career_paths(matches=matches, resolution=_resolution("expert"))

    assert paths
    assert all(path.archetypal for path in paths)
    assert all("context:current_experience_missing" in path.limitations for path in paths)
    assert all("context:goal_missing" in path.limitations for path in paths)


def test_role_and_path_results_build_persistable_rows() -> None:
    profile_id = uuid.uuid4()
    chart_id = uuid.uuid4()
    matches = match_roles(
        dimensions=_dimensions(),
        environment=_environment(),
        resolution=_resolution("expert", context=("experience:senior", "goal:independent_practice")),
    )[:2]
    role_rows = build_role_match_rows(career_profile_id=profile_id, chart_id=chart_id, matches=matches)
    paths = build_career_paths(
        matches=matches,
        resolution=_resolution("expert", context=("experience:senior", "goal:independent_practice")),
    )
    path_rows = build_career_path_rows(
        career_profile_id=profile_id,
        chart_id=chart_id,
        role_rows=role_rows,
        paths=paths,
    )

    assert all(row.id is not None for row in role_rows)
    assert all(row.reference_version == ROLE_CATALOG_VERSION for row in role_rows)
    assert path_rows
    assert all(row.role_match_id in {role.id for role in role_rows} for row in path_rows)
    assert all(row.reference_version == CAREER_PATH_GRAPH_VERSION for row in path_rows)
