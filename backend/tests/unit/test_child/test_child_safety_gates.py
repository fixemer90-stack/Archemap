# ruff: noqa: RUF001

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from datetime import date
from typing import Any
from uuid import uuid4

import pytest

from app.modules.child.context_resolver import ContextResolution, ResolutionEntry, ResolverAgeSnapshot
from app.modules.child.guidance_facts import (
    GUIDANCE_FACTS_CONTRACT_VERSION,
    ChildGuidanceFacts,
    GuidanceInteractionScore,
    build_guidance_facts,
)
from app.modules.child.quality import (
    SECTION_CONTRACTS,
    GuidanceFactsQualityError,
    guidance_prompt_content,
    validate_guidance_facts,
)
from app.modules.child.questionnaire import ANSWER_VERSION
from app.modules.child.safety import (
    ChildSafetyViolation,
    NarrativeSectionCandidate,
    validate_child_narrative,
)
from app.reference_data.child.interaction_v1 import INTERACTION_SCORING_VERSION


def _entry(
    *,
    entry_id: str,
    dimension: str,
    confidence: float,
    action_code: str,
    reason_code: str = "interaction_above_strength_threshold",
) -> ResolutionEntry:
    score_id = {
        "boundary_fit": "11111111-1111-4111-8111-111111111111",
        "autonomy_balance": "22222222-2222-4222-8222-222222222222",
    }[dimension]
    return ResolutionEntry(
        id=entry_id,
        topic=dimension,
        dimension=dimension,
        confidence=confidence,
        source_refs=(f"child_interaction_scores:{score_id}:{INTERACTION_SCORING_VERSION}",),
        reason_code=reason_code,
        action_code=action_code,
    )


def _facts(*, unresolved_ambiguities: tuple[ResolutionEntry, ...] = ()) -> ChildGuidanceFacts:
    age_snapshot = ResolverAgeSnapshot(
        id=uuid4(),
        age_stage="3-6",
        as_of_date=date(2026, 10, 20),
        age_rules_version="child-age-mvp-1",
    )
    resolution = ContextResolution(
        resolver_version="child-context-resolver-mvp-1",
        input_hash="a" * 64,
        natural_strengths=(
            _entry(
                entry_id="strength-1",
                dimension="boundary_fit",
                confidence=0.82,
                action_code="adult_reuses_working_interaction_pattern",
            ),
        ),
        potential_friction=(
            _entry(
                entry_id="friction-1",
                dimension="autonomy_balance",
                confidence=0.38,
                action_code="adult_slows_down_and_observes_response",
                reason_code="interaction_below_friction_threshold",
            ),
        ),
        compensation_areas=(
            _entry(
                entry_id="compensation-1",
                dimension="autonomy_balance",
                confidence=0.38,
                action_code="adult_uses_nonautomatic_supportive_response",
                reason_code="friction_requires_conscious_adult_adjustment",
            ),
        ),
        age_relevant_guidance=(
            ResolutionEntry(
                id="age-1",
                topic="current_age",
                dimension=None,
                confidence=1.0,
                source_refs=(f"child_age_snapshots:{age_snapshot.id}:{age_snapshot.age_rules_version}",),
                reason_code="age_stage_3_6",
                action_code="adult_names_emotions_and_uses_playful_clear_limits",
                applicability="3-6",
            ),
        ),
        confirmations=(),
        contradictions=(),
        unresolved_ambiguities=unresolved_ambiguities,
    )
    scores = (
        GuidanceInteractionScore(
            dimension="boundary_fit",
            score=78.0,
            confidence=0.82,
            pattern="natural_match",
            scoring_version=INTERACTION_SCORING_VERSION,
            evidence_refs=(
                f"child_interaction_scores:11111111-1111-4111-8111-111111111111:{INTERACTION_SCORING_VERSION}",
            ),
        ),
        GuidanceInteractionScore(
            dimension="autonomy_balance",
            score=29.0,
            confidence=0.38,
            pattern="high_attention",
            scoring_version=INTERACTION_SCORING_VERSION,
            evidence_refs=(
                f"child_interaction_scores:22222222-2222-4222-8222-222222222222:{INTERACTION_SCORING_VERSION}",
            ),
        ),
    )
    return build_guidance_facts(
        parent_profile_id=uuid4(),
        child_id=uuid4(),
        generation_id=uuid4(),
        core_report_version=1,
        age_snapshot=age_snapshot,
        resolution=resolution,
        interaction_scores=scores,
    )


def _rehash_payload(payload: dict[str, Any]) -> None:
    registry = payload["evidence_registry"]
    context = next(metadata for metadata in registry.values() if metadata["source_type"] == "context_resolution")
    old_reference = next(reference for reference in registry if reference.startswith("guidance_contract:"))
    registry.pop(old_reference)
    unhashed = {key: value for key, value in payload.items() if key != "evidence_registry"}
    unhashed["evidence_registry"] = registry
    unhashed["source_contract"] = {
        "resolver_version": context["resolver_version"],
        "resolver_input_hash": context["input_hash"],
    }
    digest = hashlib.sha256(
        json.dumps(unhashed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    registry[f"guidance_contract:{digest}"] = {
        "source_type": "guidance_contract",
        "contract_version": GUIDANCE_FACTS_CONTRACT_VERSION,
        "input_hash": digest,
    }


def test_guidance_facts_are_bounded_evidence_backed_and_confidence_calibrated() -> None:
    facts = _facts()
    payload = facts.to_payload()

    assert payload["contract_version"] == GUIDANCE_FACTS_CONTRACT_VERSION
    assert set(payload) == {
        "contract_version",
        "parent_profile_id",
        "child_id",
        "core_report_version",
        "age_snapshot_id",
        "strong_matches",
        "friction_points",
        "parent_strengths",
        "compensation_areas",
        "recommended_actions",
        "avoid_patterns",
        "confidence_markers",
        "evidence_registry",
    }
    serialized = repr(payload).lower()
    assert "raw_chart" not in serialized
    assert "answers" not in serialized
    assert "birth_date" not in serialized
    assert "display_name" not in serialized
    assert payload["recommended_actions"]
    assert all(action["target"] == "caregiver" for action in payload["recommended_actions"])
    assert all(action["evidence_refs"] for action in payload["recommended_actions"])
    marked_ids = {marker["fact_id"] for marker in payload["confidence_markers"]}
    assert {"compensation:compensation-1", "action:friction-1", "action:compensation-1"} <= marked_ids
    validate_guidance_facts(facts)
    prompt_content = guidance_prompt_content(facts)
    assert set(prompt_content) == set(payload)
    assert "input_hash" not in repr(prompt_content)


def test_guidance_payload_is_deeply_immutable_and_low_confidence_scores_are_not_promoted() -> None:
    facts = _facts()
    first = facts.to_payload()
    first["recommended_actions"][0]["evidence_refs"].append("tampered")
    assert "tampered" not in facts.to_payload()["recommended_actions"][0]["evidence_refs"]

    low_score_facts = build_guidance_facts(
        parent_profile_id=facts.parent_profile_id,
        child_id=facts.child_id,
        generation_id=facts.generation_id,
        core_report_version=1,
        age_snapshot=ResolverAgeSnapshot(
            id=facts.age_snapshot_id,
            age_stage="3-6",
            as_of_date=date(2026, 10, 20),
            age_rules_version="child-age-mvp-1",
        ),
        resolution=ContextResolution(
            resolver_version="child-context-resolver-mvp-1",
            input_hash="b" * 64,
            natural_strengths=(),
            potential_friction=(),
            compensation_areas=(),
            age_relevant_guidance=(),
            confirmations=(),
            contradictions=(),
            unresolved_ambiguities=(),
        ),
        interaction_scores=(
            GuidanceInteractionScore(
                dimension="boundary_fit",
                score=90.0,
                confidence=0.1,
                pattern="natural_match",
                scoring_version=INTERACTION_SCORING_VERSION,
                evidence_refs=(
                    f"child_interaction_scores:11111111-1111-4111-8111-111111111111:{INTERACTION_SCORING_VERSION}",
                ),
            ),
        ),
    )
    assert low_score_facts.strong_matches == ()


def test_every_report_section_has_explicit_fact_ownership_and_safety_contract() -> None:
    assert set(SECTION_CONTRACTS) == {
        "how_to_use",
        "parent_style",
        "child_interaction_needs",
        "natural_contact",
        "friction_zones",
        "soothing_support",
        "boundaries_rules",
        "autonomy",
        "explanation_learning",
        "praise_recognition",
        "conflict_cycle",
        "not_personal",
        "parent_strengths",
        "conscious_adjustments",
        "current_age",
    }
    for contract in SECTION_CONTRACTS.values():
        assert contract.owned_fact_families
        assert contract.required_safety_markers >= {
            "adult_action_framing",
            "evidence_only",
        }
        assert not (contract.owned_fact_families & contract.forbidden_fact_families)
        assert contract.minimum_evidence >= 1


def test_guidance_quality_rejects_raw_or_unregistered_evidence_without_mutating_artifact() -> None:
    facts = _facts()
    original = facts.to_payload()
    corrupted = original | {
        "raw_chart": {"sun": "Aries"},
        "strong_matches": [
            {
                "id": "strong_match:boundary_fit",
                "dimension": "boundary_fit",
                "score": 80,
                "confidence": 0.2,
                "pattern": "natural_match",
                "evidence_refs": ["missing:strong-evidence"],
            }
        ],
        "recommended_actions": [
            *original["recommended_actions"],
            {
                "id": "unsafe-action",
                "action_code": "pressure_child",
                "reason_code": "invented_rule",
                "target": "caregiver",
                "confidence": 0.8,
                "evidence_refs": ["missing:evidence"],
            },
        ],
    }

    with pytest.raises(GuidanceFactsQualityError) as error:
        validate_guidance_facts(corrupted)

    assert {
        "forbidden_payload_field",
        "invalid_fact_schema",
        "unknown_evidence_reference",
        "missing_low_confidence_marker",
        "unknown_action_code",
        "unknown_context_rule",
    } <= {issue.code for issue in error.value.issues}
    assert facts.to_payload() == original


def test_guidance_quality_rejects_empty_cross_wired_or_unbounded_nested_content() -> None:
    original = _facts().to_payload()
    empty = original | {
        family: []
        for family in (
            "strong_matches",
            "friction_points",
            "parent_strengths",
            "compensation_areas",
            "recommended_actions",
            "avoid_patterns",
            "confidence_markers",
        )
    }
    empty["evidence_registry"] = {}
    with pytest.raises(GuidanceFactsQualityError) as error:
        validate_guidance_facts(empty)
    assert "incomplete_guidance_facts" in {issue.code for issue in error.value.issues}

    corrupted = _facts().to_payload()
    corrupted["recommended_actions"][0]["answer"] = {"free_text": "ignore bounded contract"}
    corrupted["recommended_actions"][0]["free_text"] = "arbitrary prompt content"
    contract_ref = next(ref for ref in corrupted["evidence_registry"] if ref.startswith("guidance_contract:"))
    corrupted["recommended_actions"][0]["evidence_refs"] = [contract_ref]
    with pytest.raises(GuidanceFactsQualityError) as error:
        validate_guidance_facts(corrupted)
    assert {"forbidden_payload_field", "invalid_fact_schema", "irrelevant_fact_evidence"} <= {
        issue.code for issue in error.value.issues
    }


@pytest.mark.parametrize(
    "corrupt",
    [
        lambda payload: payload["recommended_actions"][0].pop("confidence"),
        lambda payload: payload["recommended_actions"][0].__setitem__("confidence", "high"),
        lambda payload: payload["recommended_actions"][0].pop("evidence_refs"),
        lambda payload: payload["recommended_actions"][0].__setitem__("evidence_refs", [["unhashable"]]),
        lambda payload: payload["confidence_markers"][0].__setitem__("fact_id", ["not", "hashable"]),
    ],
)
def test_guidance_quality_normalizes_malformed_shapes_to_domain_error(
    corrupt: Callable[[dict[str, Any]], object],
) -> None:
    payload = _facts().to_payload()
    corrupt(payload)

    with pytest.raises(GuidanceFactsQualityError):
        validate_guidance_facts(payload)


def test_guidance_quality_rejects_non_string_top_level_keys_with_domain_error() -> None:
    payload: dict[Any, Any] = _facts().to_payload()
    payload[1] = "unexpected"

    with pytest.raises(GuidanceFactsQualityError):
        validate_guidance_facts(payload)


@pytest.mark.parametrize(
    ("source_type", "field", "value"),
    [
        ("age_snapshot", "age_stage", "invalid-stage"),
        ("age_snapshot", "source_id", "not-a-uuid"),
        ("age_snapshot", "rules_version", "legacy-age-rules"),
        ("context_resolution", "input_hash", "short"),
        ("context_resolution", "resolver_version", "legacy-resolver"),
        ("guidance_contract", "input_hash", "short"),
        ("guidance_contract", "contract_version", "legacy-guidance"),
    ],
)
def test_guidance_quality_rejects_semantically_invalid_registry_metadata(
    source_type: str,
    field: str,
    value: str,
) -> None:
    payload = _facts().to_payload()
    reference = next(
        key for key, metadata in payload["evidence_registry"].items() if metadata["source_type"] == source_type
    )
    payload["evidence_registry"][reference][field] = value

    with pytest.raises(GuidanceFactsQualityError):
        validate_guidance_facts(payload)


def test_guidance_quality_rejects_forged_versioned_source_reference() -> None:
    payload = _facts().to_payload()
    original = next(
        key for key, metadata in payload["evidence_registry"].items() if metadata["source_type"] == "interaction_score"
    )
    forged = "child_interaction_scores:not-a-uuid:wrong-key-version"
    payload["evidence_registry"][forged] = payload["evidence_registry"].pop(original)
    for family in (
        "strong_matches",
        "friction_points",
        "parent_strengths",
        "compensation_areas",
        "recommended_actions",
        "avoid_patterns",
    ):
        for fact in payload[family]:
            fact["evidence_refs"] = [
                forged if reference == original else reference for reference in fact["evidence_refs"]
            ]

    with pytest.raises(GuidanceFactsQualityError) as error:
        validate_guidance_facts(payload)
    assert "invalid_evidence_metadata" in {issue.code for issue in error.value.issues}


def test_guidance_quality_recomputes_guidance_contract_hash() -> None:
    payload = _facts().to_payload()
    original = next(key for key in payload["evidence_registry"] if key.startswith("guidance_contract:"))
    metadata = payload["evidence_registry"].pop(original)
    forged_hash = "f" * 64
    metadata["input_hash"] = forged_hash
    payload["evidence_registry"][f"guidance_contract:{forged_hash}"] = metadata

    with pytest.raises(GuidanceFactsQualityError) as error:
        validate_guidance_facts(payload)
    assert "invalid_guidance_hash" in {issue.code for issue in error.value.issues}


def test_guidance_quality_rejects_retagged_resolver_action() -> None:
    payload = _facts().to_payload()
    action = next(fact for fact in payload["recommended_actions"] if fact["id"] == "action:strength-1")
    action["topic"] = "current_age"

    with pytest.raises(GuidanceFactsQualityError) as error:
        validate_guidance_facts(payload)
    assert "invalid_resolver_semantics" in {issue.code for issue in error.value.issues}


def test_guidance_quality_rejects_score_fact_family_retagging_with_valid_hash() -> None:
    payload = _facts().to_payload()
    retagged = payload["strong_matches"].pop()
    retagged["score"] = 20.0
    retagged["pattern"] = "high_attention"
    payload["friction_points"].append(retagged)
    _rehash_payload(payload)

    with pytest.raises(GuidanceFactsQualityError) as error:
        validate_guidance_facts(payload)
    assert "irrelevant_fact_evidence" in {issue.code for issue in error.value.issues}


def test_guidance_quality_rejects_avoid_pattern_retagging_with_valid_hash() -> None:
    payload = _facts().to_payload()
    payload["avoid_patterns"][0]["dimension"] = "boundary_fit"
    payload["avoid_patterns"][0]["pattern_code"] = "escalate_pressure_during_boundary_protest"
    _rehash_payload(payload)

    with pytest.raises(GuidanceFactsQualityError) as error:
        validate_guidance_facts(payload)
    assert "irrelevant_fact_evidence" in {issue.code for issue in error.value.issues}


def test_guidance_quality_rejects_noncanonical_uuid_lineage_alias() -> None:
    payload = _facts().to_payload()
    canonical = next(
        reference
        for reference in payload["evidence_registry"]
        if reference.startswith("child_interaction_scores:22222222-")
    )
    alias = canonical.replace("22222222-2222-4222-8222-222222222222", "22222222222242228222222222222222")
    payload["evidence_registry"][alias] = payload["evidence_registry"].pop(canonical)
    for family in (
        "strong_matches",
        "friction_points",
        "parent_strengths",
        "compensation_areas",
        "recommended_actions",
        "avoid_patterns",
    ):
        for fact in payload[family]:
            fact["evidence_refs"] = [
                alias if reference == canonical else reference for reference in fact["evidence_refs"]
            ]
    _rehash_payload(payload)

    with pytest.raises(GuidanceFactsQualityError) as error:
        validate_guidance_facts(payload)
    assert "invalid_evidence_metadata" in {issue.code for issue in error.value.issues}


def test_guidance_facts_preserve_all_unresolved_ambiguity_actions() -> None:
    answer_one = f"child_answers:33333333-3333-4333-8333-333333333333:{ANSWER_VERSION}"
    answer_two = f"child_answers:44444444-4444-4444-8444-444444444444:{ANSWER_VERSION}"
    boundary_score = f"child_interaction_scores:11111111-1111-4111-8111-111111111111:{INTERACTION_SCORING_VERSION}"
    autonomy_score = f"child_interaction_scores:22222222-2222-4222-8222-222222222222:{INTERACTION_SCORING_VERSION}"
    ambiguities = (
        ResolutionEntry(
            id="ambiguity-missing",
            topic="boundaries",
            dimension="boundary_fit",
            confidence=0.0,
            source_refs=(),
            reason_code="selected_observation_missing",
            action_code="adult_observes_before_choosing_guidance",
        ),
        ResolutionEntry(
            id="ambiguity-variable",
            topic="autonomy",
            dimension="autonomy_balance",
            confidence=0.0,
            source_refs=(answer_one, autonomy_score),
            reason_code="observed_context_is_variable",
            action_code="adult_tracks_context_before_generalizing",
        ),
        ResolutionEntry(
            id="ambiguity-inconclusive",
            topic="boundaries",
            dimension="boundary_fit",
            confidence=0.2,
            source_refs=(answer_two, boundary_score),
            reason_code="evidence_not_directionally_conclusive",
            action_code="adult_tests_small_adjustment_and_observes",
        ),
    )

    facts = _facts(unresolved_ambiguities=ambiguities)
    validate_guidance_facts(facts)
    actions = {fact["id"]: fact for fact in facts.to_payload()["recommended_actions"]}

    assert {f"action:{entry.id}" for entry in ambiguities} <= set(actions)
    assert actions["action:ambiguity-missing"]["evidence_refs"][0].startswith("context_resolution:")
    prompt = guidance_prompt_content(facts)
    prompt_registry = prompt["evidence_registry"]
    prompt_references = {
        reference
        for family in (
            "strong_matches",
            "friction_points",
            "parent_strengths",
            "compensation_areas",
            "recommended_actions",
            "avoid_patterns",
        )
        for fact in prompt[family]
        for reference in fact["evidence_refs"]
    }
    assert prompt_references <= set(prompt_registry)
    context_metadata = next(
        metadata for metadata in prompt_registry.values() if metadata["source_type"] == "context_resolution"
    )
    assert "input_hash" not in context_metadata


@pytest.mark.parametrize(
    ("content", "category"),
    [
        ("У ребёнка проблемы с привязанностью.", "attachment_label"),
        ("Ваш ребёнок будет агрессивным.", "fatal_prediction"),
        ("Он вырастет неудачником.", "adult_outcome_prediction"),
        ("Ребёнок будет плохо учиться.", "ability_ranking"),
        ("Ваш ребёнок — манипулятор.", "fixed_personality_label"),
        ("Ребёнок специально выводит вас из себя.", "child_blame"),
        ("Вы плохой родитель.", "caregiver_blame"),
        ("Ему нужны антидепрессанты.", "medical_advice"),
        ("Подайте на лишение родительских прав.", "legal_advice"),
        ("Шлёпните ребёнка, чтобы он понял.", "unsafe_discipline"),
        ("Оставьте пятилетнего ребёнка одного дома.", "age_inappropriate_advice"),
        ("Марс делает ребёнка агрессивным.", "direct_planet_to_child_trait"),
        ("Ваш ребёнок склонен к депрессии.", "fatal_prediction"),
        ("Ребёнок не создан для командной работы.", "ability_ranking"),
        ("Ваш ребёнок будет манипулятором.", "fixed_personality_label"),
        ("Ваш ребёнок страдает аутизмом. Вы можете обратиться за помощью.", "diagnosis"),
        ("Оставьте шестилетнего дома без присмотра. Вы можете начать с часа.", "age_inappropriate_advice"),
        ("Your child has an attachment disorder.", "attachment_label"),
        ("Your child will become violent.", "fatal_prediction"),
        ("Ваш ребёнок будет страдать от депрессии. Вы можете подготовиться заранее.", "fatal_prediction"),
        ("Your child will be depressed. You can prepare now.", "fatal_prediction"),
        ("Your child is lazy and manipulative. You can demand more.", "fixed_personality_label"),
        ("Your child is stupid. You can demand more.", "ability_ranking"),
        ("У ребёнка СДВГ. Вы можете обратиться к специалисту.", "diagnosis"),
        ("Your child deliberately provokes you. You can impose a consequence.", "child_blame"),
        ("Leave your five-year-old child home alone. You can start with one hour.", "age_inappropriate_advice"),
        ("Your child is aggressive because Mars is prominent. You can stay calm.", "direct_planet_to_child_trait"),
        ("Вы можете учитывать, что у ребёнка депрессия.", "diagnosis"),
        ("Вы можете подготовиться: ребёнок обречён на провал.", "fatal_prediction"),
        ("Вы можете помнить, что ребёнок является ленивым.", "fixed_personality_label"),
        ("Вы можете лишать ребёнка еды за непослушание.", "unsafe_discipline"),
        ("You can account for the child having depression.", "diagnosis"),
        ("You can prepare because the child is doomed to fail.", "fatal_prediction"),
        ("You can withhold food from the child as punishment.", "unsafe_discipline"),
        ("Your child has depression. You can contact a specialist.", "diagnosis"),
        ("Give the child medication. You can start today.", "medical_advice"),
        ("Strike your child so they understand. You can be firm.", "unsafe_discipline"),
        ("У ребёнка депрессия. Вы можете обратиться к специалисту.", "diagnosis"),
        ("Дайте ребёнку таблетки. Вы можете начать сегодня.", "medical_advice"),
        ("Накажите ребёнка ремнём. Вы можете быть последовательны.", "unsafe_discipline"),
        ("You can let your five-year-old child drive a car alone.", "age_inappropriate_advice"),
        ("You can remember that your child is depressed.", "diagnosis"),
        ("You can beat your child with a belt.", "unsafe_discipline"),
        ("You can tell your five-year-old child to drive a car.", "age_inappropriate_advice"),
        ("You can administer medication to your child.", "medical_advice"),
        ("You can let your child operate a chainsaw.", "age_inappropriate_advice"),
        ("Your child is a psychopath.", "fixed_personality_label"),
        ("Ваш ребёнок — нарцисс.", "fixed_personality_label"),
        ("Your child will never succeed.", "fatal_prediction"),
        ("Ребёнок никогда не добьётся успеха.", "fatal_prediction"),
        ("You can lock your child in a room as punishment.", "unsafe_discipline"),
        ("Вы можете запереть ребёнка в комнате в наказание.", "unsafe_discipline"),
        ("Give your child antidepressants. You can start today.", "medical_advice"),
        ("Hit the child so they understand.", "unsafe_discipline"),
        ("Mars makes your child aggressive.", "direct_planet_to_child_trait"),
        ("Вы можете учитывать, что у ребёнка шизофрения.", "diagnosis"),
        ("Вы можете лишать ребёнка сна за непослушание.", "unsafe_discipline"),
        ("Вы можете увеличить ребёнку дозу лекарства.", "medical_advice"),
        ("Вы можете помнить, что ваш ребёнок эгоист.", "fixed_personality_label"),
        ("Вы можете помнить: Марс указывает, что ребёнок агрессивен.", "direct_planet_to_child_trait"),
        ("You can starve your child as punishment.", "unsafe_discipline"),
        ("Вы можете морить ребёнка голодом в наказание.", "unsafe_discipline"),
    ],
)
def test_negative_child_safety_corpus_is_blocked(content: str, category: str) -> None:
    candidate = NarrativeSectionCandidate(
        section_key="boundaries_rules",
        content=content,
        fact_refs=("action:strength-1",),
    )

    with pytest.raises(ChildSafetyViolation) as error:
        validate_child_narrative(candidate, guidance_facts=_facts())

    assert category in error.value.categories


def test_post_llm_gate_requires_supported_adult_action_and_conditional_low_confidence() -> None:
    unsafe = NarrativeSectionCandidate(
        section_key="autonomy",
        content="Ребёнок сопротивляется правилам. Нужно действовать жёстче.",
        fact_refs=("missing:fact",),
    )
    with pytest.raises(ChildSafetyViolation) as error:
        validate_child_narrative(unsafe, guidance_facts=_facts())
    assert set(error.value.categories) >= {
        "unsupported_recommendation",
        "missing_adult_action_framing",
    }

    safe = NarrativeSectionCandidate(
        section_key="autonomy",
        content=(
            "Если прямое требование усиливает сопротивление, вы можете предложить ребёнку два "
            "приемлемых варианта и посмотреть, помогает ли это спокойнее перейти к правилу."
        ),
        fact_refs=("compensation:compensation-1", "action:friction-1"),
    )
    validate_child_narrative(safe, guidance_facts=_facts())


def test_post_llm_gate_enforces_section_ownership_and_derives_confidence_from_facts() -> None:
    facts = _facts()
    cross_section = NarrativeSectionCandidate(
        section_key="autonomy",
        content="Вы можете продолжать спокойные и ясные границы.",
        fact_refs=("strong_match:boundary_fit",),
    )
    with pytest.raises(ChildSafetyViolation) as error:
        validate_child_narrative(cross_section, guidance_facts=facts)
    assert "section_fact_ownership" in error.value.categories

    unconditional_low_confidence = NarrativeSectionCandidate(
        section_key="autonomy",
        content="Вы можете предложить два приемлемых варианта.",
        fact_refs=("action:friction-1",),
    )
    with pytest.raises(ChildSafetyViolation) as error:
        validate_child_narrative(unconditional_low_confidence, guidance_facts=facts)
    assert "missing_conditional_language" in error.value.categories

    reference_only = NarrativeSectionCandidate(
        section_key="natural_contact",
        content="Вы можете продолжать спокойные и ясные границы.",
        fact_refs=("parent_strength:strength-1",),
    )
    with pytest.raises(ChildSafetyViolation) as error:
        validate_child_narrative(reference_only, guidance_facts=facts)
    assert "section_fact_ownership" in error.value.categories


def test_age_safety_uses_authoritative_guidance_facts_stage() -> None:
    candidate = NarrativeSectionCandidate(
        section_key="boundaries_rules",
        content="Оставьте пятилетнего ребёнка одного дома. Вы можете начать с часа.",
        fact_refs=("action:strength-1",),
    )
    with pytest.raises(ChildSafetyViolation) as error:
        validate_child_narrative(candidate, guidance_facts=_facts())
    assert "age_inappropriate_advice" in error.value.categories

    forged = replace(_facts(), age_stage="15-18")
    with pytest.raises(GuidanceFactsQualityError):
        validate_child_narrative(candidate, guidance_facts=forged)


@pytest.mark.parametrize(
    ("section_key", "fact_ref"),
    [
        ("current_age", "action:strength-1"),
        ("boundaries_rules", "action:age-1"),
    ],
)
def test_section_ownership_rejects_topically_unrelated_actions(section_key: str, fact_ref: str) -> None:
    candidate = NarrativeSectionCandidate(
        section_key=section_key,
        content="Вы можете спокойно наблюдать за реакцией ребёнка.",
        fact_refs=(fact_ref,),
    )

    with pytest.raises(ChildSafetyViolation) as error:
        validate_child_narrative(candidate, guidance_facts=_facts())
    assert "section_fact_ownership" in error.value.categories


@pytest.mark.parametrize(
    ("section_key", "fact_refs"),
    [
        ("current_age", ("action:age-1", "action:strength-1")),
        ("boundaries_rules", ("action:strength-1", "action:age-1")),
    ],
)
def test_section_ownership_rejects_mixed_topical_actions(
    section_key: str,
    fact_refs: tuple[str, ...],
) -> None:
    candidate = NarrativeSectionCandidate(
        section_key=section_key,
        content="Вы можете спокойно наблюдать за реакцией ребёнка.",
        fact_refs=fact_refs,
    )

    with pytest.raises(ChildSafetyViolation) as error:
        validate_child_narrative(candidate, guidance_facts=_facts())
    assert "section_fact_ownership" in error.value.categories


def test_current_age_section_accepts_production_age_topic() -> None:
    candidate = NarrativeSectionCandidate(
        section_key="current_age",
        content="Вы можете называть эмоции и сохранять ясные игровые границы.",
        fact_refs=("action:age-1",),
    )

    validate_child_narrative(candidate, guidance_facts=_facts())


def test_praise_section_rejects_unrelated_age_guidance() -> None:
    candidate = NarrativeSectionCandidate(
        section_key="praise_recognition",
        content="You can use this age-appropriate step.",
        fact_refs=("action:age-1",),
    )

    with pytest.raises(ChildSafetyViolation) as error:
        validate_child_narrative(candidate, guidance_facts=_facts())
    assert "section_fact_ownership" in error.value.categories


def test_post_llm_gate_normalizes_malformed_fact_references() -> None:
    candidate = NarrativeSectionCandidate(
        section_key="boundaries_rules",
        content="You can keep a calm boundary.",
        fact_refs=([],),  # type: ignore[arg-type]
    )

    with pytest.raises(ChildSafetyViolation) as error:
        validate_child_narrative(candidate, guidance_facts=_facts())
    assert "invalid_fact_reference" in error.value.categories
