"""Deterministic, bounded Context Resolver for Child Report S08."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date
from math import isfinite
from typing import Any, Final, cast
from uuid import UUID

from app.modules.child.age_resolver import AgeStage
from app.modules.child.questionnaire import ANSWER_VERSION, AnswerInput, questions_for_age_stage, validate_answer_set
from app.modules.child.scoring.types import InteractionDimension
from app.reference_data.child.interaction_v1 import INTERACTION_SCORING_VERSION

RESOLVER_VERSION: Final = "child-context-resolver-mvp-1"
STRENGTH_THRESHOLD: Final = 65.0
FRICTION_THRESHOLD: Final = 35.0
MIN_SCORE_CONFIDENCE: Final = 0.4
_ENTRY_NAMESPACE = uuid.UUID("f678d654-2465-45c1-b4f1-ea8ef9dfece1")


@dataclass(frozen=True, slots=True)
class ResolverAgeSnapshot:
    id: UUID
    age_stage: AgeStage
    as_of_date: date
    age_rules_version: str


@dataclass(frozen=True, slots=True)
class ResolutionEntry:
    id: str
    topic: str
    dimension: str | None
    confidence: float
    source_refs: tuple[str, ...]
    reason_code: str
    action_code: str
    priority: str = "normal"
    applicability: str = "general"


@dataclass(frozen=True, slots=True)
class ContextResolution:
    resolver_version: str
    input_hash: str
    natural_strengths: tuple[ResolutionEntry, ...]
    potential_friction: tuple[ResolutionEntry, ...]
    compensation_areas: tuple[ResolutionEntry, ...]
    age_relevant_guidance: tuple[ResolutionEntry, ...]
    confirmations: tuple[ResolutionEntry, ...]
    contradictions: tuple[ResolutionEntry, ...]
    unresolved_ambiguities: tuple[ResolutionEntry, ...]

    def all_entries(self) -> tuple[ResolutionEntry, ...]:
        return (
            *self.natural_strengths,
            *self.potential_friction,
            *self.compensation_areas,
            *self.age_relevant_guidance,
            *self.confirmations,
            *self.contradictions,
            *self.unresolved_ambiguities,
        )

    def to_payload(self) -> dict[str, Any]:
        def entry_payload(item: ResolutionEntry) -> dict[str, Any]:
            payload = asdict(item)
            payload["source_refs"] = list(item.source_refs)
            return payload

        return {
            "resolver_version": self.resolver_version,
            "input_hash": self.input_hash,
            "natural_strengths": [entry_payload(item) for item in self.natural_strengths],
            "potential_friction": [entry_payload(item) for item in self.potential_friction],
            "compensation_areas": [entry_payload(item) for item in self.compensation_areas],
            "age_relevant_guidance": [entry_payload(item) for item in self.age_relevant_guidance],
            "confirmations": [entry_payload(item) for item in self.confirmations],
            "contradictions": [entry_payload(item) for item in self.contradictions],
            "unresolved_ambiguities": [entry_payload(item) for item in self.unresolved_ambiguities],
        }


@dataclass(frozen=True, slots=True)
class _AnswerRule:
    dimension: InteractionDimension
    high_options: frozenset[str]
    low_options: frozenset[str]
    topic: str
    confirmation_action: str
    contradiction_action: str


_ANSWER_RULES: dict[str, _AnswerRule] = {
    "observation_soothing": _AnswerRule(
        InteractionDimension.SOOTHING_COMPATIBILITY,
        frozenset({"physical_contact", "talk", "quiet_presence"}),
        frozenset({"space", "switch_attention"}),
        "soothing",
        "continue_observed_soothing_support",
        "test_observed_soothing_before_escalating",
    ),
    "observation_boundary_reaction": _AnswerRule(
        InteractionDimension.BOUNDARY_FIT,
        frozenset({"accepts_calmly", "accepts_with_explanation"}),
        frozenset({"protests", "withdraws"}),
        "boundaries",
        "continue_calm_clear_boundaries",
        "reduce_pressure_and_explain_before_conflict",
    ),
    "parent_preference_explanation": _AnswerRule(
        InteractionDimension.COMMUNICATION_FIT,
        frozenset({"detailed", "show"}),
        frozenset({"short"}),
        "communication",
        "use_clear_age_appropriate_explanations",
        "vary_explanation_length_and_check_understanding",
    ),
    "observation_transition": _AnswerRule(
        InteractionDimension.TEMPO_FIT,
        frozenset({"easy", "warning_helps"}),
        frozenset({"hard"}),
        "transitions",
        "prepare_transitions_calmly",
        "add_transition_warning_and_processing_time",
    ),
    "observation_autonomy": _AnswerRule(
        InteractionDimension.AUTONOMY_BALANCE,
        frozenset({"often"}),
        frozenset({"rarely"}),
        "autonomy",
        "offer_age_appropriate_choice",
        "calibrate_choice_without_forcing_independence",
    ),
}

_AGE_ACTIONS: dict[AgeStage, str] = {
    "0-1": "adult_provides_coregulation_and_predictable_rhythm",
    "1-3": "adult_prepares_transitions_and_offers_bounded_choice",
    "3-6": "adult_names_emotions_and_uses_playful_clear_limits",
    "6-9": "adult_explains_rules_and_supports_practice_after_mistakes",
    "9-12": "adult_combines_structure_with_growing_responsibility",
    "12-15": "adult_respects_privacy_and_keeps_calm_availability",
    "15-18": "adult_negotiates_responsibility_and_preserves_safe_limits",
}


def _value(row: object, key: str) -> object:
    if isinstance(row, Mapping):
        return row.get(key)
    return getattr(row, key, None)


def _entry(
    *,
    kind: str,
    topic: str,
    dimension: str | None,
    confidence: float,
    source_refs: tuple[str, ...],
    reason_code: str,
    action_code: str,
    priority: str = "normal",
    applicability: str = "general",
) -> ResolutionEntry:
    identity = json.dumps(
        {
            "action": action_code,
            "dimension": dimension,
            "kind": kind,
            "reason": reason_code,
            "sources": sorted(source_refs),
            "topic": topic,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return ResolutionEntry(
        id=str(uuid.uuid5(_ENTRY_NAMESPACE, identity)),
        topic=topic,
        dimension=dimension,
        confidence=round(max(0.0, min(1.0, confidence)), 4),
        source_refs=tuple(sorted(source_refs)),
        reason_code=reason_code,
        action_code=action_code,
        priority=priority,
        applicability=applicability,
    )


def resolve_context(
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    questionnaire_session_id: UUID,
    age_snapshot: ResolverAgeSnapshot,
    interaction_scores: Sequence[object],
    answers: Sequence[object],
) -> ContextResolution:
    """Resolve safe codes without mutating or copying raw answer values into output."""

    expected_dimensions = tuple(dimension.value for dimension in InteractionDimension)
    scores_by_dimension: dict[str, object] = {}
    score_inputs: list[dict[str, object]] = []
    for row in interaction_scores:
        dimension = _value(row, "dimension")
        score = _value(row, "score")
        confidence = _value(row, "confidence")
        version = _value(row, "scoring_version")
        row_id = _value(row, "id")
        if (
            not isinstance(dimension, str)
            or dimension in scores_by_dimension
            or version != INTERACTION_SCORING_VERSION
            or isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not isfinite(float(score))
            or not 0 <= float(score) <= 100
            or isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not isfinite(float(confidence))
            or not 0 <= float(confidence) <= 1
            or not isinstance(row_id, UUID)
        ):
            raise ValueError("Interaction score set is malformed or uses another version")
        scores_by_dimension[dimension] = row
        score_inputs.append(
            {"id": str(row_id), "dimension": dimension, "score": float(score), "confidence": float(confidence)}
        )
    complete_dimensions = tuple(dimension for dimension in expected_dimensions if dimension in scores_by_dimension)
    if complete_dimensions != expected_dimensions or len(scores_by_dimension) != len(expected_dimensions):
        raise ValueError("Resolver requires exactly the canonical eight interaction scores")

    selected_questions = {question.key: question for question in questions_for_age_stage(age_snapshot.age_stage)}
    selected_keys = set(selected_questions)
    answers_by_key: dict[str, object] = {}
    answer_inputs: list[dict[str, str]] = []
    for row in answers:
        key = _value(row, "question_key")
        option = _value(row, "option")
        if option is None:
            payload = _value(row, "answer")
            option = payload.get("option") if isinstance(payload, Mapping) else None
        version = _value(row, "answer_version")
        row_id = _value(row, "id")
        if (
            not isinstance(key, str)
            or key not in selected_keys
            or key in answers_by_key
            or not isinstance(option, str)
            or version != ANSWER_VERSION
            or not isinstance(row_id, UUID)
        ):
            raise ValueError("Completed answer set is malformed or not selected for the pinned age")
        answers_by_key[key] = row
        answer_inputs.append(
            {
                "id": str(row_id),
                "question_key": key,
                "answer_version": version,
                "option": option,
            }
        )

    validate_answer_set(
        age_stage=age_snapshot.age_stage,
        answers=tuple(AnswerInput(question_key=item["question_key"], option=item["option"]) for item in answer_inputs),
        require_complete=True,
    )

    strengths: list[ResolutionEntry] = []
    friction: list[ResolutionEntry] = []
    compensation: list[ResolutionEntry] = []
    confirmations: list[ResolutionEntry] = []
    contradictions: list[ResolutionEntry] = []
    ambiguities: list[ResolutionEntry] = []

    for dimension in expected_dimensions:
        row = scores_by_dimension[dimension]
        score = float(cast(int | float, _value(row, "score")))
        confidence = float(cast(int | float, _value(row, "confidence")))
        score_ref = f"child_interaction_scores:{_value(row, 'id')}:{INTERACTION_SCORING_VERSION}"
        if confidence >= MIN_SCORE_CONFIDENCE and score >= STRENGTH_THRESHOLD:
            strengths.append(
                _entry(
                    kind="natural_strength",
                    topic=dimension,
                    dimension=dimension,
                    confidence=confidence,
                    source_refs=(score_ref,),
                    reason_code="interaction_above_strength_threshold",
                    action_code="adult_reuses_working_interaction_pattern",
                )
            )
        elif confidence >= MIN_SCORE_CONFIDENCE and score <= FRICTION_THRESHOLD:
            friction.append(
                _entry(
                    kind="potential_friction",
                    topic=dimension,
                    dimension=dimension,
                    confidence=confidence,
                    source_refs=(score_ref,),
                    reason_code="interaction_below_friction_threshold",
                    action_code="adult_slows_down_and_observes_response",
                    priority="high",
                )
            )
            compensation.append(
                _entry(
                    kind="compensation",
                    topic=dimension,
                    dimension=dimension,
                    confidence=confidence,
                    source_refs=(score_ref,),
                    reason_code="friction_requires_conscious_adult_adjustment",
                    action_code="adult_uses_nonautomatic_supportive_response",
                    priority="high",
                )
            )

    for question_key, rule in sorted(_ANSWER_RULES.items()):
        row = answers_by_key.get(question_key)
        if row is None:
            ambiguities.append(
                _entry(
                    kind="ambiguity",
                    topic=rule.topic,
                    dimension=rule.dimension.value,
                    confidence=0.0,
                    source_refs=(),
                    reason_code="selected_observation_missing",
                    action_code="adult_observes_before_choosing_guidance",
                )
            )
            continue
        option = cast(str, _value(row, "option"))
        if not option:
            payload = _value(row, "answer")
            option = cast(str, payload["option"]) if isinstance(payload, Mapping) else ""
        answer_ref = f"child_answers:{_value(row, 'id')}:{ANSWER_VERSION}"
        score_row = scores_by_dimension[rule.dimension.value]
        score = float(cast(int | float, _value(score_row, "score")))
        confidence = float(cast(int | float, _value(score_row, "confidence")))
        score_ref = f"child_interaction_scores:{_value(score_row, 'id')}:{INTERACTION_SCORING_VERSION}"
        if option == "depends":
            ambiguities.append(
                _entry(
                    kind="ambiguity",
                    topic=rule.topic,
                    dimension=rule.dimension.value,
                    confidence=0.0,
                    source_refs=(answer_ref, score_ref),
                    reason_code="observed_context_is_variable",
                    action_code="adult_tracks_context_before_generalizing",
                )
            )
            continue
        score_side = "high" if score >= STRENGTH_THRESHOLD else "low" if score <= FRICTION_THRESHOLD else "neutral"
        answer_side = "high" if option in rule.high_options else "low" if option in rule.low_options else "neutral"
        if score_side == "neutral" or answer_side == "neutral":
            ambiguities.append(
                _entry(
                    kind="ambiguity",
                    topic=rule.topic,
                    dimension=rule.dimension.value,
                    confidence=round(confidence * 0.5, 4),
                    source_refs=(answer_ref, score_ref),
                    reason_code="evidence_not_directionally_conclusive",
                    action_code="adult_tests_small_adjustment_and_observes",
                )
            )
        elif score_side == answer_side:
            confirmations.append(
                _entry(
                    kind="confirmation",
                    topic=rule.topic,
                    dimension=rule.dimension.value,
                    confidence=confidence,
                    source_refs=(answer_ref, score_ref),
                    reason_code="observation_confirms_interaction_expectation",
                    action_code=rule.confirmation_action,
                )
            )
        else:
            contradictions.append(
                _entry(
                    kind="contradiction",
                    topic=rule.topic,
                    dimension=rule.dimension.value,
                    confidence=round(confidence * 0.5, 4),
                    source_refs=(answer_ref, score_ref),
                    reason_code="observation_opposes_interaction_expectation",
                    action_code=rule.contradiction_action,
                    priority="high",
                )
            )

    constraint_rows = [answers_by_key.get(key) for key in ("family_constraint_routine", "family_constraint_schedule")]
    constrained = any(
        row is not None
        and (
            (_value(row, "option") in {"limited", "rarely", "variable"})
            or (
                isinstance(_value(row, "answer"), Mapping)
                and cast(Mapping[str, object], _value(row, "answer")).get("option") in {"limited", "rarely", "variable"}
            )
        )
        for row in constraint_rows
    )
    age_entry = _entry(
        kind="age_guidance",
        topic="current_age",
        dimension=None,
        confidence=1.0,
        source_refs=(f"child_age_snapshots:{age_snapshot.id}:{age_snapshot.age_rules_version}",),
        reason_code=f"age_stage_{age_snapshot.age_stage.replace('-', '_')}",
        action_code=_AGE_ACTIONS[age_snapshot.age_stage],
        priority="high" if constrained else "normal",
        applicability="adapt_to_family_capacity" if constrained else "general",
    )

    canonical_input = {
        "age": {
            "age_rules_version": age_snapshot.age_rules_version,
            "age_snapshot_id": str(age_snapshot.id),
            "age_stage": age_snapshot.age_stage,
        },
        "answers": sorted(answer_inputs, key=lambda item: item["question_key"]),
        "child_profile_id": str(child_profile_id),
        "generation_id": str(generation_id),
        "questionnaire_session_id": str(questionnaire_session_id),
        "resolver_version": RESOLVER_VERSION,
        "scores": sorted(score_inputs, key=lambda item: cast(str, item["dimension"])),
    }
    input_hash = hashlib.sha256(json.dumps(canonical_input, separators=(",", ":"), sort_keys=True).encode()).hexdigest()

    def ordering(item: ResolutionEntry) -> tuple[str, str, str, str]:
        return item.topic, item.dimension or "", item.reason_code, item.id

    return ContextResolution(
        resolver_version=RESOLVER_VERSION,
        input_hash=input_hash,
        natural_strengths=tuple(sorted(strengths, key=ordering)),
        potential_friction=tuple(sorted(friction, key=ordering)),
        compensation_areas=tuple(sorted(compensation, key=ordering)),
        age_relevant_guidance=(age_entry,),
        confirmations=tuple(sorted(confirmations, key=ordering)),
        contradictions=tuple(sorted(contradictions, key=ordering)),
        unresolved_ambiguities=tuple(sorted(ambiguities, key=ordering)),
    )
