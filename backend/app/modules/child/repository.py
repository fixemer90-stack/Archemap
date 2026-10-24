"""Persistence boundary for owner-scoped immutable Child Report artifacts."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from math import isfinite
from typing import Any, TypeVar, cast
from uuid import UUID

from sqlalchemy import case, delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.core.models import BaseModel
from app.modules.astrotype_v2.models import (
    NatalChart,
    NatalFact,
    NatalFactEvidence,
    NatalHouse,
    NatalPlanetPosition,
)
from app.modules.child import models
from app.modules.child.age_resolver import AGE_RULES_VERSION, ChildAgeResolution, resolve_child_age
from app.modules.child.birth_data import child_birth_data_hash
from app.modules.child.chart_adapter import ChildChartBuild, ChildChartInput, child_chart_input_hash
from app.modules.child.child_needs import build_child_need_rows, score_child_needs
from app.modules.child.interaction import build_interaction_rows, score_interactions
from app.modules.child.interaction_identity import (
    interaction_fact_id,
    interaction_family_id,
    interaction_score_id,
    synastry_evidence_id,
)
from app.modules.child.parent_style import build_parent_style_rows, score_parent_style
from app.modules.child.scoring.types import (
    ChildNeedDimension,
    InteractionDimension,
    InteractionPattern,
    ParentStyleDimension,
)
from app.modules.child.scoring.validation import validate_dimension_breakdown
from app.modules.child.status import (
    AGE_TERMINAL_STATUSES,
    CLAIMABLE_STATUSES,
    FULL_ACTIVE_STATUSES,
    FULL_TERMINAL_STATUSES,
    ChildGenerationEventCode,
    ChildGenerationOperation,
    ChildGenerationStatus,
    require_transition,
    terminal_failure_status,
)
from app.modules.child.synastry import _rule_for_pair, build_synastry_evidence
from app.modules.profiles.models import PersonProfile
from app.reference_data.child.child_needs_v1 import (
    CHILD_NEEDS_POLICY,
    CHILD_NEEDS_REFERENCE_VERSION,
    CHILD_NEEDS_RULES,
    CHILD_NEEDS_SCALES,
    CHILD_NEEDS_SCORING_VERSION,
)
from app.reference_data.child.interaction_v1 import (
    ANGLE_BODIES,
    ASPECT_CATALOG,
    CORRELATION_FAMILY_CAP,
    EXPECTED_INDEPENDENT_FAMILIES,
    FIT_RULES,
    HOUSE_OVERLAY_DEFINITIONS,
    HOUSE_OVERLAY_WEIGHT,
    INTERACTION_REFERENCE_VERSION,
    INTERACTION_SCORING_VERSION,
    MINIMUM_INDEPENDENT_FAMILIES,
    PERSONAL_BODIES,
    SATURN_DIMENSION_CAP,
    SYNASTRY_REFERENCE_VERSION,
)
from app.reference_data.child.parent_style_v1 import (
    PARENT_STYLE_POLICY,
    PARENT_STYLE_REFERENCE_VERSION,
    PARENT_STYLE_RULES,
    PARENT_STYLE_SCALES,
    PARENT_STYLE_SCORING_VERSION,
)

_ChildModel = TypeVar("_ChildModel", bound=BaseModel)
_PARENT_STYLE_EVIDENCE_KEYS = {
    "factor_key",
    "fact_id",
    "evidence_refs",
    "lineage_refs",
    "correlation_family",
    "factor_value",
    "source_quality",
    "weight",
    "contribution",
    "direction",
}


def _validate_synastry_contract(row: models.ChildSynastryEvidence) -> None:
    payload = row.payload
    if row.source_type in {"cross_chart_aspect", "angle_aspect"}:
        prefix = "cross_aspect" if row.source_type == "cross_chart_aspect" else "angle_aspect"
        parts = row.source_key.split(":")
        if (
            len(parts) != 4
            or parts[0] != prefix
            or not parts[1].startswith("parent_")
            or not parts[2].startswith("child_")
        ):
            raise ChildLineageMismatchError("Synastry aspect source key is invalid")
        parent_body = parts[1].removeprefix("parent_")
        child_body = parts[2].removeprefix("child_")
        aspect_code = parts[3]
        aspect = next((item for item in ASPECT_CATALOG if item.code == aspect_code), None)
        if aspect is None or payload.get("aspect_code") != aspect_code:
            raise ChildLineageMismatchError("Synastry aspect code is invalid")
        if payload.get("parent_body") != parent_body or payload.get("child_body") != child_body:
            raise ChildLineageMismatchError("Synastry aspect pair is invalid")
        if payload.get("allowed_orb_degrees") != aspect.orb or not _is_finite_number(
            payload.get("orb_degrees"), minimum=0.0, maximum=aspect.orb
        ):
            raise ChildLineageMismatchError("Synastry aspect orb is invalid")
        expected_strength = round(1.0 - float(payload["orb_degrees"]) / aspect.orb, 6)
        if not _numbers_close(payload.get("strength"), expected_strength, tolerance=1e-6):
            raise ChildLineageMismatchError("Synastry aspect strength is invalid")
        if row.source_type == "cross_chart_aspect":
            rule = _rule_for_pair(parent_body, child_body)
            if rule is None:
                raise ChildLineageMismatchError("Synastry aspect pair is not allowed")
            expected = round(
                aspect.direction * min(rule.weight * expected_strength, 0.08 if rule.saturn_bounded else 1.0),
                6,
            )
            if (
                payload.get("correlation_family") != rule.signal_family
                or payload.get("factor_label") != rule.factor_label
                or payload.get("dimensions") != [dimension.value for dimension in rule.dimensions]
            ):
                raise ChildLineageMismatchError("Synastry aspect rule is invalid")
        else:
            if not (
                (parent_body in ANGLE_BODIES and child_body in PERSONAL_BODIES)
                or (parent_body in PERSONAL_BODIES and child_body in ANGLE_BODIES)
            ):
                raise ChildLineageMismatchError("Synastry angle pair is not allowed")
            if (
                payload.get("time_reliable_for_overlays") is not True
                or payload.get("factor_label") != "angle_contact_context"
                or payload.get("dimensions")
                != [InteractionDimension.COMMUNICATION_FIT.value, InteractionDimension.AUTONOMY_BALANCE.value]
            ):
                raise ChildLineageMismatchError("Synastry angle timing is invalid")
            angle = parent_body if parent_body in ANGLE_BODIES else child_body
            body = child_body if parent_body in ANGLE_BODIES else parent_body
            if payload.get("correlation_family") != f"angle:{angle}-{body}":
                raise ChildLineageMismatchError("Synastry angle family is invalid")
            expected = round(aspect.direction * 0.06 * expected_strength, 6)
        if not _numbers_close(row.contribution, expected, tolerance=1e-6):
            raise ChildLineageMismatchError("Synastry aspect contribution is invalid")
        if (
            payload.get("parent_source_ref") != f"astrotype_v2_natal_planet_positions:key:{parent_body}"
            or payload.get("child_source_ref") != f"child_chart_versions:key:planet_positions:{child_body}"
        ):
            raise ChildLineageMismatchError("Synastry aspect source refs are invalid")
        return

    parts = row.source_key.split(":")
    if (
        len(parts) != 4
        or parts[0] != "house_overlay"
        or parts[1]
        not in {
            "child_in_parent",
            "parent_in_child",
        }
    ):
        raise ChildLineageMismatchError("Synastry overlay source key is invalid")
    try:
        house_number = int(parts[3].removeprefix("house_"))
    except ValueError as exc:
        raise ChildLineageMismatchError("Synastry overlay house is invalid") from exc
    definition = next((item for item in HOUSE_OVERLAY_DEFINITIONS if item.house_number == house_number), None)
    if (
        definition is None
        or payload.get("overlay_direction") != parts[1]
        or payload.get("body") != parts[2]
        or payload.get("house_number") != house_number
        or payload.get("time_reliable_for_overlays") is not True
        or payload.get("factor_label") != definition.factor_label
        or payload.get("dimensions") != [dimension.value for dimension in definition.dimensions]
        or parts[2] not in PERSONAL_BODIES
    ):
        raise ChildLineageMismatchError("Synastry overlay contract is invalid")
    expected = round(definition.direction * HOUSE_OVERLAY_WEIGHT, 6)
    if not _numbers_close(row.contribution, expected, tolerance=1e-6):
        raise ChildLineageMismatchError("Synastry overlay contribution is invalid")
    expected_parent_ref = (
        f"astrotype_v2_natal_houses:key:{house_number}"
        if parts[1] == "child_in_parent"
        else f"astrotype_v2_natal_planet_positions:key:{parts[2]}"
    )
    expected_child_ref = (
        f"child_chart_versions:key:planet_positions:{parts[2]}"
        if parts[1] == "child_in_parent"
        else f"child_chart_versions:key:houses:{house_number}"
    )
    if (
        payload.get("correlation_family") != f"overlay:{parts[1]}"
        or payload.get("strength") != 1.0
        or payload.get("parent_source_ref") != expected_parent_ref
        or payload.get("child_source_ref") != expected_child_ref
    ):
        raise ChildLineageMismatchError("Synastry overlay source refs are invalid")


def _expected_fit_families(leaves: Sequence[dict[str, Any]]) -> dict[str, str]:
    fit_leaves = [item for item in leaves if cast(str, item["factor_key"]).startswith("fit:")]
    groups: list[set[int]] = []
    for index, item in enumerate(fit_leaves):
        refs = set(cast(list[str], item["lineage_refs"]))
        overlapping = {
            group_index
            for group_index, group in enumerate(groups)
            if any(set(cast(list[str], fit_leaves[member]["lineage_refs"])) & refs for member in group)
        }
        if not overlapping:
            groups.append({index})
            continue
        merged = {index}
        for group_index in sorted(overlapping, reverse=True):
            merged.update(groups.pop(group_index))
        groups.append(merged)
    expected: dict[str, str] = {}
    for group in groups:
        group_refs = sorted({ref for index in group for ref in cast(list[str], fit_leaves[index]["lineage_refs"])})
        family = f"fit:lineage:{interaction_family_id(group_refs)}"
        for index in group:
            expected[cast(str, fit_leaves[index]["factor_key"])] = family
    return expected


def _is_finite_number(value: object, *, minimum: float, maximum: float) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and isfinite(float(value))
        and minimum <= float(value) <= maximum
    )


def _is_nonnegative_int(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _is_unique_string_list(value: object, *, allow_empty: bool) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value))
    )


def _numbers_close(value: object, expected: float, *, tolerance: float) -> bool:
    return (
        _is_finite_number(value, minimum=-1.0, maximum=100.0)
        and abs(float(cast(int | float, value)) - expected) <= tolerance
    )


def _valid_parent_style_evidence(value: object, *, direction: str) -> bool:
    if not isinstance(value, dict) or not value.keys() >= _PARENT_STYLE_EVIDENCE_KEYS:
        return False
    if not all(isinstance(value[key], str) and value[key] for key in ("factor_key", "fact_id", "correlation_family")):
        return False
    try:
        UUID(value["fact_id"])
    except (TypeError, ValueError, AttributeError):
        return False
    if not _is_unique_string_list(value["evidence_refs"], allow_empty=False) or not _is_unique_string_list(
        value["lineage_refs"], allow_empty=False
    ):
        return False
    if not _is_finite_number(value["factor_value"], minimum=0.0, maximum=1.0):
        return False
    if not _is_finite_number(value["source_quality"], minimum=0.0, maximum=1.0):
        return False
    if not _is_finite_number(value["weight"], minimum=-1.0, maximum=1.0):
        return False
    if not _is_finite_number(value["contribution"], minimum=-1.0, maximum=1.0):
        return False
    contribution = float(value["contribution"])
    factor_value = float(value["factor_value"])
    weight = float(value["weight"])
    if contribution != 0.0 and (factor_value == 0.0 or weight == 0.0):
        return False
    return value["direction"] == direction and (contribution >= 0 if direction == "supports" else contribution < 0)


@dataclass(frozen=True, slots=True)
class _ParentStyleBreakdownSemantics:
    evidence_refs: tuple[str, ...]
    score: float
    confidence: float


def _validated_parent_style_breakdown(
    breakdown: object,
    *,
    dimension: ParentStyleDimension,
) -> _ParentStyleBreakdownSemantics | None:
    if not isinstance(breakdown, dict):
        return None
    required_keys = {
        "reference_version",
        "scale",
        "supports",
        "counters",
        "missing_families",
        "confidence_components",
        "raw_delta",
        "independent_family_count",
        "required_family_count",
        "independent_lineage_count",
        "independent_lineage_refs",
        "required_lineage_count",
        "expected_family_count",
        "correlation_family_totals",
        "excluded_time_sensitive_refs",
    }
    if not required_keys <= breakdown.keys() or breakdown["reference_version"] != PARENT_STYLE_REFERENCE_VERSION:
        return None
    expected_scale = PARENT_STYLE_SCALES[dimension]
    if breakdown["scale"] != {
        "zero": expected_scale.zero,
        "hundred": expected_scale.hundred,
        "neutral": expected_scale.neutral,
    }:
        return None
    supports = breakdown["supports"]
    counters = breakdown["counters"]
    if not isinstance(supports, list) or not all(
        _valid_parent_style_evidence(item, direction="supports") for item in supports
    ):
        return None
    if not isinstance(counters, list) or not all(
        _valid_parent_style_evidence(item, direction="counters") for item in counters
    ):
        return None
    for key in (
        "missing_families",
        "independent_lineage_refs",
        "excluded_time_sensitive_refs",
    ):
        if not _is_unique_string_list(breakdown[key], allow_empty=True):
            return None
    confidence_components = breakdown["confidence_components"]
    if not isinstance(confidence_components, dict) or not all(
        _is_finite_number(confidence_components.get(key), minimum=0.0, maximum=1.0)
        for key in ("coverage", "agreement", "source_quality")
    ):
        return None
    if not _is_finite_number(breakdown["raw_delta"], minimum=-1.0, maximum=1.0):
        return None
    count_keys = (
        "independent_family_count",
        "required_family_count",
        "independent_lineage_count",
        "required_lineage_count",
        "expected_family_count",
    )
    if not all(_is_nonnegative_int(breakdown[key]) for key in count_keys):
        return None
    if (
        breakdown["required_family_count"] != PARENT_STYLE_POLICY.minimum_independent_families
        or breakdown["required_lineage_count"] != PARENT_STYLE_POLICY.minimum_independent_families
        or breakdown["expected_family_count"] != PARENT_STYLE_POLICY.expected_independent_families
    ):
        return None

    evidence_items = cast(list[dict[str, Any]], [*supports, *counters])
    evidence_refs = tuple(sorted({ref for item in evidence_items for ref in cast(list[str], item["evidence_refs"])}))
    active_items = [item for item in evidence_items if float(item["contribution"]) != 0.0]
    active_families = {cast(str, item["correlation_family"]) for item in active_items}
    active_lineage_refs = tuple(sorted({ref for item in active_items for ref in cast(list[str], item["lineage_refs"])}))
    family_contributions: dict[str, float] = defaultdict(float)
    for item in active_items:
        family_contributions[cast(str, item["correlation_family"])] += float(item["contribution"])

    totals = breakdown["correlation_family_totals"]
    if not isinstance(totals, list):
        return None
    persisted_family_totals: dict[str, float] = {}
    for total in totals:
        if (
            not isinstance(total, dict)
            or not isinstance(total.get("family"), str)
            or not total["family"]
            or not _is_finite_number(total.get("contribution"), minimum=-1.0, maximum=1.0)
        ):
            return None
        family = cast(str, total["family"])
        if family in persisted_family_totals:
            return None
        persisted_family_totals[family] = float(total["contribution"])

    independent_family_count = cast(int, breakdown["independent_family_count"])
    independent_lineage_count = cast(int, breakdown["independent_lineage_count"])
    independent_lineage_refs = cast(list[str], breakdown["independent_lineage_refs"])
    if (
        independent_family_count != len(active_families)
        or independent_lineage_count != len(active_lineage_refs)
        or independent_lineage_refs != list(active_lineage_refs)
        or set(persisted_family_totals) != active_families
        or any(
            not _numbers_close(
                persisted_family_totals[family],
                round(contribution, 6),
                tolerance=1e-6,
            )
            for family, contribution in family_contributions.items()
        )
    ):
        return None

    expected_families = {rule.signal_family for rule in PARENT_STYLE_RULES if rule.dimension is dimension}
    if breakdown["missing_families"] != sorted(expected_families - active_families):
        return None

    contribution_sum = sum(float(item["contribution"]) for item in evidence_items)
    unrounded_raw_delta = max(-1.0, min(1.0, contribution_sum))
    raw_delta = round(unrounded_raw_delta, 6)
    if not _numbers_close(breakdown["raw_delta"], raw_delta, tolerance=1e-6):
        return None

    positive = sum(float(item["contribution"]) for item in evidence_items if float(item["contribution"]) > 0)
    negative = abs(sum(float(item["contribution"]) for item in evidence_items if float(item["contribution"]) < 0))
    total = positive + negative
    coverage = round(min(1.0, independent_family_count / PARENT_STYLE_POLICY.expected_independent_families), 4)
    if total == 0:
        agreement = 0.0
        source_quality = 0.0
    else:
        agreement = round(max(positive, negative) / total, 4)
        source_quality = round(
            sum(abs(float(item["contribution"])) * float(item["source_quality"]) for item in evidence_items) / total,
            4,
        )
    if any(
        not _numbers_close(confidence_components[key], expected, tolerance=1e-4)
        for key, expected in (
            ("coverage", coverage),
            ("agreement", agreement),
            ("source_quality", source_quality),
        )
    ):
        return None

    enough_evidence = (
        independent_family_count >= PARENT_STYLE_POLICY.minimum_independent_families
        and independent_lineage_count >= PARENT_STYLE_POLICY.minimum_independent_families
    )
    score = round(50.0 + unrounded_raw_delta * 50.0, 2) if enough_evidence else 50.0
    confidence = round(max(0.0, min(1.0, coverage * agreement * source_quality)), 4) if enough_evidence else 0.0
    return _ParentStyleBreakdownSemantics(
        evidence_refs=evidence_refs,
        score=score,
        confidence=confidence,
    )


def _validate_persisted_interaction_profile(
    evidence: Sequence[models.ChildSynastryEvidence],
    scores: Sequence[models.ChildInteractionScore],
    *,
    child_profile_id: UUID,
    generation_id: UUID,
    parent_chart_id: UUID,
    child_chart_version_id: UUID,
    parent_scores: Sequence[models.ChildParentStyleScore] | None = None,
    child_need_scores: Sequence[models.ChildNeedScore] | None = None,
    expected_evidence: Sequence[models.ChildSynastryEvidence] | None = None,
) -> None:
    pair_lineage = {
        "child_profile_id": str(child_profile_id),
        "generation_id": str(generation_id),
        "parent_chart_id": str(parent_chart_id),
        "child_chart_version_id": str(child_chart_version_id),
    }
    source_keys: set[str] = set()
    evidence_ids: set[str] = set()
    evidence_by_key: dict[str, models.ChildSynastryEvidence] = {}
    for row in evidence:
        if (
            row.child_profile_id != child_profile_id
            or row.generation_id != generation_id
            or row.parent_chart_id != parent_chart_id
            or row.child_chart_version_id != child_chart_version_id
        ):
            raise ChildLineageMismatchError("Synastry evidence references another pair lineage")
        if row.reference_version != SYNASTRY_REFERENCE_VERSION or row.source_key in source_keys:
            raise ChildLineageMismatchError("Synastry evidence version or ownership is invalid")
        expected_id = synastry_evidence_id(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            parent_chart_id=parent_chart_id,
            child_chart_version_id=child_chart_version_id,
            reference_version=SYNASTRY_REFERENCE_VERSION,
            source_key=row.source_key,
        )
        if row.id != expected_id:
            raise ChildLineageMismatchError("Synastry evidence identity is invalid")
        if row.source_type not in {"cross_chart_aspect", "angle_aspect", "house_overlay"}:
            raise ChildLineageMismatchError("Synastry evidence source type is invalid")
        if not _is_finite_number(row.contribution, minimum=-1.0, maximum=1.0):
            raise ChildLineageMismatchError("Synastry evidence contains invalid contribution")
        if row.direction != ("supports" if row.contribution >= 0 else "counters"):
            raise ChildLineageMismatchError("Synastry evidence direction is incoherent")
        if not isinstance(row.payload, dict) or row.payload.get("reference_version") != SYNASTRY_REFERENCE_VERSION:
            raise ChildLineageMismatchError("Synastry evidence payload version is invalid")
        if any(row.payload.get(key) != value for key, value in pair_lineage.items()):
            raise ChildLineageMismatchError("Synastry evidence payload pair lineage is invalid")
        dimensions = row.payload.get("dimensions")
        if (
            not isinstance(dimensions, list)
            or not dimensions
            or len(dimensions) != len(set(dimensions))
            or any(value not in {dimension.value for dimension in InteractionDimension} for value in dimensions)
        ):
            raise ChildLineageMismatchError("Synastry evidence dimensions are malformed")
        if not _is_finite_number(row.payload.get("strength"), minimum=0.0, maximum=1.0):
            raise ChildLineageMismatchError("Synastry evidence strength is invalid")
        if not all(
            isinstance(row.payload.get(key), str) and row.payload[key]
            for key in ("correlation_family", "factor_label", "parent_source_ref", "child_source_ref")
        ):
            raise ChildLineageMismatchError("Synastry evidence source lineage is malformed")
        _validate_synastry_contract(row)
        source_keys.add(row.source_key)
        evidence_ids.add(f"child_synastry_evidence:{row.id}")
        evidence_by_key[row.source_key] = row

    expected_dimensions = tuple(dimension.value for dimension in InteractionDimension)
    if tuple(score.dimension for score in scores) != expected_dimensions:
        raise ChildLineageMismatchError("Interaction profile is incomplete or not canonically ordered")
    for score_row in scores:
        if (
            score_row.child_profile_id != child_profile_id
            or score_row.generation_id != generation_id
            or score_row.parent_chart_id != parent_chart_id
            or score_row.child_chart_version_id != child_chart_version_id
        ):
            raise ChildLineageMismatchError("Interaction score references another pair lineage")
        if score_row.scoring_version != INTERACTION_SCORING_VERSION:
            raise ChildLineageMismatchError("Interaction score uses another scoring version")
        dimension = InteractionDimension(score_row.dimension)
        expected_score_id = interaction_score_id(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            parent_chart_id=parent_chart_id,
            child_chart_version_id=child_chart_version_id,
            scoring_version=score_row.scoring_version,
            dimension=dimension.value,
        )
        if score_row.id != expected_score_id:
            raise ChildLineageMismatchError("Interaction score identity is invalid")
        if not _is_finite_number(score_row.score, minimum=0.0, maximum=100.0) or not _is_finite_number(
            score_row.confidence, minimum=0.0, maximum=1.0
        ):
            raise ChildLineageMismatchError("Interaction score contains invalid numeric values")
        if score_row.pattern not in {pattern.value for pattern in InteractionPattern}:
            raise ChildLineageMismatchError("Interaction score contains invalid pattern")
        if not _is_unique_string_list(score_row.evidence_refs, allow_empty=True):
            raise ChildLineageMismatchError("Interaction score contains malformed evidence refs")
        breakdown = score_row.breakdown
        required_keys = {
            "reference_version",
            "parent_style_scoring_version",
            "child_needs_scoring_version",
            "pair_lineage",
            "supports",
            "counters",
            "confidence_components",
            "raw_delta",
            "independent_family_count",
            "required_family_count",
            "independent_lineage_count",
            "independent_lineage_refs",
            "required_lineage_count",
            "expected_family_count",
            "correlation_family_totals",
        }
        if not isinstance(breakdown, dict) or breakdown.keys() != required_keys:
            raise ChildLineageMismatchError("Interaction score contains malformed breakdown")
        if (
            breakdown["reference_version"] != INTERACTION_REFERENCE_VERSION
            or breakdown["parent_style_scoring_version"] != PARENT_STYLE_SCORING_VERSION
            or breakdown["child_needs_scoring_version"] != CHILD_NEEDS_SCORING_VERSION
            or breakdown["pair_lineage"] != pair_lineage
        ):
            raise ChildLineageMismatchError("Interaction breakdown version or lineage is invalid")
        supports = breakdown["supports"]
        counters = breakdown["counters"]
        if not isinstance(supports, list):
            raise ChildLineageMismatchError("Interaction supports are malformed")
        invalid_support = next(
            (item for item in supports if not _valid_parent_style_evidence(item, direction="supports")),
            None,
        )
        if invalid_support is not None:
            factor = invalid_support.get("factor_key") if isinstance(invalid_support, dict) else None
            raise ChildLineageMismatchError(f"Interaction supports are malformed: {factor}")
        if not isinstance(counters, list):
            raise ChildLineageMismatchError("Interaction counters are malformed")
        invalid_counter = next(
            (item for item in counters if not _valid_parent_style_evidence(item, direction="counters")),
            None,
        )
        if invalid_counter is not None:
            factor = invalid_counter.get("factor_key") if isinstance(invalid_counter, dict) else None
            raise ChildLineageMismatchError(f"Interaction counters are malformed: {factor}")
        leaves = cast(list[dict[str, Any]], [*supports, *counters])
        expected_fit_families = _expected_fit_families(leaves)
        for leaf in leaves:
            factor_key = cast(str, leaf["factor_key"])
            expected_fact_id = interaction_fact_id(
                child_profile_id=child_profile_id,
                generation_id=generation_id,
                parent_chart_id=parent_chart_id,
                child_chart_version_id=child_chart_version_id,
                factor_key=factor_key,
                dimension=dimension.value,
            )
            if leaf["fact_id"] != str(expected_fact_id):
                raise ChildLineageMismatchError("Interaction leaf identity is invalid")
            if factor_key.startswith("fit:"):
                matching_fit = [
                    rule
                    for rule in FIT_RULES
                    if rule.dimension is dimension
                    and factor_key == f"fit:{rule.parent_dimension.value}:{rule.child_dimension.value}"
                ]
                if len(matching_fit) != 1 or leaf["correlation_family"] != expected_fit_families.get(factor_key):
                    raise ChildLineageMismatchError("Interaction fit factor is invalid")
            else:
                source = evidence_by_key.get(factor_key)
                if source is None or cast(list[str], leaf["lineage_refs"]) != sorted(
                    [cast(str, source.payload["parent_source_ref"]), cast(str, source.payload["child_source_ref"])]
                ):
                    raise ChildLineageMismatchError("Interaction pair factor is invalid")
        leaf_refs = [ref for item in leaves for ref in cast(list[str], item["evidence_refs"])]
        if len(leaf_refs) != len(set(leaf_refs)):
            raise ChildLineageMismatchError("Interaction evidence ownership is duplicated")
        actual_refs = tuple(sorted(set(leaf_refs)))
        if score_row.evidence_refs != list(actual_refs):
            raise ChildLineageMismatchError("Interaction evidence refs are incoherent")
        if any(ref.startswith("child_synastry_evidence:") and ref not in evidence_ids for ref in actual_refs):
            raise ChildLineageMismatchError("Interaction score references foreign synastry evidence")
        active = [item for item in leaves if float(item["contribution"]) != 0.0]
        families = {cast(str, item["correlation_family"]) for item in active}
        lineages = tuple(sorted({ref for item in active for ref in cast(list[str], item["lineage_refs"])}))
        totals: dict[str, float] = defaultdict(float)
        for item in active:
            totals[cast(str, item["correlation_family"])] += float(item["contribution"])
        if any(
            abs(total) > (SATURN_DIMENSION_CAP if family == "pair:saturn-pressure" else CORRELATION_FAMILY_CAP) + 1e-9
            for family, total in totals.items()
        ):
            raise ChildLineageMismatchError("Interaction correlated evidence exceeds its cap")
        persisted_totals = breakdown["correlation_family_totals"]
        if not isinstance(persisted_totals, list):
            raise ChildLineageMismatchError("Interaction family totals are malformed")
        total_map: dict[str, float] = {}
        for item in persisted_totals:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("family"), str)
                or not _is_finite_number(item.get("contribution"), minimum=-1.0, maximum=1.0)
                or item["family"] in total_map
            ):
                raise ChildLineageMismatchError("Interaction family totals are malformed")
            total_map[cast(str, item["family"])] = float(item["contribution"])
        if set(total_map) != families or any(
            not _numbers_close(total_map[family], round(total, 6), tolerance=1e-6) for family, total in totals.items()
        ):
            raise ChildLineageMismatchError("Interaction family totals are incoherent")
        if (
            breakdown["independent_family_count"] != len(families)
            or breakdown["required_family_count"] != MINIMUM_INDEPENDENT_FAMILIES
            or breakdown["independent_lineage_count"] != len(lineages)
            or breakdown["independent_lineage_refs"] != list(lineages)
            or breakdown["required_lineage_count"] != MINIMUM_INDEPENDENT_FAMILIES
            or breakdown["expected_family_count"] != EXPECTED_INDEPENDENT_FAMILIES
        ):
            raise ChildLineageMismatchError("Interaction evidence counts are incoherent")
        raw_delta = max(-1.0, min(1.0, sum(float(item["contribution"]) for item in leaves)))
        if not _numbers_close(breakdown["raw_delta"], round(raw_delta, 6), tolerance=1e-6):
            raise ChildLineageMismatchError("Interaction raw delta is incoherent")
        positive = sum(float(item["contribution"]) for item in leaves if float(item["contribution"]) > 0)
        negative = abs(sum(float(item["contribution"]) for item in leaves if float(item["contribution"]) < 0))
        magnitude = positive + negative
        coverage = round(min(1.0, len(families) / EXPECTED_INDEPENDENT_FAMILIES), 4)
        agreement = round(max(positive, negative) / magnitude, 4) if magnitude else 0.0
        source_quality = (
            round(
                sum(abs(float(item["contribution"])) * float(item["source_quality"]) for item in leaves) / magnitude,
                4,
            )
            if magnitude
            else 0.0
        )
        components = breakdown["confidence_components"]
        if not isinstance(components, dict) or any(
            not _numbers_close(components.get(key), expected, tolerance=1e-4)
            for key, expected in (
                ("coverage", coverage),
                ("agreement", agreement),
                ("source_quality", source_quality),
            )
        ):
            raise ChildLineageMismatchError("Interaction confidence components are incoherent")
        has_fit_signal = any(family.startswith("fit:") for family in families)
        enough = (
            has_fit_signal
            and len(families) >= MINIMUM_INDEPENDENT_FAMILIES
            and len(lineages) >= MINIMUM_INDEPENDENT_FAMILIES
        )
        expected_score = round(50.0 + raw_delta * 50.0, 2) if enough else 50.0
        expected_confidence = round(coverage * agreement * source_quality, 4) if enough else 0.0
        expected_pattern = (
            InteractionPattern.NATURAL_MATCH.value
            if expected_score >= 60.0
            else InteractionPattern.MODERATE_TENSION.value
            if expected_score >= 35.0
            else InteractionPattern.HIGH_ATTENTION.value
        )
        if (
            not _numbers_close(score_row.score, expected_score, tolerance=1e-6)
            or not _numbers_close(score_row.confidence, expected_confidence, tolerance=1e-4)
            or score_row.pattern != expected_pattern
        ):
            raise ChildLineageMismatchError("Interaction score, confidence, or pattern is incoherent")

    supplied = (parent_scores is not None, child_need_scores is not None, expected_evidence is not None)
    if any(supplied) and not all(supplied):
        raise ChildLineageMismatchError("Interaction source validation state is incomplete")
    if all(supplied):
        assert parent_scores is not None
        assert child_need_scores is not None
        assert expected_evidence is not None
        regenerated_scores = build_interaction_rows(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            parent_chart_id=parent_chart_id,
            child_chart_version_id=child_chart_version_id,
            results=score_interactions(
                child_profile_id=child_profile_id,
                generation_id=generation_id,
                parent_chart_id=parent_chart_id,
                child_chart_version_id=child_chart_version_id,
                parent_scores=parent_scores,
                child_need_scores=child_need_scores,
                synastry_evidence=expected_evidence,
            ),
        )
        actual_evidence = tuple(
            (
                row.id,
                row.child_profile_id,
                row.parent_chart_id,
                row.child_chart_version_id,
                row.generation_id,
                row.source_type,
                row.source_key,
                row.reference_version,
                row.contribution,
                row.direction,
                row.payload,
            )
            for row in evidence
        )
        canonical_evidence = tuple(
            (
                row.id,
                row.child_profile_id,
                row.parent_chart_id,
                row.child_chart_version_id,
                row.generation_id,
                row.source_type,
                row.source_key,
                row.reference_version,
                row.contribution,
                row.direction,
                row.payload,
            )
            for row in expected_evidence
        )
        if actual_evidence != canonical_evidence:
            raise ChildLineageMismatchError("Persisted synastry evidence differs from pinned chart source state")
        actual_scores = tuple(
            (
                row.id,
                row.child_profile_id,
                row.parent_chart_id,
                row.child_chart_version_id,
                row.generation_id,
                row.dimension,
                row.score,
                row.confidence,
                row.pattern,
                row.scoring_version,
                row.evidence_refs,
                row.breakdown,
            )
            for row in scores
        )
        canonical_scores = tuple(
            (
                row.id,
                row.child_profile_id,
                row.parent_chart_id,
                row.child_chart_version_id,
                row.generation_id,
                row.dimension,
                row.score,
                row.confidence,
                row.pattern,
                row.scoring_version,
                row.evidence_refs,
                row.breakdown,
            )
            for row in regenerated_scores
        )
        if actual_scores != canonical_scores:
            raise ChildLineageMismatchError("Persisted interaction scores differ from current upstream source rows")


def _server_now(now: datetime | None) -> datetime:
    effective_now = datetime.now(UTC) if now is None else now
    if not isinstance(effective_now, datetime) or effective_now.tzinfo is None or effective_now.utcoffset() is None:
        raise ValueError("now must be a timezone-aware datetime")
    return effective_now


class ChildIdempotencyTargetMismatchError(ValueError):
    """An idempotency key was reused for a different child target."""


class ChildLineageMismatchError(ValueError):
    """Referenced owner, child, chart, session, report, or snapshot lineage does not match."""


@dataclass(frozen=True)
class ChildProfileCreateResult:
    child: models.ChildProfile
    created: bool


@dataclass(frozen=True)
class ChildChartVersionCreateResult:
    chart: models.ChildChartVersion
    created: bool


@dataclass(frozen=True)
class ChildGenerationLineage:
    parent_chart_id: UUID
    child_chart_version_id: UUID
    questionnaire_session_id: UUID
    age_snapshot_id: UUID


@dataclass(frozen=True)
class ChildGenerationCreateResult:
    generation: models.ChildGeneration
    created: bool


@dataclass(frozen=True)
class ChildGenerationClaim:
    generation: models.ChildGeneration
    claim_token: UUID


@dataclass(frozen=True)
class ChildGenerationReconcileResult:
    requeued_generation_ids: tuple[UUID, ...]
    terminal_generation_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class ChildReportCreateResult:
    report: models.ChildReport
    created: bool


@dataclass(frozen=True)
class ChildReportAssemblyCreateResult:
    assembly: models.ChildReportAssembly
    created: bool


@dataclass(frozen=True)
class ChildAgeGuidanceCreateResult:
    guidance: models.ChildReportAgeGuidance
    created: bool


@dataclass(frozen=True)
class ChildAgeSnapshotCreateResult:
    snapshot: models.ChildAgeSnapshot
    created: bool


@dataclass(frozen=True)
class ParentStyleProfilePersistenceResult:
    scores: tuple[models.ChildParentStyleScore, ...]
    created: bool


@dataclass(frozen=True)
class PersistedParentStyleProfile:
    child_profile_id: UUID
    generation_id: UUID
    parent_chart_id: UUID
    scoring_version: str
    scores: tuple[models.ChildParentStyleScore, ...]


@dataclass(frozen=True)
class ChildNeedProfilePersistenceResult:
    scores: tuple[models.ChildNeedScore, ...]
    created: bool


@dataclass(frozen=True)
class PersistedChildNeedProfile:
    child_profile_id: UUID
    generation_id: UUID
    child_chart_version_id: UUID
    scoring_version: str
    scores: tuple[models.ChildNeedScore, ...]


@dataclass(frozen=True)
class InteractionProfilePersistenceResult:
    evidence: tuple[models.ChildSynastryEvidence, ...]
    scores: tuple[models.ChildInteractionScore, ...]
    created: bool


@dataclass(frozen=True)
class PersistedInteractionProfile:
    child_profile_id: UUID
    generation_id: UUID
    parent_chart_id: UUID
    child_chart_version_id: UUID
    scoring_version: str
    evidence: tuple[models.ChildSynastryEvidence, ...]
    scores: tuple[models.ChildInteractionScore, ...]


@dataclass(frozen=True)
class _InteractionSourceSnapshot:
    generation: models.ChildGeneration
    parent_scores: tuple[models.ChildParentStyleScore, ...]
    child_scores: tuple[models.ChildNeedScore, ...]
    expected_evidence: tuple[models.ChildSynastryEvidence, ...]


@dataclass(frozen=True)
class ChildAgeUpdateResult:
    snapshot: models.ChildAgeSnapshot
    guidance: models.ChildReportAgeGuidance
    snapshot_created: bool
    guidance_created: bool


@dataclass(frozen=True)
class PinnedChildAgeGuidance:
    report: models.ChildReport
    age_snapshot: models.ChildAgeSnapshot
    guidance: models.ChildReportAgeGuidance

    @property
    def core_report_version(self) -> int:
        return self.report.version


@dataclass(frozen=True)
class ChildReportGraph:
    child: models.ChildProfile
    child_chart: models.ChildChartVersion
    generation: models.ChildGeneration
    report: models.ChildReport
    age_snapshots: tuple[models.ChildAgeSnapshot, ...]
    parent_style_scores: tuple[models.ChildParentStyleScore, ...]
    child_need_scores: tuple[models.ChildNeedScore, ...]
    synastry_evidence: tuple[models.ChildSynastryEvidence, ...]
    interaction_scores: tuple[models.ChildInteractionScore, ...]
    questionnaires: tuple[models.ChildQuestionnaireSession, ...]
    answers: tuple[models.ChildAnswer, ...]
    context_resolutions: tuple[models.ChildContextResolution, ...]
    guidance_facts: tuple[models.ChildGuidanceFacts, ...]
    segment_generations: tuple[models.ChildSegmentGeneration, ...]
    age_guidance: tuple[models.ChildReportAgeGuidance, ...]


class ChildRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def record_generation_event(
        self,
        *,
        generation_id: UUID,
        event_code: ChildGenerationEventCode,
        status_from: str | None,
        status_to: str | None,
        attempt_number: int,
        occurred_at: datetime,
        error_code: str | None = None,
        task_correlation: str | None = None,
    ) -> models.ChildGenerationEvent:
        if attempt_number < 0:
            raise ValueError("generation event attempt is invalid")
        for status in (status_from, status_to):
            if status is not None:
                ChildGenerationStatus(status)
        if error_code is not None and (len(error_code) > 80 or not error_code.replace("_", "").isalnum()):
            raise ValueError("generation event error code is unsafe")
        if task_correlation is not None and len(task_correlation) > 120:
            raise ValueError("generation task correlation is unsafe")
        event = models.ChildGenerationEvent(
            generation_id=generation_id,
            event_code=event_code.value,
            status_from=status_from,
            status_to=status_to,
            attempt_number=attempt_number,
            error_code=error_code,
            task_correlation=task_correlation,
            occurred_at=_server_now(occurred_at),
        )
        self.session.add(event)
        return event

    async def _lock_child_lineage(self, child_profile_id: UUID) -> None:
        """Serialize mutable child inputs and derived immutable lineage on one key."""

        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"child-lineage:{child_profile_id}"},
        )

    async def add(self, instance: _ChildModel) -> _ChildModel:
        self.session.add(instance)
        return instance

    async def add_many(self, instances: Sequence[_ChildModel]) -> Sequence[_ChildModel]:
        self.session.add_all(list(instances))
        return instances

    async def flush(self) -> None:
        await self.session.flush()

    async def _require_owned_child(
        self,
        *,
        child_profile_id: UUID,
        owner_user_id: UUID,
        fresh: bool = False,
    ) -> models.ChildProfile:
        statement = select(models.ChildProfile).where(
            models.ChildProfile.id == child_profile_id,
            models.ChildProfile.owner_user_id == owner_user_id,
        )
        if fresh:
            statement = statement.execution_options(populate_existing=True)
        child = await self.session.scalar(statement)
        if child is None:
            raise ChildLineageMismatchError("Child profile is not owned by the requested owner")
        return child

    async def _require_parent_profile_owner(self, *, parent_profile_id: UUID, owner_user_id: UUID) -> None:
        profile_id = await self.session.scalar(
            select(PersonProfile.id).where(
                PersonProfile.id == parent_profile_id,
                PersonProfile.user_id == owner_user_id,
            )
        )
        if profile_id is None:
            raise ChildLineageMismatchError("Parent profile is not owned by the requested owner")

    async def _require_parent_chart_owner(
        self,
        *,
        parent_chart_id: UUID,
        parent_profile_id: UUID,
        owner_user_id: UUID,
    ) -> None:
        chart_id = await self.session.scalar(
            select(NatalChart.id).where(
                NatalChart.id == parent_chart_id,
                NatalChart.profile_id == parent_profile_id,
                NatalChart.user_id == owner_user_id,
            )
        )
        if chart_id is None:
            raise ChildLineageMismatchError("Parent chart does not match the owner and parent profile")

    async def _require_child_chart(
        self,
        *,
        child_chart_version_id: UUID,
        child_profile_id: UUID,
    ) -> None:
        chart_id = await self.session.scalar(
            select(models.ChildChartVersion.id).where(
                models.ChildChartVersion.id == child_chart_version_id,
                models.ChildChartVersion.child_profile_id == child_profile_id,
            )
        )
        if chart_id is None:
            raise ChildLineageMismatchError("Child chart version does not belong to the child")

    async def get_child_by_idempotency_key(
        self,
        *,
        owner_user_id: UUID,
        idempotency_key: str,
    ) -> models.ChildProfile | None:
        result = await self.session.execute(
            select(models.ChildProfile).where(
                models.ChildProfile.owner_user_id == owner_user_id,
                models.ChildProfile.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def create_child_idempotently(
        self,
        *,
        owner_user_id: UUID,
        parent_profile_id: UUID,
        display_name: str,
        relationship_type: str,
        child_gender: str | None,
        birth_date: date,
        birth_time: time | None,
        birth_time_confidence: str,
        birth_place: str,
        latitude: float,
        longitude: float,
        timezone: str,
        caregiver_context: dict[str, Any],
        birth_data_hash: str,
        idempotency_key: str,
    ) -> ChildProfileCreateResult:
        await self._require_parent_profile_owner(
            parent_profile_id=parent_profile_id,
            owner_user_id=owner_user_id,
        )
        statement = (
            pg_insert(models.ChildProfile)
            .values(
                id=uuid.uuid4(),
                owner_user_id=owner_user_id,
                parent_profile_id=parent_profile_id,
                display_name=display_name,
                relationship_type=relationship_type,
                child_gender=child_gender,
                birth_date=birth_date,
                birth_time=birth_time,
                birth_time_confidence=birth_time_confidence,
                birth_place=birth_place,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
                caregiver_context=caregiver_context,
                birth_data_hash=birth_data_hash,
                idempotency_key=idempotency_key,
                status="active",
                version=1,
            )
            .on_conflict_do_nothing(constraint="uq_child_profiles_owner_idempotency")
            .returning(models.ChildProfile)
        )
        inserted = (await self.session.execute(statement)).scalar_one_or_none()
        if inserted is not None:
            return ChildProfileCreateResult(child=inserted, created=True)

        existing = await self.get_child_by_idempotency_key(
            owner_user_id=owner_user_id,
            idempotency_key=idempotency_key,
        )
        if existing is None:
            raise RuntimeError("Child profile conflict could not be read back")
        if (existing.parent_profile_id, existing.birth_data_hash) != (parent_profile_id, birth_data_hash):
            raise ChildIdempotencyTargetMismatchError("Idempotency key already used for another child target")
        return ChildProfileCreateResult(child=existing, created=False)

    async def resolve_current_generation_lineage(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        questionnaire_session_id: UUID,
    ) -> ChildGenerationLineage:
        """Resolve a coherent server-owned current lineage without trusting chart identifiers."""

        child = await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
            fresh=True,
        )
        if child.status != "active":
            raise ChildLineageMismatchError("Child resource is unavailable")
        questionnaire = await self.session.scalar(
            select(models.ChildQuestionnaireSession).where(
                models.ChildQuestionnaireSession.id == questionnaire_session_id,
                models.ChildQuestionnaireSession.child_profile_id == child_profile_id,
                models.ChildQuestionnaireSession.owner_user_id == owner_user_id,
                models.ChildQuestionnaireSession.status == "completed",
            )
        )
        if questionnaire is None:
            raise ChildLineageMismatchError("Generation questionnaire is unavailable")
        current_age_snapshot_id = await self.session.scalar(
            select(models.ChildAgeSnapshot.id)
            .where(models.ChildAgeSnapshot.child_profile_id == child_profile_id)
            .order_by(
                models.ChildAgeSnapshot.as_of_date.desc(),
                models.ChildAgeSnapshot.created_at.desc(),
                models.ChildAgeSnapshot.id.desc(),
            )
            .limit(1)
        )
        if current_age_snapshot_id is None or questionnaire.age_snapshot_id != current_age_snapshot_id:
            raise ChildLineageMismatchError("Generation questionnaire age snapshot is stale")
        parent_chart_id = await self.session.scalar(
            select(NatalChart.id)
            .where(
                NatalChart.profile_id == child.parent_profile_id,
                NatalChart.user_id == owner_user_id,
            )
            .order_by(NatalChart.created_at.desc(), NatalChart.id.desc())
            .limit(1)
        )
        child_chart = await self.session.scalar(
            select(models.ChildChartVersion)
            .where(models.ChildChartVersion.child_profile_id == child_profile_id)
            .order_by(models.ChildChartVersion.version.desc(), models.ChildChartVersion.id.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        if parent_chart_id is None or child_chart is None:
            raise ChildLineageMismatchError("Current chart lineage is unavailable")
        if child_chart.birth_time_confidence != child.birth_time_confidence:
            raise ChildLineageMismatchError("Current child chart confidence is stale")
        return ChildGenerationLineage(
            parent_chart_id=parent_chart_id,
            child_chart_version_id=child_chart.id,
            questionnaire_session_id=questionnaire.id,
            age_snapshot_id=questionnaire.age_snapshot_id,
        )

    async def create_generation_idempotently(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        parent_chart_id: UUID,
        child_chart_version_id: UUID,
        operation: str,
        idempotency_key: str,
        questionnaire_session_id: UUID | None = None,
        source_report_id: UUID | None = None,
        operation_payload: dict[str, Any] | None = None,
    ) -> ChildGenerationCreateResult:
        child = await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        if child.status != "active":
            raise ChildLineageMismatchError("Child resource is unavailable")
        await self._require_parent_chart_owner(
            parent_chart_id=parent_chart_id,
            parent_profile_id=child.parent_profile_id,
            owner_user_id=owner_user_id,
        )
        await self._require_child_chart(
            child_chart_version_id=child_chart_version_id,
            child_profile_id=child_profile_id,
        )
        if questionnaire_session_id is not None:
            questionnaire = await self.session.scalar(
                select(models.ChildQuestionnaireSession).where(
                    models.ChildQuestionnaireSession.id == questionnaire_session_id,
                    models.ChildQuestionnaireSession.child_profile_id == child_profile_id,
                    models.ChildQuestionnaireSession.owner_user_id == owner_user_id,
                    models.ChildQuestionnaireSession.status == "completed",
                )
            )
            if questionnaire is None:
                raise ChildLineageMismatchError("Generation questionnaire is unavailable")
        if source_report_id is not None:
            source_child_id = await self.session.scalar(
                select(models.ChildReport.child_profile_id).where(models.ChildReport.id == source_report_id)
            )
            if source_child_id != child_profile_id:
                raise ChildLineageMismatchError("Source report does not belong to the child")

        statement = (
            pg_insert(models.ChildGeneration)
            .values(
                id=uuid.uuid4(),
                child_profile_id=child_profile_id,
                owner_user_id=owner_user_id,
                parent_chart_id=parent_chart_id,
                child_chart_version_id=child_chart_version_id,
                questionnaire_session_id=questionnaire_session_id,
                generation_id=uuid.uuid4(),
                operation=operation,
                idempotency_key=idempotency_key,
                status=(
                    ChildGenerationStatus.AGE_UPDATE_QUEUED.value
                    if operation == ChildGenerationOperation.AGE_UPDATE.value
                    else (
                        ChildGenerationStatus.NARRATIVE_RETRY_WAITING.value
                        if operation == ChildGenerationOperation.NARRATIVE_RETRY.value
                        else ChildGenerationStatus.QUEUED.value
                    )
                ),
                report_id=(source_report_id if operation == ChildGenerationOperation.NARRATIVE_RETRY.value else None),
                source_report_id=source_report_id,
                operation_payload=operation_payload or {},
                diagnostics={},
            )
            .on_conflict_do_nothing(constraint="uq_child_generations_owner_operation_idempotency")
            .returning(models.ChildGeneration)
        )
        inserted = (await self.session.execute(statement)).scalar_one_or_none()
        if inserted is not None:
            self.record_generation_event(
                generation_id=inserted.generation_id,
                event_code=ChildGenerationEventCode.ACCEPTED,
                status_from=None,
                status_to=inserted.status,
                attempt_number=0,
                occurred_at=datetime.now(UTC),
            )
            return ChildGenerationCreateResult(generation=inserted, created=True)

        existing = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.owner_user_id == owner_user_id,
                models.ChildGeneration.operation == operation,
                models.ChildGeneration.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise RuntimeError("Generation conflict could not be read back")
        target = (
            existing.child_profile_id,
            existing.parent_chart_id,
            existing.child_chart_version_id,
            existing.questionnaire_session_id,
            existing.source_report_id,
            existing.operation_payload,
        )
        expected = (
            child_profile_id,
            parent_chart_id,
            child_chart_version_id,
            questionnaire_session_id,
            source_report_id,
            operation_payload or {},
        )
        if target != expected:
            raise ChildIdempotencyTargetMismatchError("Generation idempotency key was reused for another target")
        return ChildGenerationCreateResult(generation=existing, created=False)

    async def claim_generation_dispatch(
        self,
        *,
        generation_id: UUID,
        now: datetime,
        lease_duration: timedelta,
    ) -> str | None:
        current = _server_now(now)
        task_id = f"child-generation-{generation_id}"
        claimed = (
            await self.session.execute(
                update(models.ChildGeneration)
                .where(
                    models.ChildGeneration.generation_id == generation_id,
                    models.ChildGeneration.status.in_([status.value for status in CLAIMABLE_STATUSES]),
                    (models.ChildGeneration.next_retry_at.is_(None))
                    | (models.ChildGeneration.next_retry_at <= current),
                    (models.ChildGeneration.celery_task_id.is_(None))
                    | (models.ChildGeneration.dispatch_expires_at.is_(None))
                    | (models.ChildGeneration.dispatch_expires_at < current),
                )
                .values(
                    celery_task_id=task_id,
                    dispatched_at=current,
                    dispatch_expires_at=current + lease_duration,
                )
                .returning(models.ChildGeneration)
            )
        ).scalar_one_or_none()
        if claimed is None:
            return None
        self.record_generation_event(
            generation_id=claimed.generation_id,
            event_code=ChildGenerationEventCode.DISPATCH_CLAIMED,
            status_from=claimed.status,
            status_to=claimed.status,
            attempt_number=claimed.attempt_count,
            occurred_at=current,
            task_correlation=task_id,
        )
        return task_id

    async def record_generation_dispatch_outcome(
        self,
        *,
        generation_id: UUID,
        task_id: str,
        succeeded: bool,
        now: datetime,
    ) -> None:
        current = _server_now(now)
        generation = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.generation_id == generation_id,
                models.ChildGeneration.celery_task_id == task_id,
            )
        )
        if generation is None:
            raise ChildLineageMismatchError("Generation dispatch lost its claim")
        if not succeeded:
            generation.celery_task_id = None
            generation.dispatched_at = None
            generation.dispatch_expires_at = None
        self.record_generation_event(
            generation_id=generation_id,
            event_code=(
                ChildGenerationEventCode.DISPATCH_SUCCEEDED if succeeded else ChildGenerationEventCode.DISPATCH_FAILED
            ),
            status_from=generation.status,
            status_to=generation.status,
            attempt_number=generation.attempt_count,
            occurred_at=current,
            error_code=None if succeeded else "broker_dispatch_failed",
            task_correlation=task_id,
        )

    async def claim_generation(
        self,
        *,
        generation_id: UUID,
        task_id: str,
        now: datetime,
        lease_duration: timedelta,
    ) -> ChildGenerationClaim | None:
        """Atomically claim queued work and fence later transitions with a token."""

        current = _server_now(now)
        token = uuid.uuid4()
        claimed = (
            await self.session.execute(
                update(models.ChildGeneration)
                .where(
                    models.ChildGeneration.generation_id == generation_id,
                    models.ChildGeneration.status.in_([status.value for status in CLAIMABLE_STATUSES]),
                    (models.ChildGeneration.next_retry_at.is_(None))
                    | (models.ChildGeneration.next_retry_at <= current),
                )
                .values(
                    status=case(
                        (
                            models.ChildGeneration.operation == ChildGenerationOperation.AGE_UPDATE.value,
                            ChildGenerationStatus.AGE_UPDATE_RUNNING.value,
                        ),
                        (
                            (models.ChildGeneration.operation == ChildGenerationOperation.NARRATIVE_RETRY.value)
                            | (models.ChildGeneration.status == ChildGenerationStatus.NARRATIVE_RETRY_WAITING.value),
                            ChildGenerationStatus.GENERATING_SECTIONS.value,
                        ),
                        else_=ChildGenerationStatus.CALCULATING_PAIR.value,
                    ),
                    celery_task_id=task_id,
                    dispatched_at=None,
                    dispatch_expires_at=None,
                    attempt_count=models.ChildGeneration.attempt_count + 1,
                    claim_token=token,
                    claimed_at=current,
                    heartbeat_at=current,
                    lease_expires_at=current + lease_duration,
                    next_retry_at=None,
                    last_error_code=None,
                )
                .returning(models.ChildGeneration)
            )
        ).scalar_one_or_none()
        if claimed is None:
            return None
        claimed_from = (
            ChildGenerationStatus.AGE_UPDATE_QUEUED.value
            if claimed.operation == ChildGenerationOperation.AGE_UPDATE.value
            else (
                ChildGenerationStatus.NARRATIVE_RETRY_WAITING.value
                if claimed.report_id is not None
                else ChildGenerationStatus.QUEUED.value
            )
        )
        self.record_generation_event(
            generation_id=claimed.generation_id,
            event_code=ChildGenerationEventCode.WORKER_CLAIMED,
            status_from=claimed_from,
            status_to=claimed.status,
            attempt_number=claimed.attempt_count,
            occurred_at=current,
            task_correlation=task_id,
        )
        return ChildGenerationClaim(generation=claimed, claim_token=token)

    async def heartbeat_generation(
        self,
        *,
        generation_id: UUID,
        claim_token: UUID,
        now: datetime,
        lease_duration: timedelta,
    ) -> bool:
        current = _server_now(now)
        updated = await self.session.scalar(
            update(models.ChildGeneration)
            .where(
                models.ChildGeneration.generation_id == generation_id,
                models.ChildGeneration.claim_token == claim_token,
                models.ChildGeneration.status.in_(
                    [status.value for status in FULL_ACTIVE_STATUSES] + [ChildGenerationStatus.AGE_UPDATE_RUNNING.value]
                ),
            )
            .values(heartbeat_at=current, lease_expires_at=current + lease_duration)
            .returning(models.ChildGeneration.generation_id)
        )
        return updated is not None

    async def release_generation_for_retry(
        self,
        *,
        generation_id: UUID,
        claim_token: UUID,
        now: datetime,
        retry_base_seconds: int,
        max_attempts: int,
        error_code: str,
    ) -> models.ChildGeneration:
        current = _server_now(now)
        generation = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.generation_id == generation_id,
                models.ChildGeneration.claim_token == claim_token,
            )
        )
        if generation is None:
            raise ChildLineageMismatchError("Generation retry lost its claim")
        if generation.attempt_count >= max_attempts:
            return await self.fail_claimed_generation(
                generation_id=generation_id,
                claim_token=claim_token,
                now=current,
                error_code="generation_attempts_exhausted",
            )
        status_before = generation.status
        delay = retry_base_seconds * (2 ** max(generation.attempt_count - 1, 0))
        released = (
            await self.session.execute(
                update(models.ChildGeneration)
                .where(
                    models.ChildGeneration.generation_id == generation_id,
                    models.ChildGeneration.claim_token == claim_token,
                )
                .values(
                    status=(
                        ChildGenerationStatus.AGE_UPDATE_QUEUED.value
                        if generation.operation == ChildGenerationOperation.AGE_UPDATE.value
                        else (
                            ChildGenerationStatus.NARRATIVE_RETRY_WAITING.value
                            if generation.report_id is not None or generation.source_report_id is not None
                            else ChildGenerationStatus.QUEUED.value
                        )
                    ),
                    celery_task_id=None,
                    dispatched_at=None,
                    dispatch_expires_at=None,
                    claim_token=None,
                    lease_expires_at=None,
                    heartbeat_at=current,
                    next_retry_at=current + timedelta(seconds=delay),
                    last_error_code=error_code,
                )
                .returning(models.ChildGeneration)
            )
        ).scalar_one_or_none()
        if released is None:
            raise ChildLineageMismatchError("Generation retry lost its claim")
        self.record_generation_event(
            generation_id=released.generation_id,
            event_code=ChildGenerationEventCode.RETRY_RELEASED,
            status_from=status_before,
            status_to=released.status,
            attempt_number=released.attempt_count,
            occurred_at=current,
            error_code=error_code,
            task_correlation=generation.celery_task_id,
        )
        return released

    async def transition_generation(
        self,
        *,
        generation_id: UUID,
        claim_token: UUID,
        expected_status: ChildGenerationStatus,
        target_status: ChildGenerationStatus,
        now: datetime,
        report_id: UUID | None = None,
        error_code: str | None = None,
    ) -> models.ChildGeneration:
        require_transition(expected_status.value, target_status.value)
        current = _server_now(now)
        values: dict[str, Any] = {
            "status": target_status.value,
            "heartbeat_at": current,
            "last_error_code": error_code,
        }
        if report_id is not None:
            values["report_id"] = report_id
        if target_status in FULL_TERMINAL_STATUSES | AGE_TERMINAL_STATUSES:
            values.update(
                finished_at=current,
                claim_token=None,
                lease_expires_at=None,
                next_retry_at=None,
            )
        transitioned = (
            await self.session.execute(
                update(models.ChildGeneration)
                .where(
                    models.ChildGeneration.generation_id == generation_id,
                    models.ChildGeneration.claim_token == claim_token,
                    models.ChildGeneration.status == expected_status.value,
                )
                .values(**values)
                .returning(models.ChildGeneration)
            )
        ).scalar_one_or_none()
        if transitioned is None:
            raise ChildLineageMismatchError("Generation transition lost its claim or expected status")
        self.record_generation_event(
            generation_id=transitioned.generation_id,
            event_code=ChildGenerationEventCode.STATUS_TRANSITIONED,
            status_from=expected_status.value,
            status_to=target_status.value,
            attempt_number=transitioned.attempt_count,
            occurred_at=current,
            error_code=error_code,
            task_correlation=transitioned.celery_task_id,
        )
        return transitioned

    async def fail_claimed_generation(
        self,
        *,
        generation_id: UUID,
        claim_token: UUID,
        now: datetime,
        error_code: str,
    ) -> models.ChildGeneration:
        generation = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.generation_id == generation_id,
                models.ChildGeneration.claim_token == claim_token,
            )
        )
        if generation is None:
            raise ChildLineageMismatchError("Generation failure lost its claim")
        target = (
            ChildGenerationStatus.AGE_UPDATE_FAILED
            if generation.operation == ChildGenerationOperation.AGE_UPDATE.value
            else terminal_failure_status(report_id_present=generation.report_id is not None)
        )
        expected = ChildGenerationStatus(generation.status)
        age_failure_is_valid = (
            target is ChildGenerationStatus.AGE_UPDATE_FAILED and expected is ChildGenerationStatus.AGE_UPDATE_RUNNING
        )
        narrative_failure_is_valid = target is ChildGenerationStatus.NARRATIVE_FAILED and expected in {
            ChildGenerationStatus.DETERMINISTIC_READY,
            ChildGenerationStatus.GENERATING_SECTIONS,
        }
        deterministic_failure_is_valid = target is ChildGenerationStatus.FAILED and expected in {
            ChildGenerationStatus.QUEUED,
            ChildGenerationStatus.CALCULATING_PAIR,
        }
        if not age_failure_is_valid and not narrative_failure_is_valid and not deterministic_failure_is_valid:
            raise ChildLineageMismatchError("Generation failure status is inconsistent with publication state")
        current = _server_now(now)
        failed = (
            await self.session.execute(
                update(models.ChildGeneration)
                .where(
                    models.ChildGeneration.generation_id == generation_id,
                    models.ChildGeneration.claim_token == claim_token,
                    models.ChildGeneration.status == expected.value,
                )
                .values(
                    status=target.value,
                    last_error_code=error_code,
                    finished_at=current,
                    heartbeat_at=current,
                    claim_token=None,
                    lease_expires_at=None,
                    next_retry_at=None,
                )
                .returning(models.ChildGeneration)
            )
        ).scalar_one_or_none()
        if failed is None:
            raise ChildLineageMismatchError("Generation failure lost its claim")
        self.record_generation_event(
            generation_id=failed.generation_id,
            event_code=ChildGenerationEventCode.TERMINAL_FAILED,
            status_from=expected.value,
            status_to=target.value,
            attempt_number=failed.attempt_count,
            occurred_at=current,
            error_code=error_code,
            task_correlation=failed.celery_task_id,
        )
        return failed

    async def allocate_report_version(self, *, child_profile_id: UUID) -> int:
        await self._lock_child_lineage(child_profile_id)
        latest = await self.session.scalar(
            select(func.max(models.ChildReport.version)).where(models.ChildReport.child_profile_id == child_profile_id)
        )
        return int(latest or 0) + 1

    async def list_segment_generations(
        self, *, child_profile_id: UUID, generation_id: UUID
    ) -> tuple[models.ChildSegmentGeneration, ...]:
        rows = (
            await self.session.execute(
                select(models.ChildSegmentGeneration)
                .where(
                    models.ChildSegmentGeneration.child_profile_id == child_profile_id,
                    models.ChildSegmentGeneration.generation_id == generation_id,
                )
                .order_by(models.ChildSegmentGeneration.section_key)
                .execution_options(populate_existing=True)
            )
        ).scalars()
        return tuple(rows.all())

    async def claim_segment_intent(
        self,
        *,
        row: models.ChildSegmentGeneration,
        claim_token: UUID,
    ) -> str:
        if row.status != "in_progress" or row.lifecycle_token != claim_token:
            raise ValueError("segment intent is invalid")
        report_id = await self.session.scalar(
            select(func.coalesce(models.ChildGeneration.source_report_id, models.ChildGeneration.report_id)).where(
                models.ChildGeneration.generation_id == row.generation_id,
                models.ChildGeneration.child_profile_id == row.child_profile_id,
            )
        )
        if report_id is None:
            raise ChildLineageMismatchError("Provider intent has no published source report")
        # The lock is held through the intent INSERT and its checkpoint commit.
        # Every full/retry worker uses the SAME report/section key. The committed
        # in_progress row then remains the fence while no DB lock is held during
        # network I/O, including worker death before terminal persistence.
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"child-provider-section:{report_id}:{row.section_key}"},
        )
        sibling_intent = await self.session.scalar(
            select(models.ChildSegmentGeneration.id)
            .join(
                models.ChildGeneration,
                models.ChildGeneration.generation_id == models.ChildSegmentGeneration.generation_id,
            )
            .where(
                func.coalesce(models.ChildGeneration.source_report_id, models.ChildGeneration.report_id) == report_id,
                models.ChildSegmentGeneration.section_key == row.section_key,
                models.ChildSegmentGeneration.generation_id != row.generation_id,
                (models.ChildSegmentGeneration.status.in_(("in_progress", "ready")))
                | (models.ChildSegmentGeneration.error_code == "child_narrative_provider_outcome_unknown"),
            )
            .limit(1)
        )
        if sibling_intent is not None:
            # Fail closed rather than mutate/reuse another immutable generation.
            # Known rejections remain retryable; known completions cannot be billed
            # again by siblings. Existing lifecycle backoff bounds blocked retries.
            raise ChildLineageMismatchError("Source report section has a fenced provider intent")
        values = {
            "id": row.id or uuid.uuid4(),
            "child_profile_id": row.child_profile_id,
            "generation_id": row.generation_id,
            "section_key": row.section_key,
            "status": row.status,
            "prompt_version": row.prompt_version,
            "model": row.model,
            "content": None,
            "evidence_refs": [],
            "error_code": None,
            "lifecycle_token": claim_token,
            "diagnostics": row.diagnostics,
        }
        inserted = (
            await self.session.execute(
                pg_insert(models.ChildSegmentGeneration)
                .values(**values)
                .on_conflict_do_nothing(constraint="uq_child_segment_generation_section")
                .returning(models.ChildSegmentGeneration.section_key)
            )
        ).scalar_one_or_none()
        if inserted is not None:
            return "claimed"
        existing = await self.session.scalar(
            select(models.ChildSegmentGeneration).where(
                models.ChildSegmentGeneration.generation_id == row.generation_id,
                models.ChildSegmentGeneration.section_key == row.section_key,
            )
        )
        if existing is None:
            raise RuntimeError("Segment intent conflict could not be reloaded")
        if existing.status == "retry_waiting":
            if (
                existing.prompt_version != row.prompt_version
                or existing.model != row.model
                or existing.diagnostics.get("prompt_hash") != row.diagnostics.get("prompt_hash")
                or existing.diagnostics.get("input_hash") != row.diagnostics.get("input_hash")
            ):
                raise ChildLineageMismatchError("Segment retry intent does not match its pinned input")
            existing.status = "in_progress"
            existing.error_code = None
            existing.lifecycle_token = claim_token
            existing.diagnostics = dict(row.diagnostics)
            await self.session.flush()
            return "claimed"
        if existing.status == "in_progress":
            existing.status = "failed"
            existing.error_code = "child_narrative_provider_outcome_unknown"
            existing.lifecycle_token = claim_token
            existing.diagnostics = dict(existing.diagnostics) | {
                "attempts": 1,
                "error_type": "provider_error",
            }
            await self.session.flush()
            return "outcome_unknown"
        return existing.status

    async def mark_segment_retry_waiting(
        self,
        *,
        generation_id: UUID,
        section_key: str,
        claim_token: UUID,
        diagnostics: dict[str, Any],
    ) -> models.ChildSegmentGeneration:
        row = await self.session.scalar(
            update(models.ChildSegmentGeneration)
            .where(
                models.ChildSegmentGeneration.generation_id == generation_id,
                models.ChildSegmentGeneration.section_key == section_key,
                models.ChildSegmentGeneration.status == "in_progress",
                models.ChildSegmentGeneration.lifecycle_token == claim_token,
            )
            .values(
                status="retry_waiting",
                error_code="child_narrative_provider_failure",
                diagnostics=diagnostics,
            )
            .returning(models.ChildSegmentGeneration)
        )
        if row is None:
            raise ChildLineageMismatchError("Segment retry release lost its provider intent")
        return row

    async def finalize_segment_retry_exhausted(
        self,
        *,
        generation_id: UUID,
        section_key: str,
    ) -> models.ChildSegmentGeneration:
        row = await self.session.scalar(
            update(models.ChildSegmentGeneration)
            .where(
                models.ChildSegmentGeneration.generation_id == generation_id,
                models.ChildSegmentGeneration.section_key == section_key,
                models.ChildSegmentGeneration.status == "retry_waiting",
            )
            .values(status="failed", lifecycle_token=None)
            .returning(models.ChildSegmentGeneration)
        )
        if row is None:
            raise ChildLineageMismatchError("Segment retry exhaustion lost its durable intent")
        return row

    async def persist_terminal_segment(
        self,
        *,
        row: models.ChildSegmentGeneration,
        claim_token: UUID | None = None,
    ) -> models.ChildSegmentGeneration:
        if row.status not in {"ready", "not_applicable", "failed"}:
            raise ValueError("segment row is not terminal")
        values = {
            "id": row.id or uuid.uuid4(),
            "child_profile_id": row.child_profile_id,
            "generation_id": row.generation_id,
            "section_key": row.section_key,
            "status": row.status,
            "prompt_version": row.prompt_version,
            "model": row.model,
            "content": row.content,
            "evidence_refs": row.evidence_refs,
            "error_code": row.error_code,
            "lifecycle_token": claim_token,
            "diagnostics": row.diagnostics,
        }
        conflict_where = (
            models.ChildSegmentGeneration.status == "__never_update_terminal__"
            if claim_token is None
            else (
                (models.ChildSegmentGeneration.status == "in_progress")
                & (models.ChildSegmentGeneration.lifecycle_token == claim_token)
            )
        )
        persisted = (
            await self.session.execute(
                pg_insert(models.ChildSegmentGeneration)
                .values(**values)
                .on_conflict_do_update(
                    constraint="uq_child_segment_generation_section",
                    set_={
                        key: value for key, value in values.items() if key not in {"id", "generation_id", "section_key"}
                    },
                    where=conflict_where,
                )
                .returning(models.ChildSegmentGeneration)
            )
        ).scalar_one_or_none()
        if persisted is not None:
            return persisted
        existing = await self.session.scalar(
            select(models.ChildSegmentGeneration).where(
                models.ChildSegmentGeneration.generation_id == row.generation_id,
                models.ChildSegmentGeneration.section_key == row.section_key,
            )
        )
        if existing is None:
            raise RuntimeError("Segment conflict could not be reloaded")
        return existing

    async def reconcile_stuck_generations(
        self,
        *,
        now: datetime,
        max_attempts: int,
        retry_base_seconds: int = 30,
        limit: int = 100,
    ) -> ChildGenerationReconcileResult:
        current = _server_now(now)
        stuck = tuple(
            (
                await self.session.execute(
                    select(models.ChildGeneration)
                    .where(
                        models.ChildGeneration.status.in_(
                            [status.value for status in FULL_ACTIVE_STATUSES]
                            + [ChildGenerationStatus.AGE_UPDATE_RUNNING.value]
                        ),
                        models.ChildGeneration.lease_expires_at.is_not(None),
                        models.ChildGeneration.lease_expires_at < current,
                    )
                    .order_by(models.ChildGeneration.lease_expires_at, models.ChildGeneration.id)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        requeued: list[UUID] = []
        terminal: list[UUID] = []
        for generation in stuck:
            status_before = generation.status
            task_correlation = generation.celery_task_id
            if generation.attempt_count >= max_attempts:
                generation.status = (
                    ChildGenerationStatus.AGE_UPDATE_FAILED.value
                    if generation.operation == ChildGenerationOperation.AGE_UPDATE.value
                    else terminal_failure_status(report_id_present=generation.report_id is not None).value
                )
                generation.finished_at = current
                generation.last_error_code = "generation_attempts_exhausted"
                terminal.append(generation.generation_id)
                event_code = ChildGenerationEventCode.RECONCILIATION_EXHAUSTED
            else:
                generation.status = (
                    ChildGenerationStatus.AGE_UPDATE_QUEUED.value
                    if generation.operation == ChildGenerationOperation.AGE_UPDATE.value
                    else (
                        ChildGenerationStatus.NARRATIVE_RETRY_WAITING.value
                        if generation.report_id is not None or generation.source_report_id is not None
                        else ChildGenerationStatus.QUEUED.value
                    )
                )
                generation.next_retry_at = current + timedelta(
                    seconds=retry_base_seconds * (2 ** max(generation.attempt_count - 1, 0))
                )
                generation.celery_task_id = None
                generation.last_error_code = "stale_generation_requeued"
                requeued.append(generation.generation_id)
                event_code = ChildGenerationEventCode.RECONCILIATION_REQUEUED
            generation.claim_token = None
            generation.lease_expires_at = None
            generation.heartbeat_at = current
            self.record_generation_event(
                generation_id=generation.generation_id,
                event_code=event_code,
                status_from=status_before,
                status_to=generation.status,
                attempt_number=generation.attempt_count,
                occurred_at=current,
                error_code=generation.last_error_code,
                task_correlation=task_correlation,
            )
        await self.session.flush()
        return ChildGenerationReconcileResult(tuple(requeued), tuple(terminal))

    async def create_parent_style_profile(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
    ) -> ParentStyleProfilePersistenceResult:
        """Score and persist one immutable Parent Style profile from v2 fact rows."""

        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"child-parent-style:{generation_id}:{PARENT_STYLE_SCORING_VERSION}"},
        )
        child = await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        generation = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.child_profile_id == child_profile_id,
                models.ChildGeneration.owner_user_id == owner_user_id,
                models.ChildGeneration.generation_id == generation_id,
            )
        )
        if generation is None:
            raise ChildLineageMismatchError("Parent Style generation does not belong to the child")
        await self._require_parent_chart_owner(
            parent_chart_id=generation.parent_chart_id,
            parent_profile_id=child.parent_profile_id,
            owner_user_id=owner_user_id,
        )

        existing = await self._load_parent_style_scores(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        if existing:
            self._validate_parent_style_profile(existing, parent_chart_id=generation.parent_chart_id)
            return ParentStyleProfilePersistenceResult(scores=existing, created=False)

        chart = await self.session.get(NatalChart, generation.parent_chart_id)
        if chart is None:
            raise ChildLineageMismatchError("Parent Style parent chart is missing")
        facts = tuple(
            (
                await self.session.execute(
                    select(NatalFact)
                    .where(NatalFact.chart_id == chart.id)
                    .order_by(NatalFact.fact_type, NatalFact.fact_key, NatalFact.id)
                )
            )
            .scalars()
            .all()
        )
        fact_ids = [fact.id for fact in facts]
        evidence: tuple[NatalFactEvidence, ...] = ()
        if fact_ids:
            evidence = tuple(
                (
                    await self.session.execute(
                        select(NatalFactEvidence)
                        .where(
                            NatalFactEvidence.chart_id == chart.id,
                            NatalFactEvidence.fact_id.in_(fact_ids),
                        )
                        .order_by(
                            NatalFactEvidence.fact_id,
                            NatalFactEvidence.source_table,
                            NatalFactEvidence.source_key,
                            NatalFactEvidence.id,
                        )
                    )
                )
                .scalars()
                .all()
            )
        rows = build_parent_style_rows(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            parent_chart_id=chart.id,
            results=score_parent_style(chart=chart, facts=facts, evidence=evidence),
        )
        self._validate_parent_style_profile(rows, parent_chart_id=chart.id)
        self.session.add_all(list(rows))
        await self.session.flush()
        return ParentStyleProfilePersistenceResult(scores=rows, created=True)

    async def load_parent_style_profile(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
    ) -> PersistedParentStyleProfile:
        """Reload the exact persisted profile without recalculating mutable inputs."""

        await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        generation = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.child_profile_id == child_profile_id,
                models.ChildGeneration.owner_user_id == owner_user_id,
                models.ChildGeneration.generation_id == generation_id,
            )
        )
        if generation is None:
            raise ChildLineageMismatchError("Parent Style generation does not belong to the child")
        scores = await self._load_parent_style_scores(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        self._validate_parent_style_profile(scores, parent_chart_id=generation.parent_chart_id)
        return PersistedParentStyleProfile(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            parent_chart_id=generation.parent_chart_id,
            scoring_version=PARENT_STYLE_SCORING_VERSION,
            scores=scores,
        )

    async def _load_parent_style_scores(
        self,
        *,
        child_profile_id: UUID,
        generation_id: UUID,
    ) -> tuple[models.ChildParentStyleScore, ...]:
        persisted = tuple(
            (
                await self.session.execute(
                    select(models.ChildParentStyleScore)
                    .where(
                        models.ChildParentStyleScore.child_profile_id == child_profile_id,
                        models.ChildParentStyleScore.generation_id == generation_id,
                        models.ChildParentStyleScore.scoring_version == PARENT_STYLE_SCORING_VERSION,
                    )
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        canonical_rank = {dimension.value: index for index, dimension in enumerate(ParentStyleDimension)}
        return tuple(
            sorted(
                persisted,
                key=lambda row: (canonical_rank.get(row.dimension, len(canonical_rank)), row.dimension, str(row.id)),
            )
        )

    @staticmethod
    def _validate_parent_style_profile(
        rows: Sequence[models.ChildParentStyleScore],
        *,
        parent_chart_id: UUID,
    ) -> None:
        expected_dimensions = tuple(dimension.value for dimension in ParentStyleDimension)
        actual_dimensions = tuple(row.dimension for row in rows)
        if actual_dimensions != expected_dimensions:
            raise ChildLineageMismatchError("Parent Style profile is incomplete or not canonically ordered")
        if any(row.parent_chart_id != parent_chart_id for row in rows):
            raise ChildLineageMismatchError("Parent Style profile references another parent chart")
        if any(row.scoring_version != PARENT_STYLE_SCORING_VERSION for row in rows):
            raise ChildLineageMismatchError("Parent Style profile uses another scoring version")
        for row in rows:
            if not isfinite(row.score) or not 0.0 <= row.score <= 100.0:
                raise ChildLineageMismatchError("Parent Style profile contains an invalid score")
            if not isfinite(row.confidence) or not 0.0 <= row.confidence <= 1.0:
                raise ChildLineageMismatchError("Parent Style profile contains invalid confidence")
            if not _is_unique_string_list(row.evidence_refs, allow_empty=True):
                raise ChildLineageMismatchError("Parent Style profile contains malformed evidence refs")
            semantics = _validated_parent_style_breakdown(
                row.breakdown,
                dimension=ParentStyleDimension(row.dimension),
            )
            if semantics is None:
                raise ChildLineageMismatchError("Parent Style profile contains malformed breakdown")
            if row.evidence_refs != list(semantics.evidence_refs):
                raise ChildLineageMismatchError("Parent Style profile contains incoherent evidence refs")
            if not _numbers_close(row.score, semantics.score, tolerance=1e-6):
                raise ChildLineageMismatchError("Parent Style profile contains an incoherent score")
            if not _numbers_close(row.confidence, semantics.confidence, tolerance=1e-4):
                raise ChildLineageMismatchError("Parent Style profile contains incoherent confidence")

    async def create_child_need_profile(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
    ) -> ChildNeedProfilePersistenceResult:
        """Score and persist one immutable Child Needs profile from its pinned chart."""

        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"child-needs:{generation_id}:{CHILD_NEEDS_SCORING_VERSION}"},
        )
        await self._require_owned_child(child_profile_id=child_profile_id, owner_user_id=owner_user_id)
        generation = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.child_profile_id == child_profile_id,
                models.ChildGeneration.owner_user_id == owner_user_id,
                models.ChildGeneration.generation_id == generation_id,
            )
        )
        if generation is None:
            raise ChildLineageMismatchError("Child Needs generation does not belong to the child")
        existing = await self._load_child_need_scores(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        if existing:
            self._validate_child_need_profile(existing, child_chart_version_id=generation.child_chart_version_id)
            return ChildNeedProfilePersistenceResult(scores=existing, created=False)

        chart = await self.session.scalar(
            select(models.ChildChartVersion).where(
                models.ChildChartVersion.id == generation.child_chart_version_id,
                models.ChildChartVersion.child_profile_id == child_profile_id,
            )
        )
        if chart is None:
            raise ChildLineageMismatchError("Child Needs pinned chart is missing or belongs to another child")
        rows = build_child_need_rows(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            child_chart_version_id=chart.id,
            results=score_child_needs(chart=chart),
        )
        self._validate_child_need_profile(rows, child_chart_version_id=chart.id)
        self.session.add_all(list(rows))
        await self.session.flush()
        return ChildNeedProfilePersistenceResult(scores=rows, created=True)

    async def load_child_need_profile(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
    ) -> PersistedChildNeedProfile:
        """Reload the current persisted scoring version without recalculation."""

        await self._require_owned_child(child_profile_id=child_profile_id, owner_user_id=owner_user_id)
        generation = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.child_profile_id == child_profile_id,
                models.ChildGeneration.owner_user_id == owner_user_id,
                models.ChildGeneration.generation_id == generation_id,
            )
        )
        if generation is None:
            raise ChildLineageMismatchError("Child Needs generation does not belong to the child")
        scores = await self._load_child_need_scores(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        self._validate_child_need_profile(scores, child_chart_version_id=generation.child_chart_version_id)
        return PersistedChildNeedProfile(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            child_chart_version_id=generation.child_chart_version_id,
            scoring_version=CHILD_NEEDS_SCORING_VERSION,
            scores=scores,
        )

    async def _load_child_need_scores(
        self,
        *,
        child_profile_id: UUID,
        generation_id: UUID,
    ) -> tuple[models.ChildNeedScore, ...]:
        persisted = tuple(
            (
                await self.session.execute(
                    select(models.ChildNeedScore)
                    .where(
                        models.ChildNeedScore.child_profile_id == child_profile_id,
                        models.ChildNeedScore.generation_id == generation_id,
                        models.ChildNeedScore.scoring_version == CHILD_NEEDS_SCORING_VERSION,
                    )
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        rank = {dimension.value: index for index, dimension in enumerate(ChildNeedDimension)}
        return tuple(
            sorted(persisted, key=lambda row: (rank.get(row.dimension, len(rank)), row.dimension, str(row.id)))
        )

    @staticmethod
    def _validate_child_need_profile(
        rows: Sequence[models.ChildNeedScore],
        *,
        child_chart_version_id: UUID,
    ) -> None:
        expected = tuple(dimension.value for dimension in ChildNeedDimension)
        if tuple(row.dimension for row in rows) != expected:
            raise ChildLineageMismatchError("Child Needs profile is incomplete or not canonically ordered")
        if any(row.child_chart_version_id != child_chart_version_id for row in rows):
            raise ChildLineageMismatchError("Child Needs profile references another child chart")
        if any(row.scoring_version != CHILD_NEEDS_SCORING_VERSION for row in rows):
            raise ChildLineageMismatchError("Child Needs profile uses another scoring version")
        for row in rows:
            if not isfinite(row.score) or not 0.0 <= row.score <= 100.0:
                raise ChildLineageMismatchError("Child Needs profile contains an invalid score")
            if not isfinite(row.confidence) or not 0.0 <= row.confidence <= 1.0:
                raise ChildLineageMismatchError("Child Needs profile contains invalid confidence")
            if not _is_unique_string_list(row.evidence_refs, allow_empty=True):
                raise ChildLineageMismatchError("Child Needs profile contains malformed evidence refs")
            semantics = validate_dimension_breakdown(
                row.breakdown,
                dimension=ChildNeedDimension(row.dimension),
                reference_version=CHILD_NEEDS_REFERENCE_VERSION,
                scales=CHILD_NEEDS_SCALES,
                rules=CHILD_NEEDS_RULES,
                policy=CHILD_NEEDS_POLICY,
            )
            if semantics is None:
                raise ChildLineageMismatchError("Child Needs profile contains malformed breakdown")
            if row.evidence_refs != list(semantics.evidence_refs):
                raise ChildLineageMismatchError("Child Needs profile contains incoherent evidence refs")
            if not _numbers_close(row.score, semantics.score, tolerance=1e-6):
                raise ChildLineageMismatchError("Child Needs profile contains an incoherent score")
            if not _numbers_close(row.confidence, semantics.confidence, tolerance=1e-4):
                raise ChildLineageMismatchError("Child Needs profile contains incoherent confidence")

    async def _lock_interaction_source_snapshot(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
    ) -> _InteractionSourceSnapshot:
        """Lock then authoritatively read one exact interaction source snapshot.

        Create and reload acquire PostgreSQL ``FOR SHARE`` locks in the same
        deterministic table order: owned child route, generation, current Parent
        Style scores, current Child Needs scores, parent chart root, child chart
        root, parent positions (including persisted angles), then parent houses.
        Transaction-scoped locks prevent raw UPDATE/DELETE from changing source
        rows between route authorization, regeneration, and semantic validation
        under READ COMMITTED.
        """

        child = await self.session.scalar(
            select(models.ChildProfile)
            .where(
                models.ChildProfile.id == child_profile_id,
                models.ChildProfile.owner_user_id == owner_user_id,
            )
            .order_by(models.ChildProfile.id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if child is None:
            raise ChildLineageMismatchError("Child profile is not owned by the requested owner")
        parent_profile_id = child.parent_profile_id

        locked_lineage = (
            await self.session.execute(
                select(
                    models.ChildGeneration.id,
                    models.ChildGeneration.parent_chart_id,
                    models.ChildGeneration.child_chart_version_id,
                )
                .where(
                    models.ChildGeneration.child_profile_id == child_profile_id,
                    models.ChildGeneration.owner_user_id == owner_user_id,
                    models.ChildGeneration.generation_id == generation_id,
                )
                .order_by(models.ChildGeneration.id)
                .with_for_update(read=True)
            )
        ).one_or_none()
        if locked_lineage is None:
            raise ChildLineageMismatchError("Interaction generation does not belong to the child")
        generation_row_id, parent_chart_id, child_chart_version_id = locked_lineage

        lock_queries = (
            select(models.ChildParentStyleScore.id)
            .where(
                models.ChildParentStyleScore.child_profile_id == child_profile_id,
                models.ChildParentStyleScore.generation_id == generation_id,
                models.ChildParentStyleScore.scoring_version == PARENT_STYLE_SCORING_VERSION,
            )
            .order_by(models.ChildParentStyleScore.dimension, models.ChildParentStyleScore.id)
            .with_for_update(read=True),
            select(models.ChildNeedScore.id)
            .where(
                models.ChildNeedScore.child_profile_id == child_profile_id,
                models.ChildNeedScore.generation_id == generation_id,
                models.ChildNeedScore.scoring_version == CHILD_NEEDS_SCORING_VERSION,
            )
            .order_by(models.ChildNeedScore.dimension, models.ChildNeedScore.id)
            .with_for_update(read=True),
            select(NatalChart.id)
            .where(
                NatalChart.id == parent_chart_id,
                NatalChart.profile_id == parent_profile_id,
                NatalChart.user_id == owner_user_id,
            )
            .order_by(NatalChart.id)
            .with_for_update(read=True),
            select(models.ChildChartVersion.id)
            .where(
                models.ChildChartVersion.child_profile_id == child_profile_id,
                models.ChildChartVersion.id == child_chart_version_id,
            )
            .order_by(models.ChildChartVersion.id)
            .with_for_update(read=True),
            select(NatalPlanetPosition.id)
            .where(NatalPlanetPosition.chart_id == parent_chart_id)
            .order_by(NatalPlanetPosition.body, NatalPlanetPosition.id)
            .with_for_update(read=True),
            select(NatalHouse.id)
            .where(NatalHouse.chart_id == parent_chart_id)
            .order_by(NatalHouse.house_number, NatalHouse.id)
            .with_for_update(read=True),
        )
        for query in lock_queries:
            await self.session.execute(query)

        generation = await self.session.scalar(
            select(models.ChildGeneration)
            .where(models.ChildGeneration.id == generation_row_id)
            .execution_options(populate_existing=True)
        )
        if generation is None:
            raise ChildLineageMismatchError("Interaction generation does not belong to the child")
        parent_scores = await self._load_parent_style_scores(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        child_scores = await self._load_child_need_scores(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        parent_chart = await self.session.scalar(
            select(NatalChart)
            .where(
                NatalChart.id == parent_chart_id,
                NatalChart.profile_id == parent_profile_id,
                NatalChart.user_id == owner_user_id,
            )
            .execution_options(populate_existing=True)
        )
        child_chart = await self.session.scalar(
            select(models.ChildChartVersion)
            .where(
                models.ChildChartVersion.child_profile_id == child_profile_id,
                models.ChildChartVersion.id == child_chart_version_id,
            )
            .execution_options(populate_existing=True)
        )
        if parent_chart is None or child_chart is None:
            raise ChildLineageMismatchError("Interaction pinned chart lineage is missing")
        parent_positions = tuple(
            (
                await self.session.execute(
                    select(NatalPlanetPosition)
                    .where(NatalPlanetPosition.chart_id == parent_chart_id)
                    .order_by(NatalPlanetPosition.body, NatalPlanetPosition.id)
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        parent_houses = tuple(
            (
                await self.session.execute(
                    select(NatalHouse)
                    .where(NatalHouse.chart_id == parent_chart_id)
                    .order_by(NatalHouse.house_number, NatalHouse.id)
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        self._validate_parent_style_profile(parent_scores, parent_chart_id=parent_chart_id)
        self._validate_child_need_profile(child_scores, child_chart_version_id=child_chart_version_id)
        expected_evidence = build_synastry_evidence(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            parent_chart=parent_chart,
            parent_positions=parent_positions,
            child_chart=child_chart,
            parent_houses=parent_houses,
        )
        return _InteractionSourceSnapshot(
            generation=generation,
            parent_scores=parent_scores,
            child_scores=child_scores,
            expected_evidence=expected_evidence,
        )

    async def create_interaction_profile(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
    ) -> InteractionProfilePersistenceResult:
        """Persist one immutable pair-bound synastry and Interaction profile."""

        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"child-interaction:{generation_id}:{INTERACTION_SCORING_VERSION}"},
        )
        source = await self._lock_interaction_source_snapshot(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        generation = source.generation
        parent_scores = source.parent_scores
        child_scores = source.child_scores
        expected_evidence = source.expected_evidence
        existing_scores = await self._load_interaction_scores(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        existing_evidence = await self._load_synastry_evidence(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        if existing_scores or existing_evidence:
            self._validate_interaction_profile(
                existing_evidence,
                existing_scores,
                child_profile_id=child_profile_id,
                generation_id=generation_id,
                parent_chart_id=generation.parent_chart_id,
                child_chart_version_id=generation.child_chart_version_id,
                parent_scores=parent_scores,
                child_need_scores=child_scores,
                expected_evidence=expected_evidence,
            )
            return InteractionProfilePersistenceResult(
                evidence=existing_evidence,
                scores=existing_scores,
                created=False,
            )

        evidence = expected_evidence
        scores = build_interaction_rows(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            parent_chart_id=generation.parent_chart_id,
            child_chart_version_id=generation.child_chart_version_id,
            results=score_interactions(
                child_profile_id=child_profile_id,
                generation_id=generation_id,
                parent_chart_id=generation.parent_chart_id,
                child_chart_version_id=generation.child_chart_version_id,
                parent_scores=parent_scores,
                child_need_scores=child_scores,
                synastry_evidence=evidence,
            ),
        )
        self._validate_interaction_profile(
            evidence,
            scores,
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            parent_chart_id=generation.parent_chart_id,
            child_chart_version_id=generation.child_chart_version_id,
            parent_scores=parent_scores,
            child_need_scores=child_scores,
            expected_evidence=expected_evidence,
        )
        self.session.add_all([*evidence, *scores])
        await self.session.flush()
        return InteractionProfilePersistenceResult(evidence=evidence, scores=scores, created=True)

    async def load_interaction_profile(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
    ) -> PersistedInteractionProfile:
        """Reload and semantically validate the current pair scoring version."""

        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"child-interaction:{generation_id}:{INTERACTION_SCORING_VERSION}"},
        )
        source = await self._lock_interaction_source_snapshot(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        generation = source.generation
        parent_scores = source.parent_scores
        child_scores = source.child_scores
        expected_evidence = source.expected_evidence
        evidence = await self._load_synastry_evidence(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        scores = await self._load_interaction_scores(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        self._validate_interaction_profile(
            evidence,
            scores,
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            parent_chart_id=generation.parent_chart_id,
            child_chart_version_id=generation.child_chart_version_id,
            parent_scores=parent_scores,
            child_need_scores=child_scores,
            expected_evidence=expected_evidence,
        )
        return PersistedInteractionProfile(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            parent_chart_id=generation.parent_chart_id,
            child_chart_version_id=generation.child_chart_version_id,
            scoring_version=INTERACTION_SCORING_VERSION,
            evidence=evidence,
            scores=scores,
        )

    async def _load_synastry_evidence(
        self, *, child_profile_id: UUID, generation_id: UUID
    ) -> tuple[models.ChildSynastryEvidence, ...]:
        return tuple(
            (
                await self.session.execute(
                    select(models.ChildSynastryEvidence)
                    .where(
                        models.ChildSynastryEvidence.child_profile_id == child_profile_id,
                        models.ChildSynastryEvidence.generation_id == generation_id,
                        models.ChildSynastryEvidence.reference_version == SYNASTRY_REFERENCE_VERSION,
                    )
                    .order_by(models.ChildSynastryEvidence.source_key, models.ChildSynastryEvidence.id)
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )

    async def _load_interaction_scores(
        self, *, child_profile_id: UUID, generation_id: UUID
    ) -> tuple[models.ChildInteractionScore, ...]:
        persisted = tuple(
            (
                await self.session.execute(
                    select(models.ChildInteractionScore)
                    .where(
                        models.ChildInteractionScore.child_profile_id == child_profile_id,
                        models.ChildInteractionScore.generation_id == generation_id,
                        models.ChildInteractionScore.scoring_version == INTERACTION_SCORING_VERSION,
                    )
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        rank = {dimension.value: index for index, dimension in enumerate(InteractionDimension)}
        return tuple(
            sorted(persisted, key=lambda row: (rank.get(row.dimension, len(rank)), row.dimension, str(row.id)))
        )

    @staticmethod
    def _validate_interaction_profile(
        evidence: Sequence[models.ChildSynastryEvidence],
        scores: Sequence[models.ChildInteractionScore],
        *,
        child_profile_id: UUID,
        generation_id: UUID,
        parent_chart_id: UUID,
        child_chart_version_id: UUID,
        parent_scores: Sequence[models.ChildParentStyleScore] | None = None,
        child_need_scores: Sequence[models.ChildNeedScore] | None = None,
        expected_evidence: Sequence[models.ChildSynastryEvidence] | None = None,
    ) -> None:
        _validate_persisted_interaction_profile(
            evidence,
            scores,
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            parent_chart_id=parent_chart_id,
            child_chart_version_id=child_chart_version_id,
            parent_scores=parent_scores,
            child_need_scores=child_need_scores,
            expected_evidence=expected_evidence,
        )

    async def create_chart_version_idempotently(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        chart: ChildChartBuild,
    ) -> ChildChartVersionCreateResult:
        """Append one chart lineage row, serializing version allocation per child."""
        await self._lock_child_lineage(child_profile_id)
        await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
            fresh=True,
        )
        existing = await self.session.scalar(
            select(models.ChildChartVersion).where(
                models.ChildChartVersion.child_profile_id == child_profile_id,
                models.ChildChartVersion.engine_version == chart.engine_version,
                models.ChildChartVersion.input_hash == chart.input_hash,
            )
        )
        if existing is not None:
            return ChildChartVersionCreateResult(chart=existing, created=False)

        latest_version = await self.session.scalar(
            select(func.max(models.ChildChartVersion.version)).where(
                models.ChildChartVersion.child_profile_id == child_profile_id
            )
        )
        statement = (
            pg_insert(models.ChildChartVersion)
            .values(
                id=uuid.uuid4(),
                child_profile_id=child_profile_id,
                version=(latest_version or 0) + 1,
                engine_version=chart.engine_version,
                input_hash=chart.input_hash,
                birth_time_confidence=chart.birth_time_confidence,
                allowed_fact_families=list(chart.allowed_fact_families),
                excluded_fact_families=list(chart.excluded_fact_families),
                uncertainty_reason=chart.uncertainty_reason,
                calculation_payload=chart.calculation_payload,
            )
            .on_conflict_do_nothing(constraint="uq_child_chart_versions_profile_engine_input")
            .returning(models.ChildChartVersion)
        )
        inserted = (await self.session.execute(statement)).scalar_one_or_none()
        if inserted is not None:
            return ChildChartVersionCreateResult(chart=inserted, created=True)

        existing = await self.session.scalar(
            select(models.ChildChartVersion).where(
                models.ChildChartVersion.child_profile_id == child_profile_id,
                models.ChildChartVersion.engine_version == chart.engine_version,
                models.ChildChartVersion.input_hash == chart.input_hash,
            )
        )
        if existing is None:
            raise RuntimeError("Child chart conflict could not be read back")
        return ChildChartVersionCreateResult(chart=existing, created=False)

    async def create_age_snapshot_idempotently(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        now: datetime | None = None,
        age_rules_version: str = AGE_RULES_VERSION,
    ) -> ChildAgeSnapshotCreateResult:
        """Derive and append one immutable age snapshot from server-owned DOB and clock."""

        effective_now = _server_now(now)
        await self._lock_child_lineage(child_profile_id)
        child = await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
            fresh=True,
        )
        resolved = resolve_child_age(
            birth_date=child.birth_date,
            as_of=effective_now,
            timezone_name=child.timezone,
            age_rules_version=age_rules_version,
        )
        existing = await self._get_age_snapshot_by_resolution(
            child_profile_id=child_profile_id,
            resolved=resolved,
        )
        if existing is not None:
            return ChildAgeSnapshotCreateResult(snapshot=existing, created=False)

        statement = (
            pg_insert(models.ChildAgeSnapshot)
            .values(
                id=uuid.uuid4(),
                child_profile_id=child_profile_id,
                as_of_date=resolved.as_of_date,
                age_years=resolved.age_years,
                age_months=resolved.age_months,
                age_days=resolved.age_days,
                age_stage=resolved.age_stage,
                age_rules_version=resolved.age_rules_version,
                input_hash=resolved.input_hash,
            )
            .on_conflict_do_nothing(constraint="uq_child_age_snapshots_profile_date_rules_input")
            .returning(models.ChildAgeSnapshot)
        )
        inserted = (await self.session.execute(statement)).scalar_one_or_none()
        if inserted is not None:
            return ChildAgeSnapshotCreateResult(snapshot=inserted, created=True)
        existing = await self._get_age_snapshot_by_resolution(
            child_profile_id=child_profile_id,
            resolved=resolved,
        )
        if existing is None:
            raise RuntimeError("Child age snapshot conflict could not be read back")
        return ChildAgeSnapshotCreateResult(snapshot=existing, created=False)

    async def _get_age_snapshot_by_resolution(
        self,
        *,
        child_profile_id: UUID,
        resolved: ChildAgeResolution,
    ) -> models.ChildAgeSnapshot | None:
        return cast(
            models.ChildAgeSnapshot | None,
            await self.session.scalar(
                select(models.ChildAgeSnapshot).where(
                    models.ChildAgeSnapshot.child_profile_id == child_profile_id,
                    models.ChildAgeSnapshot.as_of_date == resolved.as_of_date,
                    models.ChildAgeSnapshot.age_rules_version == resolved.age_rules_version,
                    models.ChildAgeSnapshot.input_hash == resolved.input_hash,
                )
            ),
        )

    async def correct_birth_data_and_create_chart(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        birth_date: date,
        birth_time: time | None,
        birth_time_confidence: str,
        birth_place: str,
        latitude: float,
        longitude: float,
        timezone: str,
        house_system: str,
        birth_data_hash: str,
        chart: ChildChartBuild,
    ) -> ChildChartVersionCreateResult:
        """Atomically update current birth data and append, never overwrite, chart lineage."""
        if chart.birth_time_confidence != birth_time_confidence:
            raise ChildLineageMismatchError("Chart confidence does not match corrected birth data")
        if birth_time_confidence == "unknown" and birth_time is not None:
            raise ValueError("Unknown birth time must be omitted")
        if birth_time_confidence != "unknown" and birth_time is None:
            raise ValueError("Exact or approximate birth time is required")

        expected_source_input = ChildChartInput(
            birth_date=birth_date,
            birth_time=birth_time,
            birth_time_confidence=birth_time_confidence,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            house_system=house_system,
        )
        if chart.source_input is None:
            raise ChildLineageMismatchError("Chart correction requires the exact source input")
        if chart.source_input != expected_source_input:
            raise ChildLineageMismatchError("Chart source input does not match corrected birth data")
        expected_input_hash = child_chart_input_hash(chart.source_input, engine_version=chart.engine_version)
        if chart.input_hash != expected_input_hash:
            raise ChildLineageMismatchError("Chart input hash does not match its source input")
        expected_birth_data_hash = child_birth_data_hash(
            birth_date=birth_date,
            birth_time=birth_time,
            birth_time_confidence=birth_time_confidence,
            birth_place=birth_place,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
        )
        if birth_data_hash != expected_birth_data_hash:
            raise ChildLineageMismatchError("Supplied birth-data hash does not match corrected birth data")

        await self._lock_child_lineage(child_profile_id)
        child = await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
            fresh=True,
        )
        current_birth_data_hash = child_birth_data_hash(
            birth_date=child.birth_date,
            birth_time=child.birth_time,
            birth_time_confidence=child.birth_time_confidence,
            birth_place=child.birth_place,
            latitude=child.latitude,
            longitude=child.longitude,
            timezone=child.timezone,
        )
        birth_data_changed = current_birth_data_hash != expected_birth_data_hash
        result = await self.create_chart_version_idempotently(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            chart=chart,
        )
        if birth_data_changed and not result.created:
            raise ChildIdempotencyTargetMismatchError(
                "Corrected birth data must create a new child chart input lineage"
            )

        if birth_data_changed:
            child.birth_date = birth_date
            child.birth_time = birth_time
            child.birth_time_confidence = birth_time_confidence
            child.birth_place = birth_place
            child.latitude = latitude
            child.longitude = longitude
            child.timezone = timezone
            child.birth_data_hash = expected_birth_data_hash
            child.version += 1
            await self.session.flush()
        return result

    async def create_report_idempotently(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
        parent_chart_id: UUID,
        child_chart_version_id: UUID,
        idempotency_key: str,
        version: int,
        status: str,
        scoring_version: str,
        reference_version: str,
        questionnaire_version: str,
        prompt_version: str,
        report_payload: dict[str, Any],
        presentation_manifest: dict[str, Any],
    ) -> ChildReportCreateResult:
        await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        generation = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.generation_id == generation_id,
                models.ChildGeneration.child_profile_id == child_profile_id,
                models.ChildGeneration.owner_user_id == owner_user_id,
            )
        )
        if generation is None or (
            generation.parent_chart_id != parent_chart_id or generation.child_chart_version_id != child_chart_version_id
        ):
            raise ChildLineageMismatchError("Report target does not match generation lineage")

        statement = (
            pg_insert(models.ChildReport)
            .values(
                id=uuid.uuid4(),
                child_profile_id=child_profile_id,
                parent_chart_id=parent_chart_id,
                child_chart_version_id=child_chart_version_id,
                generation_id=generation_id,
                idempotency_key=idempotency_key,
                version=version,
                status=status,
                scoring_version=scoring_version,
                reference_version=reference_version,
                questionnaire_version=questionnaire_version,
                prompt_version=prompt_version,
                report_payload=report_payload,
                presentation_manifest=presentation_manifest,
            )
            .on_conflict_do_nothing()
            .returning(models.ChildReport)
        )
        inserted = (await self.session.execute(statement)).scalar_one_or_none()
        if inserted is not None:
            return ChildReportCreateResult(report=inserted, created=True)

        existing = await self.session.scalar(
            select(models.ChildReport).where(
                models.ChildReport.child_profile_id == child_profile_id,
                models.ChildReport.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise ChildIdempotencyTargetMismatchError("Report generation already produced a different target")
        target = (
            existing.generation_id,
            existing.parent_chart_id,
            existing.child_chart_version_id,
            existing.version,
        )
        expected = (generation_id, parent_chart_id, child_chart_version_id, version)
        if target != expected:
            raise ChildIdempotencyTargetMismatchError("Report idempotency key was reused for another target")
        return ChildReportCreateResult(report=existing, created=False)

    async def create_report_assembly_idempotently(
        self,
        *,
        child_profile_id: UUID,
        generation_id: UUID,
        source_generation_id: UUID,
        report_id: UUID,
        status: str,
        contract_version: str,
        payload: dict[str, Any],
    ) -> ChildReportAssemblyCreateResult:
        if status not in {"ready", "narrative_failed"}:
            raise ValueError("report assembly status is invalid")
        report_lineage = await self.session.scalar(
            select(models.ChildReport.id).where(
                models.ChildReport.id == report_id,
                models.ChildReport.child_profile_id == child_profile_id,
                models.ChildReport.generation_id == source_generation_id,
            )
        )
        artifact_generation = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.child_profile_id == child_profile_id,
                models.ChildGeneration.generation_id == generation_id,
            )
        )
        if report_lineage is None or artifact_generation is None:
            raise ChildLineageMismatchError("Report assembly lineage is invalid")
        if generation_id != source_generation_id and (
            artifact_generation.operation != ChildGenerationOperation.NARRATIVE_RETRY.value
            or artifact_generation.source_report_id != report_id
            or artifact_generation.operation_payload.get("source_generation_id") != str(source_generation_id)
        ):
            raise ChildLineageMismatchError("Retry assembly source lineage is invalid")
        statement = (
            pg_insert(models.ChildReportAssembly)
            .values(
                id=uuid.uuid4(),
                child_profile_id=child_profile_id,
                generation_id=generation_id,
                source_generation_id=source_generation_id,
                report_id=report_id,
                status=status,
                contract_version=contract_version,
                payload=payload,
            )
            .on_conflict_do_nothing(constraint="uq_child_report_assemblies_generation")
            .returning(models.ChildReportAssembly)
        )
        inserted = (await self.session.execute(statement)).scalar_one_or_none()
        if inserted is not None:
            return ChildReportAssemblyCreateResult(assembly=inserted, created=True)
        existing = await self.session.scalar(
            select(models.ChildReportAssembly).where(models.ChildReportAssembly.generation_id == generation_id)
        )
        if existing is None:
            raise RuntimeError("Report assembly conflict could not be reloaded")
        if (
            existing.child_profile_id,
            existing.source_generation_id,
            existing.report_id,
            existing.status,
            existing.contract_version,
            existing.payload,
        ) != (child_profile_id, source_generation_id, report_id, status, contract_version, payload):
            raise ChildIdempotencyTargetMismatchError("Report assembly generation was reused for another payload")
        return ChildReportAssemblyCreateResult(assembly=existing, created=False)

    async def create_age_guidance_idempotently(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        report_id: UUID,
        age_snapshot_id: UUID,
        version: int,
        idempotency_key: str,
        status: str,
        rules_version: str,
        payload: dict[str, Any],
    ) -> ChildAgeGuidanceCreateResult:
        await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        report_child_id = await self.session.scalar(
            select(models.ChildReport.child_profile_id).where(models.ChildReport.id == report_id)
        )
        snapshot_child_id = await self.session.scalar(
            select(models.ChildAgeSnapshot.child_profile_id).where(models.ChildAgeSnapshot.id == age_snapshot_id)
        )
        if report_child_id != child_profile_id or snapshot_child_id != child_profile_id:
            raise ChildLineageMismatchError("Age guidance report or snapshot does not belong to the child")

        statement = (
            pg_insert(models.ChildReportAgeGuidance)
            .values(
                id=uuid.uuid4(),
                child_profile_id=child_profile_id,
                report_id=report_id,
                age_snapshot_id=age_snapshot_id,
                version=version,
                idempotency_key=idempotency_key,
                status=status,
                rules_version=rules_version,
                payload=payload,
            )
            .on_conflict_do_nothing()
            .returning(models.ChildReportAgeGuidance)
        )
        inserted = (await self.session.execute(statement)).scalar_one_or_none()
        if inserted is not None:
            return ChildAgeGuidanceCreateResult(guidance=inserted, created=True)

        existing = await self.session.scalar(
            select(models.ChildReportAgeGuidance).where(
                models.ChildReportAgeGuidance.child_profile_id == child_profile_id,
                models.ChildReportAgeGuidance.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise RuntimeError("Age guidance conflict could not be read back")
        if (
            existing.report_id,
            existing.age_snapshot_id,
            existing.version,
            existing.status,
            existing.rules_version,
            existing.payload,
        ) != (
            report_id,
            age_snapshot_id,
            version,
            status,
            rules_version,
            payload,
        ):
            raise ChildIdempotencyTargetMismatchError("Age guidance key was reused for another target")
        return ChildAgeGuidanceCreateResult(guidance=existing, created=False)

    async def create_age_update_idempotently(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        report_id: UUID,
        idempotency_key: str,
        guidance_rules_version: str,
        payload: dict[str, Any],
        now: datetime | None = None,
        age_rules_version: str = AGE_RULES_VERSION,
        pinned_age_snapshot_id: UUID | None = None,
    ) -> ChildAgeUpdateResult:
        """Append age snapshot/guidance lineage without touching the core report."""

        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"child-age-update-idempotency:{child_profile_id}:{idempotency_key}"},
        )
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"child-age-update:{report_id}"},
        )
        await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        existing = await self.session.scalar(
            select(models.ChildReportAgeGuidance).where(
                models.ChildReportAgeGuidance.child_profile_id == child_profile_id,
                models.ChildReportAgeGuidance.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if (
                existing.report_id,
                existing.rules_version,
                existing.payload,
            ) != (
                report_id,
                guidance_rules_version,
                payload,
            ):
                raise ChildIdempotencyTargetMismatchError("Age update key was reused for another target")
            existing_snapshot = await self.session.scalar(
                select(models.ChildAgeSnapshot).where(
                    models.ChildAgeSnapshot.id == existing.age_snapshot_id,
                    models.ChildAgeSnapshot.child_profile_id == child_profile_id,
                )
            )
            if existing_snapshot is None:
                raise ChildLineageMismatchError("Persisted age update snapshot does not belong to the child")
            return ChildAgeUpdateResult(
                snapshot=existing_snapshot,
                guidance=existing,
                snapshot_created=False,
                guidance_created=False,
            )

        report = await self.session.scalar(
            select(models.ChildReport).where(
                models.ChildReport.id == report_id,
                models.ChildReport.child_profile_id == child_profile_id,
            )
        )
        if report is None:
            raise ChildLineageMismatchError("Age update report does not belong to the child")

        if pinned_age_snapshot_id is None:
            snapshot_result = await self.create_age_snapshot_idempotently(
                owner_user_id=owner_user_id,
                child_profile_id=child_profile_id,
                now=now,
                age_rules_version=age_rules_version,
            )
        else:
            pinned_snapshot = await self.session.scalar(
                select(models.ChildAgeSnapshot).where(
                    models.ChildAgeSnapshot.id == pinned_age_snapshot_id,
                    models.ChildAgeSnapshot.child_profile_id == child_profile_id,
                    models.ChildAgeSnapshot.age_rules_version == age_rules_version,
                )
            )
            if pinned_snapshot is None:
                raise ChildLineageMismatchError("Pinned age snapshot does not belong to the child")
            snapshot_result = ChildAgeSnapshotCreateResult(snapshot=pinned_snapshot, created=False)
        latest_version = await self.session.scalar(
            select(func.max(models.ChildReportAgeGuidance.version)).where(
                models.ChildReportAgeGuidance.report_id == report_id
            )
        )
        guidance_result = await self.create_age_guidance_idempotently(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            report_id=report_id,
            age_snapshot_id=snapshot_result.snapshot.id,
            version=(latest_version or 0) + 1,
            idempotency_key=idempotency_key,
            status="age_update_ready",
            rules_version=guidance_rules_version,
            payload=payload,
        )
        return ChildAgeUpdateResult(
            snapshot=snapshot_result.snapshot,
            guidance=guidance_result.guidance,
            snapshot_created=snapshot_result.created,
            guidance_created=guidance_result.created,
        )

    async def archive_child(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
    ) -> models.ChildProfile:
        archived = (
            await self.session.execute(
                update(models.ChildProfile)
                .where(
                    models.ChildProfile.id == child_profile_id,
                    models.ChildProfile.owner_user_id == owner_user_id,
                    models.ChildProfile.status != "deletion_pending",
                )
                .values(status="archived", archived_at=datetime.now().astimezone())
                .returning(models.ChildProfile)
            )
        ).scalar_one_or_none()
        if archived is None:
            raise ChildLineageMismatchError("Child profile is not owned by the requested owner")
        return archived

    async def purge_child_domain(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
    ) -> None:
        child = await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        child.status = "deletion_pending"
        await self.session.flush()
        await self.session.execute(text("SET LOCAL app.child_purge = 'on'"))
        deleted_id = await self.session.scalar(
            delete(models.ChildProfile)
            .where(
                models.ChildProfile.id == child_profile_id,
                models.ChildProfile.owner_user_id == owner_user_id,
            )
            .returning(models.ChildProfile.id)
        )
        if deleted_id is None:
            raise ChildLineageMismatchError("Child profile is not owned by the requested owner")
        self.session.add(
            AuditLog(
                actor_id=owner_user_id,
                action="child_hard_delete",
                entity_type="child_profile",
                entity_id=str(child_profile_id),
                changes={
                    "event_type": "child_hard_delete",
                    "owner_user_id": str(owner_user_id),
                    "child_profile_id": str(child_profile_id),
                    "result": "deleted",
                },
            )
        )

    async def load_report_graph(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        report_id: UUID,
    ) -> ChildReportGraph:
        child = await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        report = await self.session.scalar(
            select(models.ChildReport).where(
                models.ChildReport.id == report_id,
                models.ChildReport.child_profile_id == child_profile_id,
            )
        )
        if report is None:
            raise ChildLineageMismatchError("Report does not belong to the child")
        generation = await self.session.scalar(
            select(models.ChildGeneration).where(
                models.ChildGeneration.child_profile_id == child_profile_id,
                models.ChildGeneration.generation_id == report.generation_id,
            )
        )
        child_chart = await self.session.scalar(
            select(models.ChildChartVersion).where(
                models.ChildChartVersion.child_profile_id == child_profile_id,
                models.ChildChartVersion.id == report.child_chart_version_id,
            )
        )
        if generation is None or child_chart is None:
            raise ChildLineageMismatchError("Persisted report lineage is incomplete")

        async def rows(model: type[_ChildModel], *criteria: Any) -> tuple[Any, ...]:
            result = await self.session.execute(select(model).where(*criteria))
            return tuple(result.scalars().all())

        questionnaires = cast(
            tuple[models.ChildQuestionnaireSession, ...],
            await rows(
                models.ChildQuestionnaireSession,
                models.ChildQuestionnaireSession.child_profile_id == child_profile_id,
                models.ChildQuestionnaireSession.questionnaire_version == report.questionnaire_version,
            ),
        )
        questionnaire_ids = [questionnaire.id for questionnaire in questionnaires]
        answers: tuple[models.ChildAnswer, ...] = ()
        if questionnaire_ids:
            answers = cast(
                tuple[models.ChildAnswer, ...],
                await rows(
                    models.ChildAnswer,
                    models.ChildAnswer.child_profile_id == child_profile_id,
                    models.ChildAnswer.questionnaire_session_id.in_(questionnaire_ids),
                ),
            )

        return ChildReportGraph(
            child=child,
            child_chart=child_chart,
            generation=generation,
            report=report,
            age_snapshots=cast(
                tuple[models.ChildAgeSnapshot, ...],
                await rows(models.ChildAgeSnapshot, models.ChildAgeSnapshot.child_profile_id == child_profile_id),
            ),
            parent_style_scores=cast(
                tuple[models.ChildParentStyleScore, ...],
                await rows(
                    models.ChildParentStyleScore,
                    models.ChildParentStyleScore.child_profile_id == child_profile_id,
                    models.ChildParentStyleScore.generation_id == report.generation_id,
                ),
            ),
            child_need_scores=cast(
                tuple[models.ChildNeedScore, ...],
                await rows(
                    models.ChildNeedScore,
                    models.ChildNeedScore.child_profile_id == child_profile_id,
                    models.ChildNeedScore.generation_id == report.generation_id,
                ),
            ),
            synastry_evidence=cast(
                tuple[models.ChildSynastryEvidence, ...],
                await rows(
                    models.ChildSynastryEvidence,
                    models.ChildSynastryEvidence.child_profile_id == child_profile_id,
                    models.ChildSynastryEvidence.generation_id == report.generation_id,
                ),
            ),
            interaction_scores=cast(
                tuple[models.ChildInteractionScore, ...],
                await rows(
                    models.ChildInteractionScore,
                    models.ChildInteractionScore.child_profile_id == child_profile_id,
                    models.ChildInteractionScore.generation_id == report.generation_id,
                ),
            ),
            questionnaires=questionnaires,
            answers=answers,
            context_resolutions=cast(
                tuple[models.ChildContextResolution, ...],
                await rows(
                    models.ChildContextResolution,
                    models.ChildContextResolution.child_profile_id == child_profile_id,
                    models.ChildContextResolution.generation_id == report.generation_id,
                ),
            ),
            guidance_facts=cast(
                tuple[models.ChildGuidanceFacts, ...],
                await rows(
                    models.ChildGuidanceFacts,
                    models.ChildGuidanceFacts.child_profile_id == child_profile_id,
                    models.ChildGuidanceFacts.generation_id == report.generation_id,
                ),
            ),
            segment_generations=cast(
                tuple[models.ChildSegmentGeneration, ...],
                await rows(
                    models.ChildSegmentGeneration,
                    models.ChildSegmentGeneration.child_profile_id == child_profile_id,
                    models.ChildSegmentGeneration.generation_id == report.generation_id,
                ),
            ),
            age_guidance=cast(
                tuple[models.ChildReportAgeGuidance, ...],
                await rows(
                    models.ChildReportAgeGuidance,
                    models.ChildReportAgeGuidance.child_profile_id == child_profile_id,
                    models.ChildReportAgeGuidance.report_id == report_id,
                ),
            ),
        )

    async def get_child_for_owner(
        self,
        *,
        child_id: UUID,
        owner_user_id: UUID,
        include_archived: bool = False,
    ) -> models.ChildProfile | None:
        statement = select(models.ChildProfile).where(
            models.ChildProfile.id == child_id,
            models.ChildProfile.owner_user_id == owner_user_id,
        )
        if not include_archived:
            statement = statement.where(models.ChildProfile.status != "archived")
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_children_for_owner(
        self,
        *,
        owner_user_id: UUID,
        include_archived: bool = False,
    ) -> list[models.ChildProfile]:
        statement = select(models.ChildProfile).where(models.ChildProfile.owner_user_id == owner_user_id)
        if not include_archived:
            statement = statement.where(models.ChildProfile.status != "archived")
        result = await self.session.execute(statement.order_by(models.ChildProfile.created_at))
        return list(result.scalars().all())

    async def list_age_snapshots_for_owner(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
    ) -> list[models.ChildAgeSnapshot]:
        result = await self.session.execute(
            select(models.ChildAgeSnapshot)
            .join(models.ChildProfile, models.ChildAgeSnapshot.child_profile_id == models.ChildProfile.id)
            .where(
                models.ChildAgeSnapshot.child_profile_id == child_profile_id,
                models.ChildProfile.owner_user_id == owner_user_id,
            )
            .order_by(models.ChildAgeSnapshot.as_of_date, models.ChildAgeSnapshot.created_at)
        )
        return list(result.scalars().all())

    async def get_age_snapshot_for_owner(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        age_snapshot_id: UUID,
    ) -> models.ChildAgeSnapshot | None:
        return cast(
            models.ChildAgeSnapshot | None,
            await self.session.scalar(
                select(models.ChildAgeSnapshot)
                .join(models.ChildProfile, models.ChildAgeSnapshot.child_profile_id == models.ChildProfile.id)
                .where(
                    models.ChildAgeSnapshot.id == age_snapshot_id,
                    models.ChildAgeSnapshot.child_profile_id == child_profile_id,
                    models.ChildProfile.owner_user_id == owner_user_id,
                )
            ),
        )

    async def get_pinned_age_guidance_for_owner(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        report_id: UUID,
        age_snapshot_id: UUID | None = None,
    ) -> PinnedChildAgeGuidance:
        """Shared persisted selector for web/PDF age-guidance parity."""

        await self._require_owned_child(
            child_profile_id=child_profile_id,
            owner_user_id=owner_user_id,
        )
        report = await self.session.scalar(
            select(models.ChildReport).where(
                models.ChildReport.id == report_id,
                models.ChildReport.child_profile_id == child_profile_id,
            )
        )
        if report is None:
            raise ChildLineageMismatchError("Pinned report does not belong to the child")

        if age_snapshot_id is not None:
            snapshot = await self.session.scalar(
                select(models.ChildAgeSnapshot).where(models.ChildAgeSnapshot.id == age_snapshot_id)
            )
            if snapshot is None or snapshot.child_profile_id != child_profile_id:
                raise ChildLineageMismatchError("Pinned age snapshot does not belong to the child")
            guidance = await self.session.scalar(
                select(models.ChildReportAgeGuidance)
                .where(
                    models.ChildReportAgeGuidance.child_profile_id == child_profile_id,
                    models.ChildReportAgeGuidance.report_id == report_id,
                    models.ChildReportAgeGuidance.age_snapshot_id == age_snapshot_id,
                )
                .order_by(models.ChildReportAgeGuidance.version.desc())
                .limit(1)
            )
        else:
            guidance = await self.session.scalar(
                select(models.ChildReportAgeGuidance)
                .join(
                    models.ChildAgeSnapshot,
                    models.ChildReportAgeGuidance.age_snapshot_id == models.ChildAgeSnapshot.id,
                )
                .where(
                    models.ChildReportAgeGuidance.child_profile_id == child_profile_id,
                    models.ChildReportAgeGuidance.report_id == report_id,
                )
                .order_by(
                    models.ChildAgeSnapshot.as_of_date.desc(),
                    models.ChildReportAgeGuidance.version.desc(),
                )
                .limit(1)
            )
            snapshot = (
                await self.session.get(models.ChildAgeSnapshot, guidance.age_snapshot_id)
                if guidance is not None
                else None
            )
        if guidance is None or snapshot is None:
            raise ChildLineageMismatchError("Pinned age snapshot has no guidance for the report")
        return PinnedChildAgeGuidance(report=report, age_snapshot=snapshot, guidance=guidance)

    async def get_latest_chart_version(self, child_profile_id: UUID) -> models.ChildChartVersion | None:
        result = await self.session.execute(
            select(models.ChildChartVersion)
            .where(models.ChildChartVersion.child_profile_id == child_profile_id)
            .order_by(models.ChildChartVersion.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_report(
        self,
        *,
        child_profile_id: UUID,
        owner_user_id: UUID,
    ) -> models.ChildReport | None:
        result = await self.session.execute(
            select(models.ChildReport)
            .join(models.ChildProfile, models.ChildReport.child_profile_id == models.ChildProfile.id)
            .where(
                models.ChildReport.child_profile_id == child_profile_id,
                models.ChildProfile.owner_user_id == owner_user_id,
            )
            .order_by(models.ChildReport.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_owned_report_id(self, *, report_id: UUID, owner_user_id: UUID) -> UUID | None:
        """Resolve ownership without loading report payload columns."""

        return cast(
            UUID | None,
            await self.session.scalar(
                select(models.ChildReport.id)
                .join(models.ChildProfile, models.ChildReport.child_profile_id == models.ChildProfile.id)
                .where(
                    models.ChildReport.id == report_id,
                    models.ChildProfile.owner_user_id == owner_user_id,
                )
            ),
        )
