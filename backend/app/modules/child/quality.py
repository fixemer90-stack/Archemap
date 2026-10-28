"""Pre-LLM completeness, evidence and section-ownership gates for Child Report."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any, Final
from uuid import UUID

from app.modules.child.age_resolver import AGE_RULES_VERSION
from app.modules.child.context_resolver import CONTEXT_ACTION_CODES, CONTEXT_REASON_CODES, RESOLVER_VERSION
from app.modules.child.guidance_facts import (
    CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION,
    GUIDANCE_AVOID_PATTERN_CODES,
    GUIDANCE_FACTS_CONTRACT_VERSION,
    LOW_CONFIDENCE_THRESHOLD,
    ChildGuidanceFacts,
)
from app.modules.child.questionnaire import ANSWER_VERSION
from app.modules.child.scoring.types import (
    ChildNeedDimension,
    InteractionDimension,
    InteractionPattern,
    ParentStyleDimension,
)
from app.reference_data.child.child_needs_v1 import CHILD_NEEDS_SCORING_VERSION
from app.reference_data.child.interaction_v1 import INTERACTION_SCORING_VERSION
from app.reference_data.child.parent_style_v1 import PARENT_STYLE_SCORING_VERSION

_ALLOWED_PAYLOAD_FIELDS: Final = frozenset(
    {
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
)
_FORBIDDEN_PAYLOAD_FIELDS: Final = frozenset(
    {
        "raw_chart",
        "chart",
        "answer",
        "answers",
        "questionnaire_answers",
        "birth_date",
        "birth_time",
        "birth_place",
        "display_name",
        "name",
        "provider_secret",
        "api_key",
        "free_text",
    }
)
_FACT_FAMILIES: Final = (
    "strong_matches",
    "friction_points",
    "parent_strengths",
    "compensation_areas",
    "recommended_actions",
    "avoid_patterns",
)
_FACT_FIELDS: Final[dict[str, frozenset[str]]] = {
    "source_profiles": frozenset(
        {"id", "source_kind", "dimension", "score", "confidence", "scoring_version", "evidence_refs"}
    ),
    "strong_matches": frozenset({"id", "dimension", "score", "confidence", "pattern", "evidence_refs"}),
    "friction_points": frozenset({"id", "dimension", "score", "confidence", "pattern", "evidence_refs"}),
    "parent_strengths": frozenset(
        {"id", "topic", "dimension", "confidence", "reason_code", "action_code", "evidence_refs"}
    ),
    "compensation_areas": frozenset(
        {"id", "topic", "dimension", "confidence", "reason_code", "action_code", "evidence_refs"}
    ),
    "recommended_actions": frozenset(
        {
            "id",
            "topic",
            "dimension",
            "applicability",
            "action_code",
            "reason_code",
            "target",
            "confidence",
            "evidence_refs",
        }
    ),
    "avoid_patterns": frozenset({"id", "dimension", "pattern_code", "target", "confidence", "evidence_refs"}),
}
_REGISTRY_FIELDS: Final[dict[str, frozenset[str]]] = {
    "source_profile": frozenset({"source_type", "source_kind", "dimension", "score", "confidence", "scoring_version"}),
    "age_snapshot": frozenset(
        {"source_type", "source_id", "age_stage", "rules_version", "resolver_entry_ids", "reason_codes"}
    ),
    "context_resolution": frozenset(
        {"source_type", "resolver_version", "input_hash", "resolver_entry_ids", "reason_codes"}
    ),
    "interaction_score": frozenset(
        {
            "source_type",
            "dimension",
            "score",
            "pattern",
            "scoring_version",
            "confidence",
            "resolver_entry_ids",
            "reason_codes",
        }
    ),
    "child_answers": frozenset({"source_type", "resolver_entry_ids", "reason_codes"}),
    "child_interaction_scores": frozenset({"source_type", "resolver_entry_ids", "reason_codes"}),
    "child_age_snapshots": frozenset({"source_type", "resolver_entry_ids", "reason_codes"}),
    "guidance_contract": frozenset({"source_type", "contract_version", "input_hash"}),
}
_INTERACTION_DIMENSIONS: Final = frozenset(dimension.value for dimension in InteractionDimension)
_INTERACTION_PATTERNS: Final = frozenset(pattern.value for pattern in InteractionPattern)
_MAX_FACTS_PER_FAMILY: Final = 64
_MAX_EVIDENCE_REFS: Final = 16
_MAX_REGISTRY_ENTRIES: Final = 256
_AGE_STAGES: Final = frozenset({"0-1", "1-3", "3-6", "6-9", "9-12", "12-15", "15-18"})
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_AGE_ACTION_CONTRACTS: Final = {
    "0-1": "adult_provides_coregulation_and_predictable_rhythm",
    "1-3": "adult_prepares_transitions_and_offers_bounded_choice",
    "3-6": "adult_names_emotions_and_uses_playful_clear_limits",
    "6-9": "adult_explains_rules_and_supports_practice_after_mistakes",
    "9-12": "adult_combines_structure_with_growing_responsibility",
    "12-15": "adult_respects_privacy_and_keeps_calm_availability",
    "15-18": "adult_negotiates_responsibility_and_preserves_safe_limits",
}
_ANSWER_ACTION_CONTRACTS: Final = {
    "continue_observed_soothing_support": (
        "soothing",
        "soothing_compatibility",
        "observation_confirms_interaction_expectation",
    ),
    "test_observed_soothing_before_escalating": (
        "soothing",
        "soothing_compatibility",
        "observation_opposes_interaction_expectation",
    ),
    "continue_calm_clear_boundaries": ("boundaries", "boundary_fit", "observation_confirms_interaction_expectation"),
    "reduce_pressure_and_explain_before_conflict": (
        "boundaries",
        "boundary_fit",
        "observation_opposes_interaction_expectation",
    ),
    "use_clear_age_appropriate_explanations": (
        "communication",
        "communication_fit",
        "observation_confirms_interaction_expectation",
    ),
    "vary_explanation_length_and_check_understanding": (
        "communication",
        "communication_fit",
        "observation_opposes_interaction_expectation",
    ),
    "prepare_transitions_calmly": ("transitions", "tempo_fit", "observation_confirms_interaction_expectation"),
    "add_transition_warning_and_processing_time": (
        "transitions",
        "tempo_fit",
        "observation_opposes_interaction_expectation",
    ),
    "offer_age_appropriate_choice": ("autonomy", "autonomy_balance", "observation_confirms_interaction_expectation"),
    "calibrate_choice_without_forcing_independence": (
        "autonomy",
        "autonomy_balance",
        "observation_opposes_interaction_expectation",
    ),
}
_ANSWER_TOPIC_DIMENSIONS: Final = frozenset(
    (topic, dimension) for topic, dimension, _ in _ANSWER_ACTION_CONTRACTS.values()
)
_AVOID_PATTERN_BY_DIMENSION: Final = {
    "emotional_attunement": "dismiss_child_signals",
    "boundary_fit": "escalate_pressure_during_boundary_protest",
    "soothing_compatibility": "repeat_soothing_that_increases_distress",
    "communication_fit": "overload_with_explanations_during_conflict",
    "autonomy_balance": "interpret_independence_as_disobedience",
    "learning_interaction": "correct_before_checking_understanding",
    "conflict_pattern": "mirror_child_escalation",
    "tempo_fit": "expect_behavior_above_current_age_stage",
}


@dataclass(frozen=True, slots=True)
class SectionContract:
    owned_fact_families: frozenset[str]
    reference_fact_families: frozenset[str]
    forbidden_fact_families: frozenset[str]
    required_safety_markers: frozenset[str]
    minimum_evidence: int
    low_confidence_behavior: str
    owned_topics: frozenset[str]
    owned_dimensions: frozenset[str]


_BASE_SAFETY = frozenset({"adult_action_framing", "evidence_only", "no_fixed_child_labels"})
_ALL_SECTION_FACT_FAMILIES = frozenset(_FACT_FAMILIES)


def _section(
    *owned: str,
    reference: tuple[str, ...] = (),
    topics: tuple[str, ...] = (),
    dimensions: tuple[str, ...] = (),
) -> SectionContract:
    allowed = frozenset((*owned, *reference))
    return SectionContract(
        owned_fact_families=frozenset(owned),
        reference_fact_families=frozenset(reference),
        forbidden_fact_families=_ALL_SECTION_FACT_FAMILIES - allowed,
        required_safety_markers=_BASE_SAFETY,
        minimum_evidence=1,
        low_confidence_behavior="conditional",
        owned_topics=frozenset(topics),
        owned_dimensions=frozenset(dimensions),
    )


SECTION_CONTRACTS: Final[dict[str, SectionContract]] = {
    "how_to_use": _section("recommended_actions"),
    "parent_style": _section("parent_strengths", reference=("strong_matches",)),
    "child_interaction_needs": _section("recommended_actions", reference=("friction_points",)),
    "natural_contact": _section("strong_matches", reference=("parent_strengths",)),
    "friction_zones": _section("friction_points", reference=("avoid_patterns",)),
    "soothing_support": _section(
        "recommended_actions",
        reference=("friction_points",),
        topics=("soothing",),
        dimensions=("soothing_compatibility",),
    ),
    "boundaries_rules": _section(
        "recommended_actions",
        reference=("avoid_patterns",),
        topics=("boundaries",),
        dimensions=("boundary_fit",),
    ),
    "autonomy": _section(
        "compensation_areas",
        reference=("recommended_actions",),
        topics=("autonomy",),
        dimensions=("autonomy_balance",),
    ),
    "explanation_learning": _section(
        "recommended_actions",
        reference=("strong_matches",),
        topics=("communication", "learning"),
        dimensions=("communication_fit", "learning_interaction"),
    ),
    "praise_recognition": _section(
        "recommended_actions",
        reference=("parent_strengths",),
        topics=("soothing", "boundaries", "communication", "transitions", "autonomy"),
        dimensions=tuple(_INTERACTION_DIMENSIONS),
    ),
    "conflict_cycle": _section("avoid_patterns", reference=("friction_points",)),
    "not_personal": _section("avoid_patterns", reference=("friction_points",)),
    "parent_strengths": _section("parent_strengths", reference=("strong_matches",)),
    "conscious_adjustments": _section("compensation_areas", reference=("avoid_patterns",)),
    "current_age": _section("recommended_actions", topics=("current_age",)),
}


@dataclass(frozen=True, slots=True)
class GuidanceQualityIssue:
    code: str
    path: str


def fact_families(version: str) -> tuple[str, ...]:
    return (
        (*_FACT_FAMILIES, "source_profiles") if version == CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION else _FACT_FAMILIES
    )


def section_contracts(version: str) -> dict[str, SectionContract]:
    if version != CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION:
        return SECTION_CONTRACTS
    return {
        **SECTION_CONTRACTS,
        "how_to_use": _section("recommended_actions", topics=("current_age",)),
        "parent_style": _section("source_profiles"),
        "child_interaction_needs": _section("source_profiles"),
        "parent_strengths": _section("source_profiles"),
        "soothing_support": _section(
            "recommended_actions", "source_profiles", topics=("soothing",), dimensions=("soothing_compatibility",)
        ),
        "boundaries_rules": _section(
            "recommended_actions", "source_profiles", topics=("boundaries",), dimensions=("boundary_fit",)
        ),
        "autonomy": _section(
            "recommended_actions", "source_profiles", topics=("autonomy",), dimensions=("autonomy_balance",)
        ),
        "explanation_learning": _section(
            "recommended_actions",
            "source_profiles",
            topics=("communication", "learning"),
            dimensions=("communication_fit", "learning_interaction"),
        ),
        "praise_recognition": _section("source_profiles"),
        "conscious_adjustments": _section("compensation_areas", "source_profiles", "recommended_actions"),
        "conflict_cycle": _section("avoid_patterns", dimensions=("conflict_pattern",)),
        "not_personal": _section("avoid_patterns", dimensions=("autonomy_balance", "emotional_attunement")),
    }


def fact_matches_section(
    fact: Mapping[str, Any], *, section_key: str, version: str, contract: SectionContract, family: str
) -> bool:
    if (
        version == CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION
        and section_key == "conscious_adjustments"
        and family == "recommended_actions"
    ):
        return fact.get("topic") == "transitions"
    if version == CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION and "source_kind" in fact:
        kind, dimension = fact.get("source_kind"), fact.get("dimension")
        if section_key == "parent_style":
            return kind == "parent_style"
        if section_key == "parent_strengths":
            return kind == "parent_style" and float(fact["score"]) >= 65 and float(fact["confidence"]) >= 0.4
        if section_key == "child_interaction_needs":
            return kind == "child_needs" and dimension in {"reassurance", "exploration", "personal_space", "variety"}
        if section_key == "praise_recognition":
            return kind == "child_needs" and dimension == "recognition"
        if section_key == "conscious_adjustments":
            return (kind == "interaction" and 35 < float(fact["score"]) < 65) or (
                kind == "child_needs" and dimension == "transition_time"
            )
        topic_dimensions = {
            "soothing_support": "physical_sensory_calm",
            "boundaries_rules": "predictability",
            "autonomy": "autonomy",
            "explanation_learning": "verbal_explanation",
        }
        if section_key in topic_dimensions:
            return kind == "child_needs" and dimension == topic_dimensions[section_key]
        return False
    return (
        not (contract.owned_topics or contract.owned_dimensions)
        or fact.get("topic") in contract.owned_topics
        or fact.get("dimension") in contract.owned_dimensions
    )


_PROFILE_SOURCES = {
    "parent_style": (
        frozenset(item.value for item in ParentStyleDimension),
        PARENT_STYLE_SCORING_VERSION,
        "child_parent_style_scores",
    ),
    "child_needs": (
        frozenset(item.value for item in ChildNeedDimension),
        CHILD_NEEDS_SCORING_VERSION,
        "child_need_scores",
    ),
    "interaction": (_INTERACTION_DIMENSIONS, INTERACTION_SCORING_VERSION, "child_interaction_scores"),
}


def _profile_values_valid(value: Mapping[str, Any]) -> bool:
    kind = value.get("source_kind")
    if not isinstance(kind, str) or kind not in _PROFILE_SOURCES:
        return False
    dimensions, version, _ = _PROFILE_SOURCES[kind]
    dimension = value.get("dimension")
    return (
        isinstance(dimension, str)
        and dimension in dimensions
        and value.get("scoring_version") == version
        and _valid_number(value.get("score"), minimum=0, maximum=100)
        and _valid_number(value.get("confidence"), minimum=0, maximum=1)
    )


class GuidanceFactsQualityError(ValueError):
    def __init__(self, issues: Sequence[GuidanceQualityIssue]) -> None:
        self.issues = tuple(issues)
        summary = ", ".join(f"{issue.code}@{issue.path}" for issue in self.issues)
        super().__init__(f"Guidance Facts failed bounded quality validation: {summary}")


def _find_forbidden_fields(value: object, *, path: str = "$") -> list[GuidanceQualityIssue]:
    issues: list[GuidanceQualityIssue] = []
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            key = str(raw_key)
            nested_path = f"{path}.{key}"
            if key.lower() in _FORBIDDEN_PAYLOAD_FIELDS:
                issues.append(GuidanceQualityIssue("forbidden_payload_field", nested_path))
            issues.extend(_find_forbidden_fields(nested, path=nested_path))
    elif isinstance(value, list | tuple):
        for index, nested in enumerate(value):
            issues.extend(_find_forbidden_fields(nested, path=f"{path}[{index}]"))
    return issues


def _bounded_string(value: object, *, maximum: int = 128) -> bool:
    return isinstance(value, str) and bool(value) and len(value) <= maximum


def _valid_number(value: object, *, minimum: float, maximum: float) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, int | float)
        and isfinite(float(value))
        and minimum <= float(value) <= maximum
    )


def _valid_string_list(value: object, *, maximum: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) <= maximum
        and all(_bounded_string(item, maximum=200) for item in value)
        and len(value) == len(set(value))
    )


def _fact_schema_is_valid(family: str, fact: Mapping[str, Any]) -> bool:
    if set(fact) != _FACT_FIELDS[family] or not _bounded_string(fact.get("id")):
        return False
    if not _valid_number(fact.get("confidence"), minimum=0, maximum=1):
        return False
    if not _valid_string_list(fact.get("evidence_refs"), maximum=_MAX_EVIDENCE_REFS) or not fact["evidence_refs"]:
        return False
    if family == "source_profiles":
        return (
            _profile_values_valid(fact) and fact["id"] == f"profile:{fact.get('source_kind')}:{fact.get('dimension')}"
        )
    if family in {"strong_matches", "friction_points"}:
        return (
            fact.get("dimension") in _INTERACTION_DIMENSIONS
            and _valid_number(fact.get("score"), minimum=0, maximum=100)
            and fact.get("pattern") in _INTERACTION_PATTERNS
        )
    if family in {"parent_strengths", "compensation_areas"}:
        return (
            _bounded_string(fact.get("topic"), maximum=64)
            and (fact.get("dimension") is None or fact.get("dimension") in _INTERACTION_DIMENSIONS)
            and fact.get("reason_code") in CONTEXT_REASON_CODES
            and fact.get("action_code") in CONTEXT_ACTION_CODES
        )
    if family == "recommended_actions":
        return (
            fact.get("target") == "caregiver"
            and _bounded_string(fact.get("topic"), maximum=64)
            and (fact.get("dimension") is None or fact.get("dimension") in _INTERACTION_DIMENSIONS)
            and _bounded_string(fact.get("applicability"), maximum=64)
            and fact.get("reason_code") in CONTEXT_REASON_CODES
            and fact.get("action_code") in CONTEXT_ACTION_CODES
        )
    return (
        fact.get("target") == "caregiver"
        and (fact.get("dimension") is None or fact.get("dimension") in _INTERACTION_DIMENSIONS)
        and fact.get("pattern_code") in GUIDANCE_AVOID_PATTERN_CODES
    )


def _is_uuid(value: object) -> bool:
    try:
        parsed = UUID(str(value))
    except (TypeError, ValueError):
        return False
    return str(parsed) == value


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


def _versioned_uuid_reference(reference: str, *, prefix: str, version: str) -> bool:
    parts = reference.split(":")
    return len(parts) == 3 and parts[0] == prefix and _is_uuid(parts[1]) and parts[2] == version


def _guidance_payload_hash(payload: Mapping[str, Any]) -> str | None:
    registry = payload.get("evidence_registry")
    if not isinstance(registry, Mapping):
        return None
    context_entries = [
        metadata
        for metadata in registry.values()
        if isinstance(metadata, Mapping) and metadata.get("source_type") == "context_resolution"
    ]
    if len(context_entries) != 1:
        return None
    context = context_entries[0]
    try:
        fields = _ALLOWED_PAYLOAD_FIELDS | (
            {"source_profiles"} if payload.get("contract_version") == CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION else set()
        )
        unhashed_payload = {field: payload[field] for field in fields if field != "evidence_registry"}
        unhashed_payload["evidence_registry"] = {
            reference: metadata
            for reference, metadata in registry.items()
            if isinstance(metadata, Mapping) and metadata.get("source_type") != "guidance_contract"
        }
        unhashed_payload["source_contract"] = {
            "resolver_version": context["resolver_version"],
            "resolver_input_hash": context["input_hash"],
        }
        encoded = json.dumps(unhashed_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    except (KeyError, TypeError, ValueError):
        return None
    return hashlib.sha256(encoded).hexdigest()


def _registry_metadata_is_valid(reference: object, metadata: Mapping[str, Any]) -> bool:
    if not isinstance(reference, str):
        return False
    source_type = metadata.get("source_type")
    if not isinstance(source_type, str):
        return False
    expected_fields = _REGISTRY_FIELDS.get(source_type)
    if expected_fields is None or set(metadata) != set(expected_fields):
        return False
    resolver_source_types = {
        "age_snapshot",
        "context_resolution",
        "interaction_score",
        "child_answers",
        "child_interaction_scores",
        "child_age_snapshots",
    }
    if source_type in resolver_source_types:
        if not _valid_string_list(metadata.get("resolver_entry_ids"), maximum=64):
            return False
        if not _valid_string_list(metadata.get("reason_codes"), maximum=64):
            return False
        if any(reason not in CONTEXT_REASON_CODES for reason in metadata["reason_codes"]):
            return False
    if source_type == "age_snapshot":
        source_id = metadata.get("source_id")
        return (
            _is_uuid(source_id)
            and reference == f"age_snapshot:{source_id}"
            and metadata.get("age_stage") in _AGE_STAGES
            and metadata.get("rules_version") == AGE_RULES_VERSION
        )
    if source_type == "context_resolution":
        input_hash = metadata.get("input_hash")
        return (
            metadata.get("resolver_version") == RESOLVER_VERSION
            and _is_sha256(input_hash)
            and reference == f"context_resolution:{input_hash}"
        )
    if source_type == "guidance_contract":
        input_hash = metadata.get("input_hash")
        return (
            metadata.get("contract_version")
            in (GUIDANCE_FACTS_CONTRACT_VERSION, CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION)
            and _is_sha256(input_hash)
            and reference == f"guidance_contract:{input_hash}"
        )
    if source_type == "source_profile":
        if not _profile_values_valid(metadata):
            return False
        _, version, prefix = _PROFILE_SOURCES[metadata["source_kind"]]
        return _versioned_uuid_reference(reference, prefix=prefix, version=version)
    if source_type == "interaction_score":
        return (
            _versioned_uuid_reference(
                reference,
                prefix="child_interaction_scores",
                version=INTERACTION_SCORING_VERSION,
            )
            and metadata.get("dimension") in _INTERACTION_DIMENSIONS
            and _valid_number(metadata.get("score"), minimum=0, maximum=100)
            and metadata.get("pattern") in _INTERACTION_PATTERNS
            and _valid_number(metadata.get("confidence"), minimum=0, maximum=1)
            and metadata.get("scoring_version") == INTERACTION_SCORING_VERSION
        )
    if source_type == "child_interaction_scores":
        return _versioned_uuid_reference(
            reference,
            prefix="child_interaction_scores",
            version=INTERACTION_SCORING_VERSION,
        )
    if source_type == "child_answers":
        return _versioned_uuid_reference(reference, prefix="child_answers", version=ANSWER_VERSION)
    if source_type == "child_age_snapshots":
        return _versioned_uuid_reference(reference, prefix="child_age_snapshots", version=AGE_RULES_VERSION)
    return False


def _resolver_fact_semantics_are_valid(family: str, fact: Mapping[str, Any], *, age_stage: object) -> bool:
    topic = fact.get("topic")
    dimension = fact.get("dimension")
    action_code = fact.get("action_code")
    reason_code = fact.get("reason_code")
    references = fact.get("evidence_refs")
    if not isinstance(references, list) or any(not isinstance(reference, str) for reference in references):
        return False
    if family == "strong_matches":
        return (
            _valid_number(fact.get("score"), minimum=65, maximum=100)
            and _valid_number(fact.get("confidence"), minimum=0.4, maximum=1)
            and fact.get("pattern") in _INTERACTION_PATTERNS
        )
    if family == "friction_points":
        return (
            _valid_number(fact.get("score"), minimum=0, maximum=35)
            and _valid_number(fact.get("confidence"), minimum=0.4, maximum=1)
            and fact.get("pattern") in _INTERACTION_PATTERNS
        )
    if family == "avoid_patterns":
        dimension = fact.get("dimension")
        return isinstance(dimension, str) and fact.get("pattern_code") == _AVOID_PATTERN_BY_DIMENSION.get(dimension)
    if family not in {"parent_strengths", "compensation_areas", "recommended_actions"}:
        return True
    if not isinstance(action_code, str) or not isinstance(reason_code, str):
        return False
    if family == "parent_strengths":
        return (
            topic == dimension
            and dimension in _INTERACTION_DIMENSIONS
            and action_code == "adult_reuses_working_interaction_pattern"
            and reason_code == "interaction_above_strength_threshold"
            and len(references) == 1
            and references[0].startswith("child_interaction_scores:")
        )
    if family == "compensation_areas":
        return (
            topic == dimension
            and dimension in _INTERACTION_DIMENSIONS
            and action_code == "adult_uses_nonautomatic_supportive_response"
            and reason_code == "friction_requires_conscious_adult_adjustment"
            and len(references) == 1
            and references[0].startswith("child_interaction_scores:")
        )
    if family != "recommended_actions":
        return True
    if action_code in _AGE_ACTION_CONTRACTS.values():
        return (
            age_stage in _AGE_ACTION_CONTRACTS
            and action_code == _AGE_ACTION_CONTRACTS[age_stage]
            and topic == "current_age"
            and dimension is None
            and reason_code == f"age_stage_{str(age_stage).replace('-', '_')}"
            and len(references) == 1
            and references[0].startswith("child_age_snapshots:")
        )
    score_actions = {
        "adult_reuses_working_interaction_pattern": "interaction_above_strength_threshold",
        "adult_slows_down_and_observes_response": "interaction_below_friction_threshold",
        "adult_uses_nonautomatic_supportive_response": "friction_requires_conscious_adult_adjustment",
    }
    if action_code in score_actions:
        return (
            topic == dimension
            and dimension in _INTERACTION_DIMENSIONS
            and reason_code == score_actions[action_code]
            and len(references) == 1
            and references[0].startswith("child_interaction_scores:")
        )
    answer_contract = _ANSWER_ACTION_CONTRACTS.get(action_code)
    if answer_contract is not None:
        expected_topic, expected_dimension, expected_reason = answer_contract
        return (
            (topic, dimension, reason_code) == (expected_topic, expected_dimension, expected_reason)
            and len(references) == 2
            and any(reference.startswith("child_answers:") for reference in references)
            and any(reference.startswith("child_interaction_scores:") for reference in references)
        )
    ambiguity_reasons = {
        "adult_observes_before_choosing_guidance": "selected_observation_missing",
        "adult_tracks_context_before_generalizing": "observed_context_is_variable",
        "adult_tests_small_adjustment_and_observes": "evidence_not_directionally_conclusive",
    }
    if action_code not in ambiguity_reasons or (topic, dimension) not in _ANSWER_TOPIC_DIMENSIONS:
        return False
    if action_code == "adult_observes_before_choosing_guidance":
        return (
            reason_code == ambiguity_reasons[action_code]
            and len(references) == 1
            and references[0].startswith("context_resolution:")
        )
    return (
        reason_code == ambiguity_reasons[action_code]
        and len(references) == 2
        and any(reference.startswith("child_answers:") for reference in references)
        and any(reference.startswith("child_interaction_scores:") for reference in references)
    )


def _evidence_supports_fact(family: str, fact: Mapping[str, Any], metadata: Mapping[str, Any]) -> bool:
    source_type = metadata.get("source_type")
    if family == "source_profiles":
        if fact.get("source_kind") == "interaction":
            return source_type == "interaction_score" and all(
                metadata.get(key) == fact.get(key) for key in ("dimension", "score", "confidence", "scoring_version")
            )
        return source_type == "source_profile" and all(
            metadata.get(key) == fact.get(key)
            for key in ("source_kind", "dimension", "score", "confidence", "scoring_version")
        )
    if family in {"strong_matches", "friction_points"}:
        return (
            source_type == "interaction_score"
            and metadata.get("dimension") == fact.get("dimension")
            and metadata.get("score") == fact.get("score")
            and metadata.get("pattern") == fact.get("pattern")
            and metadata.get("confidence") == fact.get("confidence")
        )
    fact_id = str(fact["id"])
    entry_id = fact_id.split(":", 1)[1] if ":" in fact_id else ""
    resolver_entry_ids = metadata.get("resolver_entry_ids")
    reason_codes = metadata.get("reason_codes")
    if not isinstance(resolver_entry_ids, list) or entry_id not in resolver_entry_ids:
        return False
    if family != "avoid_patterns" and (
        not isinstance(reason_codes, list) or fact.get("reason_code") not in reason_codes
    ):
        return False
    if family == "avoid_patterns":
        return source_type == "interaction_score" and metadata.get("dimension") == fact.get("dimension")
    return source_type in {
        "age_snapshot",
        "context_resolution",
        "interaction_score",
        "child_answers",
        "child_interaction_scores",
        "child_age_snapshots",
    }


def validate_guidance_facts(facts: ChildGuidanceFacts | Mapping[str, Any]) -> None:
    payload = facts.to_payload() if isinstance(facts, ChildGuidanceFacts) else dict(facts)
    issues = _find_forbidden_fields(payload)
    version = payload.get("contract_version")
    allowed_fields = _ALLOWED_PAYLOAD_FIELDS | (
        {"source_profiles"} if version == CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION else set()
    )
    payload_fields = {field for field in payload if isinstance(field, str)}
    for field in payload:
        if not isinstance(field, str):
            issues.append(GuidanceQualityIssue("unexpected_payload_field", f"$.{field!r}"))
    for field in sorted(payload_fields - allowed_fields):
        if field.lower() not in _FORBIDDEN_PAYLOAD_FIELDS:
            issues.append(GuidanceQualityIssue("unexpected_payload_field", f"$.{field}"))
    for field in sorted(allowed_fields - payload_fields):
        issues.append(GuidanceQualityIssue("missing_payload_field", f"$.{field}"))

    if version not in (GUIDANCE_FACTS_CONTRACT_VERSION, CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION):
        issues.append(GuidanceQualityIssue("invalid_contract_version", "$.contract_version"))
    for field in ("parent_profile_id", "child_id", "age_snapshot_id"):
        try:
            UUID(str(payload.get(field)))
        except (TypeError, ValueError):
            issues.append(GuidanceQualityIssue("invalid_identity", f"$.{field}"))
    core_report_version = payload.get("core_report_version")
    if isinstance(core_report_version, bool) or not isinstance(core_report_version, int) or core_report_version < 1:
        issues.append(GuidanceQualityIssue("invalid_core_report_version", "$.core_report_version"))

    registry = payload.get("evidence_registry")
    known_registry: Mapping[str, Any] = registry if isinstance(registry, Mapping) else {}
    if not isinstance(registry, Mapping) or not 1 <= len(registry) <= _MAX_REGISTRY_ENTRIES:
        issues.append(GuidanceQualityIssue("invalid_evidence_registry", "$.evidence_registry"))
    source_types: set[str] = set()
    registry_by_type: dict[str, list[Mapping[str, Any]]] = {}
    for reference, metadata in known_registry.items():
        path = f"$.evidence_registry.{reference}"
        if (
            not _bounded_string(reference, maximum=240)
            or not isinstance(metadata, Mapping)
            or not _registry_metadata_is_valid(reference, metadata)
        ):
            issues.append(GuidanceQualityIssue("invalid_evidence_metadata", path))
            continue
        source_type = str(metadata["source_type"])
        if source_type == "source_profile" and version != CURRENT_GUIDANCE_FACTS_CONTRACT_VERSION:
            issues.append(GuidanceQualityIssue("invalid_evidence_metadata", path))
        if source_type == "guidance_contract" and metadata.get("contract_version") != version:
            issues.append(GuidanceQualityIssue("invalid_evidence_metadata", path))
        source_types.add(source_type)
        registry_by_type.setdefault(source_type, []).append(metadata)
    if not {"age_snapshot", "context_resolution", "guidance_contract"} <= source_types:
        issues.append(GuidanceQualityIssue("incomplete_guidance_facts", "$.evidence_registry"))
    for source_type in ("age_snapshot", "context_resolution", "guidance_contract"):
        if len(registry_by_type.get(source_type, ())) != 1:
            issues.append(GuidanceQualityIssue("incomplete_guidance_facts", "$.evidence_registry"))
    age_entries = registry_by_type.get("age_snapshot", ())
    authoritative_age_stage = age_entries[0].get("age_stage") if age_entries else None
    if age_entries and str(age_entries[0].get("source_id")) != str(payload.get("age_snapshot_id")):
        issues.append(GuidanceQualityIssue("invalid_evidence_metadata", "$.evidence_registry"))
    if isinstance(facts, ChildGuidanceFacts) and age_entries:
        if age_entries[0].get("age_stage") != facts.age_stage or str(age_entries[0].get("source_id")) != str(
            facts.age_snapshot_id
        ):
            issues.append(GuidanceQualityIssue("invalid_evidence_metadata", "$.evidence_registry"))
        guidance_entries = registry_by_type.get("guidance_contract", ())
        if guidance_entries and guidance_entries[0].get("input_hash") != facts.input_hash:
            issues.append(GuidanceQualityIssue("invalid_evidence_metadata", "$.evidence_registry"))
    computed_guidance_hash = _guidance_payload_hash(payload)
    guidance_entries = registry_by_type.get("guidance_contract", ())
    if (
        computed_guidance_hash is None
        or not guidance_entries
        or guidance_entries[0].get("input_hash") != computed_guidance_hash
        or (isinstance(facts, ChildGuidanceFacts) and facts.input_hash != computed_guidance_hash)
    ):
        issues.append(GuidanceQualityIssue("invalid_guidance_hash", "$.evidence_registry"))

    markers = payload.get("confidence_markers")
    marked_ids: set[str] = set()
    if isinstance(markers, list):
        marked_ids = {
            fact_id
            for marker in markers
            if isinstance(marker, Mapping) and isinstance((fact_id := marker.get("fact_id")), str)
        }
    else:
        issues.append(GuidanceQualityIssue("invalid_confidence_markers", "$.confidence_markers"))

    fact_ids: set[str] = set()
    for family in fact_families(str(version)):
        facts_in_family = payload.get(family)
        if not isinstance(facts_in_family, list) or len(facts_in_family) > _MAX_FACTS_PER_FAMILY:
            issues.append(GuidanceQualityIssue("invalid_fact_family", f"$.{family}"))
            continue
        for index, fact in enumerate(facts_in_family):
            path = f"$.{family}[{index}]"
            if not isinstance(fact, Mapping) or not _bounded_string(fact.get("id")):
                issues.append(GuidanceQualityIssue("invalid_fact_schema", path))
                continue
            if not _fact_schema_is_valid(family, fact):
                issues.append(GuidanceQualityIssue("invalid_fact_schema", path))
            if not _resolver_fact_semantics_are_valid(family, fact, age_stage=authoritative_age_stage):
                issues.append(GuidanceQualityIssue("invalid_resolver_semantics", path))
            fact_id = str(fact["id"])
            if fact_id in fact_ids:
                issues.append(GuidanceQualityIssue("duplicate_fact_id", path))
            fact_ids.add(fact_id)
            confidence = fact.get("confidence")
            if (
                not isinstance(confidence, bool)
                and isinstance(confidence, int | float)
                and isfinite(float(confidence))
                and 0 <= float(confidence) < LOW_CONFIDENCE_THRESHOLD
                and fact_id not in marked_ids
            ):
                issues.append(GuidanceQualityIssue("missing_low_confidence_marker", path))
            refs = fact.get("evidence_refs")
            if not isinstance(refs, list):
                refs = []
            for reference in refs:
                if not isinstance(reference, str):
                    issues.append(GuidanceQualityIssue("invalid_fact_schema", f"{path}.evidence_refs"))
                    continue
                metadata = known_registry.get(reference)
                if not isinstance(metadata, Mapping):
                    issues.append(GuidanceQualityIssue("unknown_evidence_reference", f"{path}.evidence_refs"))
                elif not _evidence_supports_fact(family, fact, metadata):
                    issues.append(GuidanceQualityIssue("irrelevant_fact_evidence", f"{path}.evidence_refs"))
            if family == "recommended_actions":
                if fact.get("action_code") not in CONTEXT_ACTION_CODES:
                    issues.append(GuidanceQualityIssue("unknown_action_code", f"{path}.action_code"))
                if fact.get("reason_code") not in CONTEXT_REASON_CODES:
                    issues.append(GuidanceQualityIssue("unknown_context_rule", f"{path}.reason_code"))

    actions = payload.get("recommended_actions")
    has_age_action = isinstance(actions, list) and any(
        isinstance(action, Mapping)
        and any(
            isinstance(reference, str)
            and isinstance(known_registry.get(reference), Mapping)
            and known_registry[reference].get("source_type") in {"age_snapshot", "child_age_snapshots"}
            for reference in action.get("evidence_refs", ())
        )
        for action in actions
    )
    if not has_age_action:
        issues.append(GuidanceQualityIssue("incomplete_guidance_facts", "$.recommended_actions"))

    if isinstance(markers, list):
        seen_markers: set[str] = set()
        for index, marker in enumerate(markers):
            path = f"$.confidence_markers[{index}]"
            if (
                not isinstance(marker, Mapping)
                or set(marker) != {"fact_id", "level", "required_language"}
                or not isinstance(marker.get("fact_id"), str)
                or marker["fact_id"] not in fact_ids
                or marker["fact_id"] in seen_markers
                or marker.get("level") != "low"
                or marker.get("required_language") != "conditional"
            ):
                issues.append(GuidanceQualityIssue("invalid_confidence_marker", path))
            elif isinstance(marker.get("fact_id"), str):
                seen_markers.add(marker["fact_id"])

    if issues:
        raise GuidanceFactsQualityError(tuple(dict.fromkeys(issues)))


def guidance_prompt_content(facts: ChildGuidanceFacts) -> dict[str, Any]:
    """Return the sole bounded content object permitted for the S10 prompt pipeline."""

    validate_guidance_facts(facts)
    payload = facts.to_payload()
    registry = payload["evidence_registry"]
    prompt_registry: dict[str, Mapping[str, Any]] = {}
    for reference, metadata in registry.items():
        source_type = metadata.get("source_type")
        if source_type == "guidance_contract":
            continue
        if source_type == "context_resolution":
            prompt_registry[reference] = {key: value for key, value in metadata.items() if key != "input_hash"}
        else:
            prompt_registry[reference] = metadata
    payload["evidence_registry"] = prompt_registry
    return payload
