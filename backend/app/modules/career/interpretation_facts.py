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
from app.modules.career.questionnaire import sanitize_bounded_text
from app.modules.career.role_matching import ROLE_CATALOG, RoleMatchResult

CAREER_FACTS_CONTRACT_VERSION = "career_interpretation_facts_v2"
CAREER_FACTS_CURATION_VERSION = "career-facts-curation-2"
LOW_CONFIDENCE_THRESHOLD = 0.5

_LEGACY_ROLE_EXAMPLES: dict[str, tuple[str, ...]] = {
    "architecture": ("Solution Architect", "Systems Architect", "Lead Engineer"),
    "product": ("Product Manager", "Product Operations Lead"),
    "strategy": ("Strategy Lead", "Corporate Strategist"),
    "analytics": ("Data Analyst", "Business Intelligence Analyst"),
    "consulting": ("Management Consultant", "Independent Advisor"),
    "operations": ("Operations Lead", "Program Manager"),
    "research": ("Research Scientist", "UX Researcher"),
    "management": ("Engineering Manager", "Department Head"),
    "entrepreneurship": ("Founder", "Independent Venture Builder"),
}


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
    evidence_refs: list[str]


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
    evidence_refs: list[str]


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
    evidence_refs: list[str]


class CuratedUserContextFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_key: str
    context_key: str
    context_value: str = Field(min_length=1, max_length=500)
    evidence_refs: list[str]


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
    user_context: list[CuratedUserContextFact] = Field(default_factory=list)
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
    questionnaire_evidence: dict[str, UUID],
    questionnaire_context: dict[str, str] | None = None,
) -> CareerInterpretationFacts:
    ordered_dimensions = sorted(dimensions, key=lambda item: (-item.score, item.dimension.value))
    dimension_facts = [_dimension_fact(item) for item in ordered_dimensions]
    dimension_evidence = {item.dimension: list(item.evidence_refs) for item in dimension_facts}
    questionnaire_refs = [f"career_answer:{answer_id}" for answer_id in questionnaire_evidence.values()]
    high = [item for item in dimension_facts if item.score >= 50]
    low = [item for item in reversed(dimension_facts) if item.score < 50]
    archetype_facts = [
        CuratedArchetypeFact(
            fact_key=f"archetype:{item.key}",
            archetype_key=item.key,
            score=item.score,
            confidence=item.confidence,
            source_version=item.scoring_version,
            evidence_refs=_refs_for_dimension_keys(item.evidence, dimension_evidence),
            limitations=list(item.limitations),
        )
        for item in archetypes
    ]
    preferred = [
        CuratedEnvironmentFact(
            fact_key=f"environment:preferred:{index}",
            condition_key=condition,
            source_version=environment.scoring_version,
            evidence_refs=_environment_evidence_refs(environment, dimension_evidence),
        )
        for index, condition in enumerate(environment.preferred_conditions)
    ]
    risks = [
        CuratedEnvironmentFact(
            fact_key=f"environment:risk:{index}",
            condition_key=condition,
            source_version=environment.scoring_version,
            evidence_refs=_environment_evidence_refs(environment, dimension_evidence),
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
            evidence_refs=_unique_refs(
                [
                    *dimension_evidence.get(item.dimension.value, []),
                    _answer_ref(questionnaire_evidence, item.preference_key),
                ]
            ),
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
            evidence_refs=_role_evidence_refs(
                role_family_key=item.role_family_key,
                dimension_evidence=dimension_evidence,
                environment=environment,
                questionnaire_refs=questionnaire_refs,
            ),
        )
        for item in role_matches
    ]
    role_evidence = {item.role_family_key: list(item.evidence_refs) for item in roles}
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
            evidence_refs=role_evidence.get(item.role_family_key, []),
        )
        for index, item in enumerate(career_paths)
    ]
    context_facts = [
        CuratedUserContextFact(
            fact_key=f"user_context:{key}",
            context_key=key,
            context_value=sanitize_bounded_text(value),
            evidence_refs=[_answer_ref(questionnaire_evidence, key)],
        )
        for key in ("current_activity", "change_goal", "current_constraints")
        if (value := (questionnaire_context or {}).get(key))
    ]
    fact_groups = {
        "dimensions": [item.fact_key for item in dimension_facts],
        "archetypes": [item.fact_key for item in archetype_facts],
        "preferred_environment": [item.fact_key for item in preferred],
        "risk_environment": [item.fact_key for item in risks],
        "contradictions": [item.fact_key for item in contradictions],
        "roles": [item.fact_key for item in roles],
        "paths": [item.fact_key for item in paths],
        "user_context": [item.fact_key for item in context_facts],
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
        user_context=context_facts,
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


def _answer_ref(questionnaire_evidence: dict[str, UUID], question_key: str) -> str:
    answer_id = questionnaire_evidence.get(question_key)
    if answer_id is None:
        raise CareerFactsValidationError(f"missing questionnaire evidence for {question_key}")
    return f"career_answer:{answer_id}"


def _unique_refs(refs: list[str]) -> list[str]:
    return list(dict.fromkeys(refs))


def _refs_for_dimension_keys(keys: tuple[str, ...], dimension_evidence: dict[str, list[str]]) -> list[str]:
    return _unique_refs([ref for key in keys for ref in dimension_evidence.get(key.removeprefix("dimension:"), [])])


def _environment_evidence_refs(
    environment: WorkEnvironmentResult,
    dimension_evidence: dict[str, list[str]],
) -> list[str]:
    return _unique_refs(
        [ref for axis in environment.axes for key in axis.evidence for ref in dimension_evidence.get(key, [])]
    )


def _role_evidence_refs(
    *,
    role_family_key: str,
    dimension_evidence: dict[str, list[str]],
    environment: WorkEnvironmentResult,
    questionnaire_refs: list[str],
) -> list[str]:
    definition = ROLE_CATALOG[role_family_key]
    refs = [ref for key in definition.weights for ref in dimension_evidence.get(key.value, [])]
    environment_by_key = {axis.key: axis for axis in environment.axes}
    for axis_key in definition.environment_axes:
        axis = environment_by_key.get(axis_key)
        if axis is not None:
            refs.extend(ref for key in axis.evidence for ref in dimension_evidence.get(key, []))
    return _unique_refs([*refs, *questionnaire_refs])


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
        if section in {"role_families", "career_paths"}:
            reference = list(dict.fromkeys([*groups["user_context"], *reference]))
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
    evidence_collections = (
        facts.top_dimensions,
        facts.low_dimensions,
        facts.career_archetypes,
        facts.preferred_environment,
        facts.risk_environment,
        facts.contradictions,
        facts.user_context,
        facts.role_matches,
        facts.career_paths,
    )
    for collection in evidence_collections:
        for item in collection:
            if not item.evidence_refs:
                raise CareerFactsValidationError(f"missing evidence for {item.fact_key}")
            if any(ref.startswith("chart:") for ref in item.evidence_refs):
                raise CareerFactsValidationError(f"imprecise evidence for {item.fact_key}")
    for dimension in (*facts.top_dimensions, *facts.low_dimensions):
        if dimension.confidence < LOW_CONFIDENCE_THRESHOLD and not dimension.conditional_language_required:
            raise CareerFactsValidationError(f"low confidence is not conditional for {dimension.fact_key}")

    role_keys = {item.role_family_key for item in facts.role_matches}
    for role in facts.role_matches:
        definition = ROLE_CATALOG.get(role.role_family_key)
        if definition is None:
            raise CareerFactsValidationError(f"unsupported role family: {role.role_family_key}")
        supported_examples = (
            _LEGACY_ROLE_EXAMPLES.get(role.role_family_key, ())
            if role.catalog_version == "career-role-catalog-1"
            else definition.profession_examples
        )
        unsupported_examples = set(role.profession_examples) - set(supported_examples)
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
        facts.user_context,
        facts.role_matches,
        facts.career_paths,
    )
    return {item.fact_key for collection in collections for item in collection}


def call_provider_with_validated_facts(
    *, facts: CareerInterpretationFacts, provider: Callable[[dict[str, Any]], Any]
) -> Any:
    validate_interpretation_facts(facts)
    return provider(facts.model_dump(mode="json"))


def build_interpretation_fact_rows(
    facts: CareerInterpretationFacts, *, generation_id: UUID
) -> list[CareerInterpretationFact]:
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
        facts.user_context,
        facts.role_matches,
        facts.career_paths,
    ):
        for item in collection:
            payload = item.model_dump(mode="json")
            evidence_refs = payload.get("evidence_refs") or []
            if not evidence_refs:
                raise CareerFactsValidationError(f"missing evidence for {item.fact_key}")
            rows.append(
                CareerInterpretationFact(
                    career_profile_id=facts.profile_id,
                    chart_id=facts.chart_id,
                    generation_id=generation_id,
                    fact_key=item.fact_key,
                    section_key=section_by_fact.get(item.fact_key, "professional_summary"),
                    source_version=facts.contract_version,
                    confidence=float(payload.get("confidence", 1.0)),
                    payload=payload,
                    evidence_refs=evidence_refs,
                )
            )
    return rows
