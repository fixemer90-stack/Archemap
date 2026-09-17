from __future__ import annotations

from app.modules.career.dimension_engine import CareerDimensionResult
from app.modules.career.profile_resolver import CareerContradiction, CareerProfileResolution
from app.modules.career.schemas import CareerDimensionKey


def _dimension(key: CareerDimensionKey, score: float, confidence: float = 0.9) -> CareerDimensionResult:
    return CareerDimensionResult(
        dimension=key,
        score=score,
        confidence=confidence,
        scoring_version="career-mvp-1",
        evidence=(),
    )


def _resolution(
    *, preferences: tuple[str, ...], contradictions: tuple[CareerContradiction, ...] = ()
) -> CareerProfileResolution:
    return CareerProfileResolution(
        resolver_version="career-resolver-1",
        confirmed_traits=(),
        contradictions=contradictions,
        preferences=preferences,
        context_constraints=("experience:senior",),
        unresolved_ambiguities=(),
    )


def test_expert_leader_returns_top_three_and_avoids_people_manager_overclaim() -> None:
    from app.modules.career.archetype_engine import match_archetypes

    contradiction = CareerContradiction(
        code="leadership_without_people_management",
        dimension=CareerDimensionKey.LEADERSHIP,
        capability_score=88,
        preference_key="people_management_motivation",
        preference_value=1,
        scenario_keys=("expert_leadership",),
    )
    results = match_archetypes(
        dimensions=[
            _dimension(CareerDimensionKey.LEADERSHIP, 88),
            _dimension(CareerDimensionKey.SYSTEMS_THINKING, 92),
            _dimension(CareerDimensionKey.ANALYTICAL_THINKING, 86),
            _dimension(CareerDimensionKey.AUTONOMY, 84),
            _dimension(CareerDimensionKey.PEOPLE_ORIENTATION, 38),
        ],
        resolution=_resolution(preferences=("expert", "expert_leadership"), contradictions=(contradiction,)),
    )

    assert len(results) == 3
    assert [result.key for result in results] == ["architect", "strategist", "specialist"]
    assert all(result.evidence for result in results)
    assert all(0 <= result.confidence <= 1 for result in results)
    assert all(result.scoring_version == "career-archetypes-1" for result in results)
    assert "leader" not in {result.key for result in results}


def test_people_manager_and_autonomous_specialist_golden_cases_diverge() -> None:
    from app.modules.career.archetype_engine import match_archetypes

    dimensions = [
        _dimension(CareerDimensionKey.LEADERSHIP, 85),
        _dimension(CareerDimensionKey.PEOPLE_ORIENTATION, 88),
        _dimension(CareerDimensionKey.COMMUNICATION, 82),
        _dimension(CareerDimensionKey.AUTONOMY, 76),
        _dimension(CareerDimensionKey.ANALYTICAL_THINKING, 84),
        _dimension(CareerDimensionKey.EXECUTION, 80),
    ]
    manager = match_archetypes(dimensions=dimensions, resolution=_resolution(preferences=("manager",)))
    specialist = match_archetypes(dimensions=dimensions, resolution=_resolution(preferences=("expert",)))

    assert manager[0].key == "leader"
    assert specialist[0].key == "specialist"
    assert manager != specialist


def test_environment_axes_are_normalized_and_risk_conditions_are_conditional() -> None:
    from app.modules.career.environment_engine import score_work_environment

    environment = score_work_environment(
        dimensions=[
            _dimension(CareerDimensionKey.STRUCTURE, 78),
            _dimension(CareerDimensionKey.AUTONOMY, 90),
            _dimension(CareerDimensionKey.RISK_TOLERANCE, 35),
            _dimension(CareerDimensionKey.PEOPLE_ORIENTATION, 40),
            _dimension(CareerDimensionKey.INNOVATION, 72),
            _dimension(CareerDimensionKey.LONG_TERM_FOCUS, 82),
            _dimension(CareerDimensionKey.EXECUTION, 75),
            _dimension(CareerDimensionKey.LEADERSHIP, 80),
        ],
        resolution=_resolution(preferences=("expert", "people_management:low", "risk:stable")),
    )

    assert len(environment.axes) == 10
    assert all(0 <= axis.score <= 100 for axis in environment.axes)
    assert all(0 <= axis.confidence <= 1 for axis in environment.axes)
    assert environment.preferred_conditions
    assert environment.risk_conditions
    assert all(condition.startswith("condition:") for condition in environment.risk_conditions)
    assert not any(
        word in " ".join(environment.risk_conditions).lower() for word in ("нельзя", "forbidden", "must not")
    )


def test_archetype_and_environment_rows_are_persistable_and_versioned() -> None:
    import uuid

    from app.modules.career.archetype_engine import build_archetype_rows, match_archetypes
    from app.modules.career.environment_engine import build_environment_rows, score_work_environment

    dimensions = [
        _dimension(CareerDimensionKey.ANALYTICAL_THINKING, 85),
        _dimension(CareerDimensionKey.SYSTEMS_THINKING, 88),
        _dimension(CareerDimensionKey.AUTONOMY, 80),
        _dimension(CareerDimensionKey.STRUCTURE, 70),
    ]
    resolution = _resolution(preferences=("expert",))
    profile_id = uuid.uuid4()
    chart_id = uuid.uuid4()

    archetype_rows = build_archetype_rows(
        career_profile_id=profile_id,
        chart_id=chart_id,
        results=match_archetypes(dimensions=dimensions, resolution=resolution),
    )
    environment_rows = build_environment_rows(
        career_profile_id=profile_id,
        chart_id=chart_id,
        result=score_work_environment(dimensions=dimensions, resolution=resolution),
    )

    assert len(archetype_rows) == 3
    assert all(row.reference_version == "career-archetypes-1" for row in archetype_rows)
    assert len(environment_rows) == 10
    assert all(row.reference_version == "career-environment-1" for row in environment_rows)


def test_career_matching_source_has_no_planet_or_llm_dependency() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3] / "app" / "modules" / "career"
    source = (root / "archetype_engine.py").read_text() + (root / "environment_engine.py").read_text()
    assert "planet" not in source.lower()
    assert "modules.llm" not in source
