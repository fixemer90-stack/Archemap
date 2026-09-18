"""Curated, validated deterministic facts for Career narrative generation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.career.archetype_engine import ArchetypeMatch
from app.modules.career.career_paths import CareerPathResult
from app.modules.career.dimension_engine import CareerDimensionResult
from app.modules.career.environment_engine import WorkEnvironmentResult
from app.modules.career.models import CareerInterpretationFact
from app.modules.career.profile_resolver import CareerProfileResolution
from app.modules.career.role_matching import ROLE_CATALOG, RoleMatchResult

CAREER_FACTS_CONTRACT_VERSION = "career_interpretation_facts_v1"
CAREER_FACTS_CURATION_VERSION = "career-facts-curation-1"
LOW_CONFIDENCE_THRESHOLD = 0.5


class CuratedDimensionFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_key: str
    dimension: str
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    scoring_version: str
    evidence_refs: list[str]
    conditional_language_required: bool


class CuratedArchetypeFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_key: str
    archetype_key: str
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    source_version: str
    evidence_refs: list[str]
    limitations: list[str]


class CuratedEnvironmentFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_key: str
    condition_key: str
    source_version: str
    evidence_refs: list[str]


class CuratedContradictionFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_key: str
    code: str
    dimension: str
    capability_score: float
    preference_key: str
    preference_value: str
    scenario_keys: list[str]
    source_version: str


class CuratedRoleFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_key: str
    role_family_key: str
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    category: str
    reasons: list[str]
    tensions: list[str]
    requirements: list[str]
    profession_examples: list[str]
    catalog_version: str


class CuratedPathStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_key: str
    transition_key: str | None
    prerequisites: list[str]


class CuratedPathFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_key: str
    role_family_key: str
    steps: list[CuratedPathStep]
    limitations: list[str]
    archetypal: bool
    graph_version: str


class CareerSectionContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_key: str
    owned_fact_keys: list[str]
    reference_fact_keys: list[str]
    forbidden_fact_keys: list[str]


class CareerInterpretationFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = CAREER_FACTS_CONTRACT_VERSION
    curation_version: str = CAREER_FACTS_CURATION_VERSION
    profile_id: UUID
    chart_id: UUID
    scoring_version: str
    top_dimensions: list[CuratedDimensionFact]
    low_dimensions: list[CuratedDimensionFact]
    career_archetypes: list[CuratedArchetypeFact]
    preferred_environment: list[CuratedEnvironmentFact]
    risk_environment: list[CuratedEnvironmentFact]
    confirmed_traits: list[str]
    contradictions: list[CuratedContradictionFact]
    user_preferences: list[str]
    context_constraints: list[str]
    role_matches: list[CuratedRoleFact]
    career_paths: list[CuratedPathFact]
    section_contracts: dict[str, CareerSectionContract]


class CareerFactsValidationError(ValueError):
    """Raised before any provider call when curated facts violate their contract."""


def build_interpretation_facts(
    *,
    profile_id: UUID,
    chart_id: UUID,
    dimensions: list[CareerDimensionResult] | tuple[CareerDimensionResult, ...],
    archetypes: tuple[ArchetypeMatch, ...],
    environment: WorkEnvironmentResult,
    resolution: CareerProfileResolution,
    role_matches: tuple[RoleMatchResult, ...],
    career_paths: tuple[CareerPathResult, ...],
) -> CareerInterpretationFacts:
    ordered_dimensions = sorted(dimensions, key=lambda item: (-item.score, item.dimension.value))
    dimension_facts = [_dimension_fact(item) for item in ordered_dimensions]
    high = [item for item in dimension_facts if item.score >= 50]
    low = [item for item in reversed(dimension_facts) if item.score < 50]
    archetype_facts = [
        CuratedArchetypeFact(
            fact_key=f"archetype:{item.key}",
            archetype_key=item.key,
            score=item.score,
            confidence=item.confidence,
            source_version=item.scoring_version,
            evidence_refs=list(item.evidence),
            limitations=list(item.limitations),
        )
        for item in archetypes
    ]
    preferred = [
        CuratedEnvironmentFact(
            fact_key=f"environment:preferred:{index}",
            condition_key=condition,
            source_version=environment.scoring_version,
            evidence_refs=[axis.key for axis in environment.axes],
        )
        for index, condition in enumerate(environment.preferred_conditions)
    ]
    risks = [
        CuratedEnvironmentFact(
            fact_key=f"environment:risk:{index}",
            condition_key=condition,
            source_version=environment.scoring_version,
            evidence_refs=[axis.key for axis in environment.axes],
        )
        for index, condition in enumerate(environment.risk_conditions)
    ]
    contradictions = [
        CuratedContradictionFact(
            fact_key=f"contradiction:{item.code}",
            code=item.code,
            dimension=item.dimension.value,
            capability_score=item.capability_score,
            preference_key=item.preference_key,
            preference_value=str(item.preference_value),
            scenario_keys=list(item.scenario_keys),
            source_version=resolution.resolver_version,
        )
        for item in resolution.contradictions
    ]
    roles = [
        CuratedRoleFact(
            fact_key=f"role:{item.role_family_key}",
            role_family_key=item.role_family_key,
            score=item.score,
            confidence=item.confidence,
            category=item.category.value,
            reasons=list(item.reasons),
            tensions=list(item.tensions),
            requirements=list(item.requirements),
            profession_examples=list(item.profession_examples),
            catalog_version=item.catalog_version,
        )
        for item in role_matches
    ]
    paths = [
        CuratedPathFact(
            fact_key=f"path:{index}:{item.role_family_key}",
            role_family_key=item.role_family_key,
            steps=[
                CuratedPathStep(
                    node_key=step.node_key,
                    transition_key=step.transition_key,
                    prerequisites=list(step.prerequisites),
                )
                for step in item.steps
            ],
            limitations=list(item.limitations),
            archetypal=item.archetypal,
            graph_version=item.graph_version,
        )
        for index, item in enumerate(career_paths)
    ]
    fact_groups = {
        "dimensions": [item.fact_key for item in dimension_facts],
        "archetypes": [item.fact_key for item in archetype_facts],
        "preferred_environment": [item.fact_key for item in preferred],
        "risk_environment": [item.fact_key for item in risks],
        "contradictions": [item.fact_key for item in contradictions],
        "roles": [item.fact_key for item in roles],
        "paths": [item.fact_key for item in paths],
    }
    facts = CareerInterpretationFacts(
        profile_id=profile_id,
        chart_id=chart_id,
        scoring_version=ordered_dimensions[0].scoring_version if ordered_dimensions else "unknown",
        top_dimensions=high,
        low_dimensions=low,
        career_archetypes=archetype_facts,
        preferred_environment=preferred,
        risk_environment=risks,
        confirmed_traits=list(resolution.confirmed_traits),
        contradictions=contradictions,
        user_preferences=list(resolution.preferences),
        context_constraints=list(resolution.context_constraints),
        role_matches=roles,
        career_paths=paths,
        section_contracts=_section_contracts(fact_groups),
    )
    validate_interpretation_facts(
        facts,
        expected_contradiction_codes={item.code for item in resolution.contradictions},
    )
    return facts


def _dimension_fact(item: CareerDimensionResult) -> CuratedDimensionFact:
    return CuratedDimensionFact(
        fact_key=f"dimension:{item.dimension.value}",
        dimension=item.dimension.value,
        score=item.score,
        confidence=item.confidence,
        scoring_version=item.scoring_version,
        evidence_refs=[f"{evidence.source_type}:{evidence.source_id}" for evidence in item.evidence],
        conditional_language_required=item.confidence < LOW_CONFIDENCE_THRESHOLD,
    )


def _section_contracts(groups: dict[str, list[str]]) -> dict[str, CareerSectionContract]:
    ownership = {
        "professional_summary": ("dimensions", "contradictions"),
        "work_style": ("dimensions", "preferred_environment"),
        "strengths": ("dimensions",),
        "decision_making": ("dimensions", "contradictions"),
        "leadership_and_influence": ("dimensions", "contradictions"),
        "optimal_environment": ("preferred_environment",),
        "risk_environment": ("risk_environment", "contradictions"),
        "career_archetypes": ("archetypes",),
        "role_families": ("roles",),
        "career_paths": ("paths",),
    }
    all_keys = {key for values in groups.values() for key in values}
    contracts: dict[str, CareerSectionContract] = {}
    previous: list[str] = []
    for section, group_names in ownership.items():
        owned = [key for name in group_names for key in groups[name]]
        if not owned:
            owned = groups["dimensions"][:1]
        reference = list(dict.fromkeys(previous[-4:]))
        forbidden = sorted(all_keys - set(owned) - set(reference))
        if not forbidden:
            forbidden = ["raw_chart", "raw_answers"]
        contracts[section] = CareerSectionContract(
            section_key=section,
            owned_fact_keys=owned,
            reference_fact_keys=reference,
            forbidden_fact_keys=forbidden,
        )
        previous.extend(owned)
    return contracts


def validate_interpretation_facts(
    facts: CareerInterpretationFacts,
    *,
    expected_contradiction_codes: set[str] | None = None,
) -> CareerInterpretationFacts:
    for dimension in (*facts.top_dimensions, *facts.low_dimensions):
        if not dimension.evidence_refs:
            raise CareerFactsValidationError(f"missing evidence for {dimension.fact_key}")
        if dimension.confidence < LOW_CONFIDENCE_THRESHOLD and not dimension.conditional_language_required:
            raise CareerFactsValidationError(f"low confidence is not conditional for {dimension.fact_key}")

    role_keys = {item.role_family_key for item in facts.role_matches}
    for role in facts.role_matches:
        definition = ROLE_CATALOG.get(role.role_family_key)
        if definition is None:
            raise CareerFactsValidationError(f"unsupported role family: {role.role_family_key}")
        unsupported_examples = set(role.profession_examples) - set(definition.profession_examples)
        if unsupported_examples:
            raise CareerFactsValidationError(f"unsupported profession examples: {sorted(unsupported_examples)}")
    for path in facts.career_paths:
        if path.role_family_key not in role_keys:
            raise CareerFactsValidationError(f"unsupported career path: {path.role_family_key}")

    actual_contradictions = {item.code for item in facts.contradictions}
    if expected_contradiction_codes is not None and actual_contradictions != expected_contradiction_codes:
        raise CareerFactsValidationError("contradiction lineage mismatch")

    payload = facts.model_dump(mode="json")
    forbidden_keys = {"raw_chart", "raw_answers", "birth_data", "planet_positions", "free_text"}
    present_keys = _collect_keys(payload)
    leaked = forbidden_keys & present_keys
    if leaked:
        raise CareerFactsValidationError(f"forbidden raw input keys: {sorted(leaked)}")

    all_fact_keys = _all_fact_keys(facts)
    for section in facts.section_contracts.values():
        unknown = set(section.owned_fact_keys + section.reference_fact_keys) - all_fact_keys
        if unknown:
            raise CareerFactsValidationError(f"unknown section fact keys: {sorted(unknown)}")
        if not section.forbidden_fact_keys:
            raise CareerFactsValidationError(f"missing forbidden facts for section {section.section_key}")
    return facts


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in _collect_keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in _collect_keys(item)}
    return set()


def _all_fact_keys(facts: CareerInterpretationFacts) -> set[str]:
    collections = (
        facts.top_dimensions,
        facts.low_dimensions,
        facts.career_archetypes,
        facts.preferred_environment,
        facts.risk_environment,
        facts.contradictions,
        facts.role_matches,
        facts.career_paths,
    )
    return {item.fact_key for collection in collections for item in collection}


def call_provider_with_validated_facts(
    *, facts: CareerInterpretationFacts, provider: Callable[[dict[str, Any]], Any]
) -> Any:
    validate_interpretation_facts(facts)
    return provider(facts.model_dump(mode="json"))


def build_interpretation_fact_rows(facts: CareerInterpretationFacts) -> list[CareerInterpretationFact]:
    rows: list[CareerInterpretationFact] = []
    section_by_fact = {
        fact_key: section.section_key
        for section in facts.section_contracts.values()
        for fact_key in section.owned_fact_keys
    }
    for collection in (
        facts.top_dimensions,
        facts.low_dimensions,
        facts.career_archetypes,
        facts.preferred_environment,
        facts.risk_environment,
        facts.contradictions,
        facts.role_matches,
        facts.career_paths,
    ):
        for item in collection:
            payload = item.model_dump(mode="json")
            evidence_refs = payload.get("evidence_refs") or [f"chart:{facts.chart_id}"]
            rows.append(
                CareerInterpretationFact(
                    career_profile_id=facts.profile_id,
                    chart_id=facts.chart_id,
                    fact_key=item.fact_key,
                    section_key=section_by_fact.get(item.fact_key, "professional_summary"),
                    source_version=facts.contract_version,
                    confidence=float(payload.get("confidence", 1.0)),
                    payload=payload,
                    evidence_refs=evidence_refs,
                )
            )
    return rows
