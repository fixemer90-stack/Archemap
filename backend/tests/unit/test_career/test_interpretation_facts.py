from __future__ import annotations

import uuid

import pytest

from app.modules.career.archetype_engine import ArchetypeMatch
from app.modules.career.career_paths import CareerPathNode, CareerPathResult
from app.modules.career.dimension_engine import CareerDimensionResult, DimensionEvidence
from app.modules.career.environment_engine import EnvironmentAxis, WorkEnvironmentResult
from app.modules.career.interpretation_facts import (
    CAREER_FACTS_CONTRACT_VERSION,
    CareerFactsValidationError,
    build_interpretation_fact_rows,
    build_interpretation_facts,
    call_provider_with_validated_facts,
    validate_interpretation_facts,
)
from app.modules.career.profile_resolver import CareerContradiction, CareerProfileResolution
from app.modules.career.role_matching import ROLE_CATALOG_VERSION, RoleMatchResult
from app.modules.career.schemas import CareerDimensionKey, EvidenceDirection, MatchCategory


def _dimension(key: CareerDimensionKey, score: float, confidence: float) -> CareerDimensionResult:
    source_id = uuid.uuid4()
    return CareerDimensionResult(
        dimension=key,
        score=score,
        confidence=confidence,
        scoring_version="career-mvp-1",
        evidence=(
            DimensionEvidence(
                factor_key=f"factor:{key.value}",
                source_type="natal_fact",
                source_id=source_id,
                correlation_family=f"family:{key.value}",
                factor_value=0.8,
                source_quality=confidence,
                weight=0.5,
                contribution=0.4,
                direction=EvidenceDirection.SUPPORTS,
            ),
        ),
    )


def _payload():
    dimensions = [
        _dimension(CareerDimensionKey.SYSTEMS_THINKING, 90, 0.92),
        _dimension(CareerDimensionKey.ANALYTICAL_THINKING, 84, 0.86),
        _dimension(CareerDimensionKey.PEOPLE_ORIENTATION, 35, 0.42),
    ]
    contradiction = CareerContradiction(
        code="leadership_without_people_management",
        dimension=CareerDimensionKey.LEADERSHIP,
        capability_score=82,
        preference_key="people_management_motivation",
        preference_value=1,
        scenario_keys=("expert_leadership",),
    )
    resolution = CareerProfileResolution(
        resolver_version="career-resolver-1",
        confirmed_traits=("high_autonomy",),
        contradictions=(contradiction,),
        preferences=("expert", "people_management:low"),
        context_constraints=("experience:senior", "goal:independent_practice"),
        unresolved_ambiguities=(),
    )
    environment = WorkEnvironmentResult(
        scoring_version="career-environment-1",
        axes=(EnvironmentAxis("operational_strategic", 88, 0.9, ("systems_thinking",)),),
        preferred_conditions=("condition:deep_expertise",),
        risk_conditions=("condition:micromanagement_requires_boundaries",),
    )
    archetypes = (
        ArchetypeMatch("architect", 88, 0.9, "career-archetypes-1", ("systems_thinking",), ()),
    )
    matches = (
        RoleMatchResult(
            role_family_key="architecture",
            score=86,
            confidence=0.88,
            category=MatchCategory.STRONG_MATCH,
            reasons=("dimension:systems_thinking",),
            tensions=("preference:low_people_management",),
            requirements=("context:validate_against_real_role_scope",),
            profession_examples=("Solution Architect",),
        ),
    )
    paths = (
        CareerPathResult(
            role_family_key="architecture",
            steps=(
                CareerPathNode("domain_specialist", None),
                CareerPathNode("solution_architect", "domain_specialist_to_solution_architect"),
            ),
            limitations=(),
            archetypal=False,
        ),
    )
    return dimensions, archetypes, environment, resolution, matches, paths


def test_facts_are_typed_curated_and_section_owned() -> None:
    profile_id = uuid.uuid4()
    chart_id = uuid.uuid4()
    facts = build_interpretation_facts(
        profile_id=profile_id,
        chart_id=chart_id,
        dimensions=_payload()[0],
        archetypes=_payload()[1],
        environment=_payload()[2],
        resolution=_payload()[3],
        role_matches=_payload()[4],
        career_paths=_payload()[5],
    )

    assert facts.contract_version == CAREER_FACTS_CONTRACT_VERSION
    assert facts.profile_id == profile_id
    assert facts.chart_id == chart_id
    assert all(item.evidence_refs for item in (*facts.top_dimensions, *facts.low_dimensions))
    assert facts.low_dimensions[0].conditional_language_required
    assert facts.contradictions[0].code == "leadership_without_people_management"
    assert set(facts.section_contracts) == {
        "professional_summary", "work_style", "strengths", "decision_making",
        "leadership_and_influence", "optimal_environment", "risk_environment",
        "career_archetypes", "role_families", "career_paths",
    }
    assert all(contract.owned_fact_keys for contract in facts.section_contracts.values())
    assert all(contract.forbidden_fact_keys for contract in facts.section_contracts.values())
    serialized = facts.model_dump(mode="json")
    assert "raw_chart" not in str(serialized)
    assert "raw_answers" not in str(serialized)
    validate_interpretation_facts(facts)


def test_unsupported_role_or_path_is_rejected_before_provider_call() -> None:
    parts = _payload()
    facts = build_interpretation_facts(
        profile_id=uuid.uuid4(), chart_id=uuid.uuid4(), dimensions=parts[0], archetypes=parts[1],
        environment=parts[2], resolution=parts[3], role_matches=parts[4], career_paths=parts[5],
    )
    tampered = facts.model_copy(deep=True)
    tampered.career_paths[0].role_family_key = "invented_profession"
    called = False

    def provider(_payload):
        nonlocal called
        called = True
        return {"body": "should not run"}

    with pytest.raises(CareerFactsValidationError, match="unsupported career path"):
        call_provider_with_validated_facts(facts=tampered, provider=provider)
    assert called is False


def test_contradiction_loss_and_missing_lineage_are_rejected() -> None:
    parts = _payload()
    facts = build_interpretation_facts(
        profile_id=uuid.uuid4(), chart_id=uuid.uuid4(), dimensions=parts[0], archetypes=parts[1],
        environment=parts[2], resolution=parts[3], role_matches=parts[4], career_paths=parts[5],
    )
    facts.contradictions.clear()
    with pytest.raises(CareerFactsValidationError, match="contradiction lineage"):
        validate_interpretation_facts(facts, expected_contradiction_codes={"leadership_without_people_management"})

    facts = build_interpretation_facts(
        profile_id=uuid.uuid4(), chart_id=uuid.uuid4(), dimensions=parts[0], archetypes=parts[1],
        environment=parts[2], resolution=parts[3], role_matches=parts[4], career_paths=parts[5],
    )
    facts.top_dimensions[0].evidence_refs.clear()
    with pytest.raises(CareerFactsValidationError, match="missing evidence"):
        validate_interpretation_facts(facts)


def test_facts_build_versioned_persistable_rows() -> None:
    parts = _payload()
    profile_id = uuid.uuid4()
    chart_id = uuid.uuid4()
    facts = build_interpretation_facts(
        profile_id=profile_id, chart_id=chart_id, dimensions=parts[0], archetypes=parts[1],
        environment=parts[2], resolution=parts[3], role_matches=parts[4], career_paths=parts[5],
    )
    rows = build_interpretation_fact_rows(facts)

    assert rows
    assert all(row.career_profile_id == profile_id for row in rows)
    assert all(row.chart_id == chart_id for row in rows)
    assert all(row.source_version == CAREER_FACTS_CONTRACT_VERSION for row in rows)
    assert all(row.evidence_refs for row in rows)
    assert facts.role_matches[0].catalog_version == ROLE_CATALOG_VERSION
