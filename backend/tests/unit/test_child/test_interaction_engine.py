from __future__ import annotations

import copy
import math
import random
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from app.modules.astrotype_v2.models import NatalChart, NatalHouse, NatalPlanetPosition
from app.modules.child.models import (
    ChildChartVersion,
    ChildNeedScore,
    ChildParentStyleScore,
    ChildSynastryEvidence,
)
from app.modules.child.scoring.types import (
    ChildNeedDimension,
    InteractionResult,
    ParentStyleDimension,
)

PARENT_VALUES = {
    ParentStyleDimension.EMOTIONAL_RESPONSIVENESS: 82.0,
    ParentStyleDimension.STRUCTURE: 76.0,
    ParentStyleDimension.CONTROL_TENDENCY: 42.0,
    ParentStyleDimension.FLEXIBILITY: 68.0,
    ParentStyleDimension.COMMUNICATION_STYLE: 79.0,
    ParentStyleDimension.PROTECTION: 63.0,
    ParentStyleDimension.AUTONOMY_SUPPORT: 74.0,
    ParentStyleDimension.CONSISTENCY: 71.0,
}
CHILD_VALUES = {
    ChildNeedDimension.REASSURANCE: 84.0,
    ChildNeedDimension.PREDICTABILITY: 70.0,
    ChildNeedDimension.AUTONOMY: 77.0,
    ChildNeedDimension.VERBAL_EXPLANATION: 80.0,
    ChildNeedDimension.PHYSICAL_SENSORY_CALM: 66.0,
    ChildNeedDimension.EXPLORATION: 72.0,
    ChildNeedDimension.RECOGNITION: 69.0,
    ChildNeedDimension.PERSONAL_SPACE: 55.0,
    ChildNeedDimension.TRANSITION_TIME: 62.0,
    ChildNeedDimension.VARIETY: 64.0,
}


def _parent_chart(*, exact: bool = True) -> NatalChart:
    return NatalChart(
        id=uuid.UUID(int=1),
        user_id=uuid.UUID(int=2),
        profile_id=uuid.UUID(int=3),
        engine_version="0.1.6",
        input_hash="p" * 64,
        birth_datetime_utc=datetime(1990, 1, 1, 9, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.7,
        longitude=37.6,
        house_system="P",
        calculation_payload={
            "birth_time_proof": {
                "contract_version": "natal-timing-proof-v1",
                "birth_time_confidence": "exact" if exact else "unknown",
                "user_supplied_time": exact,
                "synthetic_noon": not exact,
            }
        },
    )


def _positions(chart_id: uuid.UUID, longitudes: dict[str, float] | None = None) -> list[NatalPlanetPosition]:
    values = longitudes or {
        "Sun": 10.0,
        "Moon": 40.0,
        "Mercury": 70.0,
        "Venus": 100.0,
        "Mars": 130.0,
        "Jupiter": 160.0,
        "Saturn": 190.0,
    }
    return [
        NatalPlanetPosition(
            id=uuid.uuid5(uuid.NAMESPACE_URL, f"{chart_id}:{body}"),
            chart_id=chart_id,
            body=body,
            longitude=longitude,
            latitude=0.0,
            speed=1.0,
            sign="Aries",
            sign_degree=longitude % 30,
            house_number=index,
            retrograde=False,
        )
        for index, (body, longitude) in enumerate(values.items(), start=1)
    ]


def _houses(chart_id: uuid.UUID) -> list[NatalHouse]:
    return [
        NatalHouse(
            id=uuid.uuid5(uuid.NAMESPACE_URL, f"{chart_id}:house:{number}"),
            chart_id=chart_id,
            house_number=number,
            longitude=float((number - 1) * 30),
            sign="Aries",
        )
        for number in range(1, 13)
    ]


def _child_chart(*, confidence: str = "exact", longitudes: dict[str, float] | None = None) -> ChildChartVersion:
    values = longitudes or {
        "Sun": 12.0,
        "Moon": 42.0,
        "Mercury": 72.0,
        "Venus": 102.0,
        "Mars": 132.0,
        "Jupiter": 162.0,
        "Saturn": 192.0,
    }
    exact = confidence == "exact"
    payload: dict[str, object] = {
        "contract_version": "child-birth-time-policy-v3",
        "technical_reference": {
            "birth_datetime_utc": "2021-05-12T07:00:00+00:00" if exact else "2021-05-12T09:00:00+00:00",
            "synthetic_noon": not exact,
            "user_supplied_time": exact,
            "birth_time_confidence": confidence,
        },
        "planet_positions": [
            {
                "body": body,
                "sign": "Aries",
                "house_number": index if exact else None,
                "longitude": longitude,
                "latitude": 0.0,
                "speed": 1.0,
                "sign_degree": longitude % 30,
                "retrograde": False,
            }
            for index, (body, longitude) in enumerate(values.items(), start=1)
        ],
        "houses": (
            [{"house_number": n, "longitude": float((n - 1) * 30), "sign": "Aries"} for n in range(1, 13)]
            if exact
            else []
        ),
        "aspects": [],
        "stability_evidence": (
            {"policy_version": "child-birth-time-policy-v3", "exact_input": True, "confidence": 1.0}
            if exact
            else {
                "policy_version": "child-birth-time-policy-v3",
                "window": "local_birth_date",
                "sample_datetimes_utc": [
                    "2021-05-11T21:00:00+00:00",
                    "2021-05-12T09:00:00+00:00",
                    "2021-05-12T20:59:59+00:00",
                ],
                "facts": {
                    f"planet_sign:{body}": {
                        "stable": body != "Moon",
                        "confidence": 1.0,
                        "observed_values": ["Aries"] * 3,
                        "sample_count": 3,
                    }
                    for body in values
                },
            }
        ),
        "exclusions": []
        if exact
        else ["houses", "angles", "house_assignments", "house_overlays", "moon_sign", "planet_sign:Moon"],
    }
    return ChildChartVersion(
        id=uuid.UUID(int=4),
        child_profile_id=uuid.UUID(int=5),
        version=1,
        engine_version="0.1.6",
        input_hash="c" * 64,
        birth_time_confidence=confidence,
        allowed_fact_families=(
            [
                "planet_positions",
                "planet_signs",
                "moon_sign",
                "aspects",
                "houses",
                "angles",
                "house_assignments",
                "house_overlays",
            ]
            if exact
            else ["planet_positions", "planet_signs", "stable_aspects"]
        ),
        excluded_fact_families=copy.deepcopy(payload["exclusions"]),
        uncertainty_reason=None if exact else "unknown_birth_time",
        calculation_payload=payload,
    )


def _parent_scores(
    values: dict[ParentStyleDimension, float] | None = None, *, confidence: float = 0.9
) -> tuple[ChildParentStyleScore, ...]:
    source = values or PARENT_VALUES
    return tuple(
        ChildParentStyleScore(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"parent:{dimension.value}"),
            child_profile_id=uuid.UUID(int=5),
            parent_chart_id=uuid.UUID(int=1),
            generation_id=uuid.UUID(int=6),
            dimension=dimension.value,
            score=source[dimension],
            confidence=confidence,
            scoring_version="parent-style-mvp-2",
            breakdown={
                "reference_version": "parent-style-reference-1",
                "supports": [{"lineage_refs": [f"astrotype_v2_natal_planet_positions:key:{dimension.value}"]}],
                "counters": [],
            },
            evidence_refs=[f"parent:{dimension.value}"],
        )
        for dimension in ParentStyleDimension
    )


def _child_scores(
    values: dict[ChildNeedDimension, float] | None = None, *, confidence: float = 0.9
) -> tuple[ChildNeedScore, ...]:
    source = values or CHILD_VALUES
    return tuple(
        ChildNeedScore(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"child:{dimension.value}"),
            child_profile_id=uuid.UUID(int=5),
            child_chart_version_id=uuid.UUID(int=4),
            generation_id=uuid.UUID(int=6),
            dimension=dimension.value,
            score=source[dimension],
            confidence=confidence,
            scoring_version="child-needs-mvp-1",
            breakdown={
                "reference_version": "child-needs-reference-1",
                "supports": [{"lineage_refs": [f"child_chart_versions:key:planet_positions:{dimension.value}"]}],
                "counters": [],
            },
            evidence_refs=[f"child:{dimension.value}"],
        )
        for dimension in ChildNeedDimension
    )


def _evidence_snapshot(rows: Sequence[ChildSynastryEvidence]) -> list[tuple[object, ...]]:
    return [
        (
            row.id,
            row.source_type,
            row.source_key,
            row.contribution,
            row.direction,
            row.payload,
        )
        for row in rows
    ]


def _score(
    *,
    parent_scores: Sequence[ChildParentStyleScore] | None = None,
    child_scores: Sequence[ChildNeedScore] | None = None,
    parent_chart: NatalChart | None = None,
    child_chart: ChildChartVersion | None = None,
    positions: Sequence[NatalPlanetPosition] | None = None,
    houses: Sequence[NatalHouse] | None = None,
) -> tuple[tuple[InteractionResult, ...], tuple[ChildSynastryEvidence, ...]]:
    from app.modules.child.interaction import score_interactions
    from app.modules.child.synastry import build_synastry_evidence

    parent_chart = parent_chart or _parent_chart()
    child_chart = child_chart or _child_chart()
    pair_evidence = build_synastry_evidence(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart=parent_chart,
        parent_positions=positions or _positions(parent_chart.id),
        child_chart=child_chart,
        parent_houses=houses or _houses(parent_chart.id),
    )
    return score_interactions(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart_id=parent_chart.id,
        child_chart_version_id=child_chart.id,
        parent_scores=parent_scores or _parent_scores(),
        child_need_scores=child_scores or _child_scores(),
        synastry_evidence=pair_evidence,
    ), pair_evidence


def test_interaction_engine_returns_exactly_eight_canonical_dimensions_and_no_compatibility_contract() -> None:
    from app.modules.child.scoring.types import InteractionDimension

    first, evidence = _score()
    shuffled_parent = list(_parent_scores())
    shuffled_child = list(_child_scores())
    random.Random(20261018).shuffle(shuffled_parent)  # noqa: S311
    random.Random(20261019).shuffle(shuffled_child)  # noqa: S311
    second, shuffled_evidence = _score(parent_scores=shuffled_parent, child_scores=shuffled_child)

    assert first == second
    assert _evidence_snapshot(evidence) == _evidence_snapshot(shuffled_evidence)
    assert tuple(result.dimension for result in first) == tuple(InteractionDimension)
    assert len(first) == 8
    assert all(result.scoring_version == "child-interaction-mvp-1" for result in first)
    assert all(result.pattern in {"natural_match", "moderate_tension", "high_attention"} for result in first)
    assert all(0 <= result.score <= 100 and 0 <= result.confidence <= 1 for result in first)
    assert all(not hasattr(result, "compatibility") and not hasattr(result, "child_trait") for result in first)
    assert all(item.payload.get("factor_label") not in {"harm", "blame", "suppression"} for item in evidence)


def test_opposite_pair_inputs_change_at_least_one_dimension() -> None:
    baseline, _ = _score()
    opposite_values = {dimension: 100.0 - value for dimension, value in CHILD_VALUES.items()}
    opposite, _ = _score(child_scores=_child_scores(opposite_values))

    assert any(left.score != right.score for left, right in zip(baseline, opposite, strict=True))


def test_unreliable_time_excludes_overlays_and_unknown_moon_even_with_optimistic_payload() -> None:
    parent = _parent_chart(exact=False)
    child = _child_chart(confidence="unknown")
    child.calculation_payload["stability_evidence"]["facts"]["planet_sign:Moon"]["stable"] = True
    child.calculation_payload["exclusions"].remove("planet_sign:Moon")
    child.excluded_fact_families.remove("planet_sign:Moon")

    _, evidence = _score(parent_chart=parent, child_chart=child, positions=_positions(parent.id))

    assert all(item.source_type != "house_overlay" for item in evidence)
    assert all("moon" not in item.source_key.casefold() for item in evidence)


def test_exact_time_pair_emits_pair_bound_house_overlays() -> None:
    _, evidence = _score()

    overlays = [item for item in evidence if item.source_type == "house_overlay"]
    assert overlays
    assert {item.payload["overlay_direction"] for item in overlays} == {"child_in_parent", "parent_in_child"}
    assert all(item.payload["time_reliable_for_overlays"] is True for item in overlays)


def test_single_family_single_lineage_and_saturn_only_are_neutral_and_safe() -> None:
    low_parent = _parent_scores(confidence=0.0)
    low_child = _child_scores(confidence=0.0)
    saturn_parent = _positions(uuid.UUID(int=1), {"Saturn": 10.0})
    saturn_child = _child_chart(longitudes={"Sun": 10.0})

    results, evidence = _score(
        parent_scores=low_parent,
        child_scores=low_child,
        positions=saturn_parent,
        child_chart=saturn_child,
    )

    assert all(result.score == 50 and result.confidence == 0 for result in results)
    assert evidence
    assert all(abs(item.contribution) <= 0.08 for item in evidence)
    saturn_evidence = [item for item in evidence if item.source_type == "cross_chart_aspect"]
    assert saturn_evidence
    assert all(item.payload["factor_label"] == "structure_expectations_pressure_awareness" for item in saturn_evidence)
    assert all(item.payload["factor_label"] not in {"harm", "blame", "suppression"} for item in evidence)


def test_correlated_synastry_evidence_is_capped_and_deduplicated() -> None:
    results, evidence = _score()

    for result in results:
        totals = dict(result.breakdown.correlation_family_totals)
        assert all(abs(total) <= 0.30 for total in totals.values())
        leaf_refs = [ref for item in (*result.supports, *result.counters) for ref in item.evidence_refs]
        assert len(leaf_refs) == len(set(leaf_refs))
    assert len({item.source_key for item in evidence}) == len(evidence)


def test_duplicate_and_reversed_input_order_is_deterministic_but_conflicts_fail_closed() -> None:
    from app.modules.child.synastry import build_synastry_evidence

    parent = _parent_chart()
    child = _child_chart()
    positions = _positions(parent.id)
    duplicate = copy.deepcopy(positions[0])
    duplicate.body = " sun "
    duplicate.id = uuid.uuid4()
    duplicated = [*reversed(positions), duplicate]

    expected = build_synastry_evidence(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart=parent,
        parent_positions=positions,
        child_chart=child,
    )
    actual = build_synastry_evidence(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart=parent,
        parent_positions=duplicated,
        child_chart=child,
    )
    assert _evidence_snapshot(actual) == _evidence_snapshot(expected)

    conflicting = copy.deepcopy(duplicate)
    conflicting.longitude += 1.0
    with pytest.raises(ValueError, match="conflicting duplicate"):
        build_synastry_evidence(
            child_profile_id=uuid.UUID(int=5),
            generation_id=uuid.UUID(int=6),
            parent_chart=parent,
            parent_positions=[*positions, conflicting],
            child_chart=child,
        )


@pytest.mark.parametrize("bad", [math.nan, math.inf, -0.1, 100.1])
def test_invalid_score_inputs_are_rejected(bad: float) -> None:
    rows = list(_parent_scores())
    rows[0].score = bad

    with pytest.raises(ValueError, match=r"finite.*range"):
        _score(parent_scores=rows)


def test_pair_identity_is_bound_into_deterministic_evidence_and_score_rows() -> None:
    from app.modules.child.interaction import build_interaction_rows

    results, evidence = _score()
    rows_ab = build_interaction_rows(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart_id=uuid.UUID(int=1),
        child_chart_version_id=uuid.UUID(int=4),
        results=results,
    )
    rows_ac = build_interaction_rows(
        child_profile_id=uuid.UUID(int=7),
        generation_id=uuid.UUID(int=8),
        parent_chart_id=uuid.UUID(int=1),
        child_chart_version_id=uuid.UUID(int=9),
        results=results,
    )

    assert {row.id for row in rows_ab}.isdisjoint(row.id for row in rows_ac)
    assert all(item.child_profile_id == uuid.UUID(int=5) for item in evidence)
    assert all(item.generation_id == uuid.UUID(int=6) for item in evidence)
    assert all(item.parent_chart_id == uuid.UUID(int=1) for item in evidence)
    assert all(item.child_chart_version_id == uuid.UUID(int=4) for item in evidence)


def _score_breakdown_with_lineage(reference_version: str, *refs: str) -> dict[str, object]:
    return {
        "reference_version": reference_version,
        "supports": [{"lineage_refs": list(refs)}],
        "counters": [],
    }


def test_fit_independence_uses_underlying_lineage_not_derived_score_ids() -> None:
    shared = "astrotype_v2_natal_planet_positions:key:moon"
    parent = list(_parent_scores())
    child = list(_child_scores())
    for parent_row in parent:
        parent_row.breakdown = _score_breakdown_with_lineage("parent-style-reference-1", shared)
    for child_row in child:
        child_row.breakdown = _score_breakdown_with_lineage("child-needs-reference-1", shared)

    results, _ = _score(
        parent_scores=parent,
        child_scores=child,
        positions=_positions(uuid.UUID(int=1), {"Uranus": 13.0}),
        houses=_houses(uuid.UUID(int=1))[:1],
    )

    assert all(result.score == 50.0 and result.confidence == 0.0 for result in results)
    assert all(result.breakdown.independent_lineage_refs in {(), (shared,)} for result in results)
    assert all(
        not ref.startswith(("child_parent_style_scores:", "child_need_scores:"))
        for result in results
        for ref in result.breakdown.independent_lineage_refs
    )


def test_saturn_total_is_capped_per_dimension_across_all_personal_planets() -> None:
    parent = _positions(uuid.UUID(int=1), {"Saturn": 10.0})
    child = _child_chart(longitudes={"Sun": 10.0, "Moon": 10.0, "Mercury": 10.0, "Venus": 10.0, "Mars": 10.0})

    results, evidence = _score(positions=parent, child_chart=child)

    saturn_rows = [row for row in evidence if row.source_key.startswith("cross_aspect:parent_saturn:")]
    assert len(saturn_rows) == 5
    assert {row.payload["correlation_family"] for row in saturn_rows} == {"pair:saturn-pressure"}
    for result in results:
        saturn_leaves = [
            item for item in (*result.supports, *result.counters) if item.correlation_family == "pair:saturn-pressure"
        ]
        assert abs(sum(item.contribution for item in saturn_leaves)) <= 0.08 + 1e-9
        assert abs(dict(result.breakdown.correlation_family_totals).get("pair:saturn-pressure", 0.0)) <= 0.08
    assert all(row.payload["factor_label"] == "structure_expectations_pressure_awareness" for row in saturn_rows)


def test_normative_reverse_pairs_and_exact_angles_are_emitted_but_unreliable_angles_are_excluded() -> None:
    from app.modules.child.synastry import build_synastry_evidence

    parent = _parent_chart()
    positions = _positions(
        parent.id,
        {"Moon": 10.0, "Mars": 30.0, "Ascendant": 50.0, "MC": 70.0},
    )
    child = _child_chart(longitudes={"Venus": 10.0, "Mercury": 30.0, "Sun": 50.0, "Ascendant": 30.0})
    exact = build_synastry_evidence(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart=parent,
        parent_positions=positions,
        child_chart=child,
    )
    keys = {row.source_key for row in exact}
    assert "cross_aspect:parent_moon:child_venus:conjunction" in keys
    assert "cross_aspect:parent_mars:child_mercury:conjunction" in keys
    assert "angle_aspect:parent_ascendant:child_sun:conjunction" in keys
    assert "angle_aspect:parent_mars:child_ascendant:conjunction" in keys

    unreliable = _child_chart(confidence="unknown", longitudes={"Sun": 50.0, "Ascendant": 30.0})
    excluded = build_synastry_evidence(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart=parent,
        parent_positions=positions,
        child_chart=unreliable,
    )
    assert all(row.source_type != "angle_aspect" for row in excluded)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -0.1, 360.0])
def test_malformed_exact_child_longitude_fails_closed_for_the_entire_builder(bad: float) -> None:
    from app.modules.child.synastry import build_synastry_evidence

    parent = _parent_chart()
    child = _child_chart()
    child.calculation_payload["planet_positions"][1]["longitude"] = bad

    assert (
        build_synastry_evidence(
            child_profile_id=uuid.UUID(int=5),
            generation_id=uuid.UUID(int=6),
            parent_chart=parent,
            parent_positions=_positions(parent.id),
            child_chart=child,
        )
        == ()
    )


def test_conflicting_duplicate_exact_child_longitude_is_rejected_without_partial_evidence() -> None:
    from app.modules.child.synastry import build_synastry_evidence

    parent = _parent_chart()
    child = _child_chart()
    duplicate = copy.deepcopy(child.calculation_payload["planet_positions"][0])
    duplicate["body"] = " sun "
    duplicate["longitude"] = 99.0
    child.calculation_payload["planet_positions"].append(duplicate)

    with pytest.raises(ValueError, match="conflicting duplicate child position"):
        build_synastry_evidence(
            child_profile_id=uuid.UUID(int=5),
            generation_id=uuid.UUID(int=6),
            parent_chart=parent,
            parent_positions=_positions(parent.id),
            child_chart=child,
        )


def test_persisted_current_rows_reject_relabelled_ids_and_unsafe_synastry_contract() -> None:
    from app.modules.child.interaction import build_interaction_rows
    from app.modules.child.repository import ChildLineageMismatchError, ChildRepository

    results, evidence = _score()
    scores = list(
        build_interaction_rows(
            child_profile_id=uuid.UUID(int=5),
            generation_id=uuid.UUID(int=6),
            parent_chart_id=uuid.UUID(int=1),
            child_chart_version_id=uuid.UUID(int=4),
            results=results,
        )
    )
    for evidence_row in evidence:
        evidence_row.child_profile_id = uuid.UUID(int=7)
        evidence_row.payload["child_profile_id"] = str(uuid.UUID(int=7))
    for score_row in scores:
        score_row.child_profile_id = uuid.UUID(int=7)
        score_row.breakdown["pair_lineage"]["child_profile_id"] = str(uuid.UUID(int=7))
    with pytest.raises(ChildLineageMismatchError):
        ChildRepository._validate_interaction_profile(
            evidence,
            scores,
            child_profile_id=uuid.UUID(int=7),
            generation_id=uuid.UUID(int=6),
            parent_chart_id=uuid.UUID(int=1),
            child_chart_version_id=uuid.UUID(int=4),
        )

    results, evidence = _score()
    valid_scores = build_interaction_rows(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart_id=uuid.UUID(int=1),
        child_chart_version_id=uuid.UUID(int=4),
        results=results,
    )
    ChildRepository._validate_interaction_profile(
        evidence,
        valid_scores,
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart_id=uuid.UUID(int=1),
        child_chart_version_id=uuid.UUID(int=4),
    )
    evidence[0].source_type = "invented"
    evidence[0].payload["aspect_code"] = "invented"
    with pytest.raises(ChildLineageMismatchError):
        ChildRepository._validate_interaction_profile(
            evidence,
            valid_scores,
            child_profile_id=uuid.UUID(int=5),
            generation_id=uuid.UUID(int=6),
            parent_chart_id=uuid.UUID(int=1),
            child_chart_version_id=uuid.UUID(int=4),
        )

    results, aspect_evidence = _score()
    aspect_scores = build_interaction_rows(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart_id=uuid.UUID(int=1),
        child_chart_version_id=uuid.UUID(int=4),
        results=results,
    )
    aspect_row = next(row for row in aspect_evidence if row.source_type == "cross_chart_aspect")
    aspect_row.payload["aspect_code"] = "invented"
    with pytest.raises(ChildLineageMismatchError, match="aspect code"):
        ChildRepository._validate_interaction_profile(
            aspect_evidence,
            aspect_scores,
            child_profile_id=uuid.UUID(int=5),
            generation_id=uuid.UUID(int=6),
            parent_chart_id=uuid.UUID(int=1),
            child_chart_version_id=uuid.UUID(int=4),
        )

    results, identity_evidence = _score()
    identity_scores = list(
        build_interaction_rows(
            child_profile_id=uuid.UUID(int=5),
            generation_id=uuid.UUID(int=6),
            parent_chart_id=uuid.UUID(int=1),
            child_chart_version_id=uuid.UUID(int=4),
            results=results,
        )
    )
    identity_scores[0].id = uuid.uuid4()
    with pytest.raises(ChildLineageMismatchError, match="score identity"):
        ChildRepository._validate_interaction_profile(
            identity_evidence,
            identity_scores,
            child_profile_id=uuid.UUID(int=5),
            generation_id=uuid.UUID(int=6),
            parent_chart_id=uuid.UUID(int=1),
            child_chart_version_id=uuid.UUID(int=4),
        )

    results, leaf_evidence = _score()
    leaf_scores = build_interaction_rows(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart_id=uuid.UUID(int=1),
        child_chart_version_id=uuid.UUID(int=4),
        results=results,
    )
    first_leaves = [*leaf_scores[0].breakdown["supports"], *leaf_scores[0].breakdown["counters"]]
    first_leaves[0]["fact_id"] = str(uuid.uuid4())
    with pytest.raises(ChildLineageMismatchError, match="leaf identity"):
        ChildRepository._validate_interaction_profile(
            leaf_evidence,
            leaf_scores,
            child_profile_id=uuid.UUID(int=5),
            generation_id=uuid.UUID(int=6),
            parent_chart_id=uuid.UUID(int=1),
            child_chart_version_id=uuid.UUID(int=4),
        )


@pytest.mark.parametrize(
    "cusps",
    [
        [0.0, 180.0, 30.0, 60.0, 90.0, 120.0, 150.0, 210.0, 240.0, 270.0, 300.0, 330.0],
        [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 300.0],
    ],
)
def test_malformed_parent_cusp_cycle_excludes_all_house_overlays(cusps: list[float]) -> None:
    from app.modules.child.synastry import build_synastry_evidence

    parent = _parent_chart()
    houses = _houses(parent.id)
    for house, longitude in zip(houses, cusps, strict=True):
        house.longitude = longitude

    evidence = build_synastry_evidence(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart=parent,
        parent_positions=_positions(parent.id),
        child_chart=_child_chart(),
        parent_houses=houses,
    )

    assert all(row.source_type != "house_overlay" for row in evidence)


def test_malformed_child_cusp_cycle_excludes_all_house_overlays() -> None:
    from app.modules.child.synastry import build_synastry_evidence

    child = _child_chart()
    child.calculation_payload["houses"][1]["longitude"] = 180.0

    evidence = build_synastry_evidence(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart=_parent_chart(),
        parent_positions=_positions(uuid.UUID(int=1)),
        child_chart=child,
        parent_houses=_houses(uuid.UUID(int=1)),
    )

    assert all(row.source_type != "house_overlay" for row in evidence)


def test_identical_thirteenth_parent_cusp_excludes_all_house_overlays() -> None:
    from app.modules.child.synastry import build_synastry_evidence

    parent = _parent_chart()
    houses = _houses(parent.id)
    houses.append(copy.deepcopy(houses[0]))

    evidence = build_synastry_evidence(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart=parent,
        parent_positions=_positions(parent.id),
        child_chart=_child_chart(),
        parent_houses=houses,
    )

    assert all(row.source_type != "house_overlay" for row in evidence)


def test_identical_thirteenth_child_cusp_excludes_all_house_overlays() -> None:
    from app.modules.child.synastry import build_synastry_evidence

    child = _child_chart()
    child.calculation_payload["houses"].append(copy.deepcopy(child.calculation_payload["houses"][0]))

    evidence = build_synastry_evidence(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart=_parent_chart(),
        parent_positions=_positions(uuid.UUID(int=1)),
        child_chart=child,
        parent_houses=_houses(uuid.UUID(int=1)),
    )

    assert all(row.source_type != "house_overlay" for row in evidence)


def test_wraparound_cusp_cycle_is_valid_for_parent_and_child() -> None:
    from app.modules.child.synastry import build_synastry_evidence

    cusps = [350.0, 20.0, 50.0, 80.0, 110.0, 140.0, 170.0, 200.0, 230.0, 260.0, 290.0, 320.0]
    parent = _parent_chart()
    houses = _houses(parent.id)
    child = _child_chart()
    for house, longitude in zip(houses, cusps, strict=True):
        house.longitude = longitude
    for house, longitude in zip(child.calculation_payload["houses"], cusps, strict=True):
        house["longitude"] = longitude

    evidence = build_synastry_evidence(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart=parent,
        parent_positions=_positions(parent.id),
        child_chart=child,
        parent_houses=houses,
    )

    assert any(row.source_type == "house_overlay" for row in evidence)


def test_saturn_exact_cancellation_preserves_support_and_counter_leaves() -> None:
    from app.modules.child.interaction import _score_dimension
    from app.modules.child.scoring.types import DimensionEvidence, EvidenceDirection, InteractionDimension

    leaves = (
        DimensionEvidence(
            factor_key="saturn-support",
            fact_id=uuid.UUID(int=101),
            evidence_refs=("support",),
            lineage_refs=("parent:saturn", "child:sun"),
            correlation_family="pair:saturn-pressure",
            factor_value=1.0,
            source_quality=1.0,
            weight=0.08,
            contribution=0.08,
            direction=EvidenceDirection.SUPPORTS,
        ),
        DimensionEvidence(
            factor_key="saturn-counter",
            fact_id=uuid.UUID(int=102),
            evidence_refs=("counter",),
            lineage_refs=("parent:saturn", "child:moon"),
            correlation_family="pair:saturn-pressure",
            factor_value=1.0,
            source_quality=1.0,
            weight=0.08,
            contribution=-0.08,
            direction=EvidenceDirection.COUNTERS,
        ),
    )

    result = _score_dimension(InteractionDimension.BOUNDARY_FIT, leaves)

    assert [item.contribution for item in result.supports] == [0.08]
    assert [item.contribution for item in result.counters] == [-0.08]
    assert result.breakdown.raw_delta == 0.0
    assert result.breakdown.agreement == 0.5
    assert dict(result.breakdown.correlation_family_totals)["pair:saturn-pressure"] == 0.0

    from app.modules.child.interaction import build_interaction_rows

    baseline, _ = _score()
    persisted = build_interaction_rows(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart_id=uuid.UUID(int=1),
        child_chart_version_id=uuid.UUID(int=4),
        results=tuple(result if item.dimension is InteractionDimension.BOUNDARY_FIT else item for item in baseline),
    )
    boundary = next(row for row in persisted if row.dimension == InteractionDimension.BOUNDARY_FIT.value)
    assert [leaf["contribution"] for leaf in boundary.breakdown["supports"]] == [0.08]
    assert [leaf["contribution"] for leaf in boundary.breakdown["counters"]] == [-0.08]
    assert boundary.breakdown["confidence_components"]["agreement"] == 0.5


def test_shared_identity_helpers_match_generated_rows_and_leaves() -> None:
    from app.modules.child.interaction import build_interaction_rows
    from app.modules.child.interaction_identity import interaction_fact_id, interaction_score_id, synastry_evidence_id

    results, evidence = _score()
    scores = build_interaction_rows(
        child_profile_id=uuid.UUID(int=5),
        generation_id=uuid.UUID(int=6),
        parent_chart_id=uuid.UUID(int=1),
        child_chart_version_id=uuid.UUID(int=4),
        results=results,
    )

    for evidence_row in evidence:
        assert evidence_row.id == synastry_evidence_id(
            child_profile_id=evidence_row.child_profile_id,
            generation_id=evidence_row.generation_id,
            parent_chart_id=evidence_row.parent_chart_id,
            child_chart_version_id=evidence_row.child_chart_version_id,
            reference_version=evidence_row.reference_version,
            source_key=evidence_row.source_key,
        )
    for score_row in scores:
        assert score_row.id == interaction_score_id(
            child_profile_id=score_row.child_profile_id,
            generation_id=score_row.generation_id,
            parent_chart_id=score_row.parent_chart_id,
            child_chart_version_id=score_row.child_chart_version_id,
            scoring_version=score_row.scoring_version,
            dimension=score_row.dimension,
        )
        for leaf in [*score_row.breakdown["supports"], *score_row.breakdown["counters"]]:
            assert leaf["fact_id"] == str(
                interaction_fact_id(
                    child_profile_id=score_row.child_profile_id,
                    generation_id=score_row.generation_id,
                    parent_chart_id=score_row.parent_chart_id,
                    child_chart_version_id=score_row.child_chart_version_id,
                    factor_key=leaf["factor_key"],
                    dimension=score_row.dimension,
                )
            )


def test_persisted_fit_leaf_is_anchored_to_exact_upstream_rows() -> None:
    from app.modules.child.interaction import build_interaction_rows
    from app.modules.child.repository import ChildLineageMismatchError, ChildRepository

    parent_scores = _parent_scores()
    child_scores = _child_scores()
    results, evidence = _score(parent_scores=parent_scores, child_scores=child_scores)
    scores = list(
        build_interaction_rows(
            child_profile_id=uuid.UUID(int=5),
            generation_id=uuid.UUID(int=6),
            parent_chart_id=uuid.UUID(int=1),
            child_chart_version_id=uuid.UUID(int=4),
            results=results,
        )
    )
    score_row, fit_leaf = next(
        (row, leaf)
        for row in scores
        for leaf in [*row.breakdown["supports"], *row.breakdown["counters"]]
        if leaf["factor_key"].startswith("fit:")
    )
    fit_leaf["factor_value"] = 0.0
    fit_leaf["weight"] = 0.0
    fit_leaf["evidence_refs"] = [
        f"child_parent_style_scores:{parent_scores[-1].id}",
        f"child_need_scores:{child_scores[-1].id}",
    ]
    score_row.evidence_refs = sorted(
        {
            ref
            for leaf in [*score_row.breakdown["supports"], *score_row.breakdown["counters"]]
            for ref in leaf["evidence_refs"]
        }
    )

    with pytest.raises(ChildLineageMismatchError):
        ChildRepository._validate_interaction_profile(
            evidence,
            scores,
            child_profile_id=uuid.UUID(int=5),
            generation_id=uuid.UUID(int=6),
            parent_chart_id=uuid.UUID(int=1),
            child_chart_version_id=uuid.UUID(int=4),
            parent_scores=parent_scores,
            child_need_scores=child_scores,
            expected_evidence=evidence,
        )


def test_create_and_load_use_the_same_pre_read_source_snapshot_lock_helper() -> None:
    import inspect

    from app.modules.child.repository import ChildRepository

    helper_name = "_lock_interaction_source_snapshot"
    assert hasattr(ChildRepository, helper_name)
    create_source = inspect.getsource(ChildRepository.create_interaction_profile)
    load_source = inspect.getsource(ChildRepository.load_interaction_profile)
    lock_source = inspect.getsource(ChildRepository._lock_interaction_source_snapshot)

    assert helper_name in create_source
    assert helper_name in load_source
    assert "_require_owned_child" not in create_source
    assert "_require_owned_child" not in load_source
    assert lock_source.index("models.ChildProfile") < lock_source.index("models.ChildGeneration")
    assert ".with_for_update(read=True)" in lock_source
    assert "populate_existing=True" in lock_source
