from __future__ import annotations

import copy
import json
import math
import random
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from app.modules.child.birth_time_policy import resolve_birth_time_policy
from app.modules.child.child_needs import ChildNeedResult
from app.modules.child.models import ChildChartVersion, ChildNeedScore

FIXTURE = Path(__file__).parent / "fixtures" / "child_needs_golden.json"


def _chart(
    confidence: str = "exact",
    *,
    allowed: list[str] | None = None,
    payload: dict[str, object] | None = None,
) -> ChildChartVersion:
    if allowed is None:
        allowed = list(resolve_birth_time_policy(confidence).allowed_fact_families)
    if payload is None:
        payload = _payload(confidence)
    return ChildChartVersion(
        id=uuid.UUID(int=101),
        child_profile_id=uuid.UUID(int=102),
        version=3,
        engine_version="0.1.6",
        input_hash="c" * 64,
        birth_time_confidence=confidence,
        allowed_fact_families=allowed,
        excluded_fact_families=list(cast(list[str], payload["exclusions"])),
        uncertainty_reason=resolve_birth_time_policy(confidence).uncertainty_reason,
        calculation_payload=payload,
    )


def _payload(confidence: str = "exact") -> dict[str, object]:
    exact = confidence == "exact"
    positions = [
        ("Sun", "Leo", 5),
        ("Moon", "Cancer", 4),
        ("Mercury", "Gemini", 3),
        ("Venus", "Libra", 7),
        ("Mars", "Aries", 1),
        ("Jupiter", "Sagittarius", 9),
        ("Saturn", "Capricorn", 10),
        ("Uranus", "Aquarius", 11),
        ("Neptune", "Pisces", 12),
        ("Pluto", "Scorpio", 8),
    ]
    sign_by_body = {body: sign for body, sign, _ in positions}
    facts: dict[str, dict[str, object]] = {
        **{f"planet_sign:{body}": {"stable": True, "confidence": 1.0} for body, _, _ in positions},
        "aspect:Moon:Venus:trine": {"stable": True, "confidence": 1.0},
        "aspect:Mercury:Saturn:trine": {"stable": True, "confidence": 1.0},
    }
    if confidence == "unknown":
        facts["planet_sign:Moon"] = {"stable": False, "confidence": 1.0, "reason": "unknown_time_moon"}
        facts["aspect:Moon:Venus:trine"] = {
            "stable": False,
            "confidence": 1.0,
            "reason": "aspect_involves_unstable_body",
        }
    technical_reference: dict[str, object] = {
        "birth_datetime_utc": ("2021-05-12T07:00:00+00:00" if confidence != "unknown" else "2021-05-12T09:00:00+00:00"),
        "synthetic_noon": confidence == "unknown",
        "user_supplied_time": confidence != "unknown",
        "birth_time_confidence": confidence,
    }
    return {
        "contract_version": "child-birth-time-policy-v3",
        "technical_reference": technical_reference,
        "planet_positions": [
            {
                "body": body,
                "sign": sign,
                "house_number": house if exact else None,
                "longitude": 1.0 if exact else None,
                "latitude": 0.0 if exact else None,
                "speed": 1.0 if exact else None,
                "sign_degree": 1.0 if exact else None,
                "retrograde": False if exact else None,
            }
            for body, sign, house in positions
            if confidence != "unknown" or body != "Moon"
        ],
        "houses": (
            [{"house_number": n, "longitude": float(n), "sign": "Aries"} for n in range(1, 13)] if exact else []
        ),
        "aspects": [
            *(
                [
                    {
                        "body_a": "Moon",
                        "body_b": "Venus",
                        "aspect_code": "trine",
                        "angle_degrees": 120.0 if exact else None,
                        "orb_degrees": 1.0 if exact else None,
                        "applying": True if exact else None,
                    }
                ]
                if confidence != "unknown"
                else []
            ),
            {
                "body_a": "Mercury",
                "body_b": "Saturn",
                "aspect_code": "trine",
                "angle_degrees": 120.0 if exact else None,
                "orb_degrees": 2.0 if exact else None,
                "applying": False if exact else None,
            },
        ],
        "stability_evidence": {
            "policy_version": "child-birth-time-policy-v3",
            "exact_input": True,
            "confidence": 1.0,
        }
        if exact
        else (
            {
                "policy_version": "child-birth-time-policy-v3",
                "window_minutes": 60,
                "sample_offsets_minutes": [-60, -30, 0, 30, 60],
                "sample_datetimes_utc": [
                    "2021-05-12T06:00:00+00:00",
                    "2021-05-12T06:30:00+00:00",
                    "2021-05-12T07:00:00+00:00",
                    "2021-05-12T07:30:00+00:00",
                    "2021-05-12T08:00:00+00:00",
                ],
                "facts": {
                    key: {
                        **value,
                        "observed_values": (
                            [sign_by_body[key.split(":", 1)[1]]] * 5 if key.startswith("planet_sign:") else [True] * 5
                        ),
                        "sample_count": 5,
                    }
                    for key, value in facts.items()
                },
            }
            if confidence == "approximate"
            else {
                "policy_version": "child-birth-time-policy-v3",
                "window": "local_birth_date",
                "sample_datetimes_utc": [
                    "2021-05-11T21:00:00+00:00",
                    "2021-05-12T09:00:00+00:00",
                    "2021-05-12T20:59:59+00:00",
                ],
                "facts": {
                    key: {
                        **value,
                        "observed_values": (
                            [sign_by_body[key.split(":", 1)[1]]] * 3 if key.startswith("planet_sign:") else [True] * 3
                        ),
                        "sample_count": 3,
                    }
                    for key, value in facts.items()
                },
            }
        ),
        "exclusions": (
            []
            if exact
            else [
                *resolve_birth_time_policy(confidence).excluded_fact_families,
                *(["aspect:Moon:Venus:trine", "planet_sign:Moon"] if confidence == "unknown" else []),
            ]
        ),
    }


def _score(chart: ChildChartVersion) -> tuple[ChildNeedResult, ...]:
    from app.modules.child.child_needs import score_child_needs

    return score_child_needs(chart=chart)


def _rows() -> list[ChildNeedScore]:
    from app.modules.child.child_needs import build_child_need_rows

    chart = _chart()
    return list(
        build_child_need_rows(
            child_profile_id=chart.child_profile_id,
            generation_id=uuid.UUID(int=103),
            child_chart_version_id=chart.id,
            results=_score(chart),
        )
    )


def test_child_needs_returns_exactly_ten_canonical_dimensions_with_golden_output() -> None:
    from app.modules.child.scoring.types import ChildNeedDimension

    first = _score(_chart())
    shuffled = copy.deepcopy(_chart())
    random.Random(20261017).shuffle(shuffled.calculation_payload["planet_positions"])  # noqa: S311
    random.Random(20261018).shuffle(shuffled.calculation_payload["aspects"])  # noqa: S311
    second = _score(shuffled)

    assert first == second
    assert tuple(result.dimension for result in first) == tuple(ChildNeedDimension)
    assert len(first) == 10
    assert all(result.scoring_version == "child-needs-mvp-1" for result in first)
    assert all(0 <= result.score <= 100 and 0 <= result.confidence <= 1 for result in first)
    actual = {
        result.dimension.value: {
            "score": result.score,
            "confidence": result.confidence,
            "supports": [item.factor_key for item in result.supports],
            "counters": [item.factor_key for item in result.counters],
            "missing_families": list(result.missing_families),
        }
        for result in first
    }
    assert actual == json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_unknown_time_excludes_all_time_sensitive_facts() -> None:
    results = _score(_chart("unknown"))

    assert any(result.supports or result.counters for result in results)
    assert all(
        "house:" in missing for result in results for missing in result.missing_families if missing.startswith("house:")
    )
    assert all(
        not any("house_" in item.factor_key for item in (*result.supports, *result.counters)) for result in results
    )


def test_approximate_time_does_not_infer_house_from_fact_keys_or_payload() -> None:
    chart = _chart("approximate")
    chart.calculation_payload["planet_positions"][0]["house_number"] = 5
    chart.calculation_payload["planet_positions"][0]["body"] = "Sun:house_5"

    results = _score(chart)

    assert all(
        not any("house_" in item.factor_key for item in (*result.supports, *result.counters)) for result in results
    )


def test_approximate_uses_only_stable_facts_present_in_pinned_policy() -> None:
    chart = _chart("approximate")
    chart.calculation_payload["stability_evidence"]["facts"]["planet_sign:Moon"]["stable"] = False
    chart.calculation_payload["stability_evidence"]["facts"]["planet_sign:Moon"]["confidence"] = 0.4

    results = _score(chart)

    assert all(
        not any(item.factor_key.startswith("placement:moon:") for item in (*result.supports, *result.counters))
        for result in results
    )


def test_approximate_requires_complete_consistent_stability_proof() -> None:
    chart = _chart("approximate")
    chart.calculation_payload["stability_evidence"].pop("sample_offsets_minutes")

    results = _score(chart)

    assert all(result.score == 50 and result.confidence == 0 for result in results)
    assert all(not result.supports and not result.counters for result in results)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda chart: chart.allowed_fact_families.append("invented"),
        lambda chart: chart.allowed_fact_families.reverse(),
        lambda chart: setattr(chart, "uncertainty_reason", "not the pinned policy"),
        lambda chart: chart.excluded_fact_families.remove("house_overlays"),
        lambda chart: chart.calculation_payload["exclusions"].append("invented"),
        lambda chart: chart.calculation_payload.__setitem__("exclusions", ["houses", "houses"]),
    ],
)
def test_confidence_allowlists_and_exclusions_must_match_canonical_policy_exactly(
    mutation: Callable[[ChildChartVersion], object],
) -> None:
    chart = _chart("approximate")
    mutation(chart)

    results = _score(chart)

    assert all(result.score == 50 and result.confidence == 0 for result in results)
    assert all(not result.supports and not result.counters for result in results)


def test_exact_chart_rejects_any_house_exclusion_contradiction() -> None:
    chart = _chart("exact")
    chart.excluded_fact_families = ["houses"]
    chart.calculation_payload["exclusions"] = ["houses"]

    assert all(result.score == 50 and result.confidence == 0 for result in _score(chart))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda chart: chart.calculation_payload["stability_evidence"]["sample_datetimes_utc"].__setitem__(0, "junk"),
        lambda chart: chart.calculation_payload["stability_evidence"]["sample_datetimes_utc"].__setitem__(
            0, "2021-05-12T06:00:00"
        ),
        lambda chart: chart.calculation_payload["stability_evidence"]["sample_datetimes_utc"].reverse(),
        lambda chart: chart.calculation_payload["technical_reference"].__setitem__(
            "birth_datetime_utc", "2021-05-12T07:30:00+00:00"
        ),
    ],
)
def test_approximate_stability_samples_must_be_aware_and_match_center_offsets(
    mutation: Callable[[ChildChartVersion], object],
) -> None:
    chart = _chart("approximate")
    mutation(chart)

    assert all(result.score == 50 and result.confidence == 0 for result in _score(chart))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda chart: chart.calculation_payload["stability_evidence"]["sample_datetimes_utc"].__setitem__(
            1, "2021-05-12T08:00:00+00:00"
        ),
        lambda chart: chart.calculation_payload["stability_evidence"]["sample_datetimes_utc"].__setitem__(
            0, "2021-05-12T00:00:00+03:00"
        ),
        lambda chart: chart.calculation_payload["stability_evidence"]["sample_datetimes_utc"].reverse(),
        lambda chart: chart.calculation_payload["stability_evidence"]["sample_datetimes_utc"].__setitem__(
            2, "2021-05-12T20:59:59"
        ),
    ],
)
def test_unknown_stability_samples_must_match_ordered_production_shape(
    mutation: Callable[[ChildChartVersion], object],
) -> None:
    chart = _chart("unknown")
    mutation(chart)

    assert all(result.score == 50 and result.confidence == 0 for result in _score(chart))


@pytest.mark.parametrize(
    "samples",
    [
        [
            "2021-05-11T21:00:00+00:00",
            "2021-05-12T09:00:00+00:00",
            "2021-05-12T20:59:59+00:00",
        ],
        [
            "2021-03-14T05:00:00+00:00",
            "2021-03-14T16:00:00+00:00",
            "2021-03-15T03:59:59+00:00",
        ],
        [
            "2021-11-07T04:00:00+00:00",
            "2021-11-07T17:00:00+00:00",
            "2021-11-08T04:59:59+00:00",
        ],
    ],
    ids=["normal-day", "spring-forward", "fall-back"],
)
def test_unknown_stability_accepts_full_local_day_sample_spans(samples: list[str]) -> None:
    chart = _chart("unknown")
    chart.calculation_payload["stability_evidence"]["sample_datetimes_utc"] = samples
    chart.calculation_payload["technical_reference"]["birth_datetime_utc"] = samples[1]

    assert any(result.supports or result.counters for result in _score(chart))


def test_unknown_stability_rejects_one_second_review_counterexample() -> None:
    chart = _chart("unknown")
    chart.calculation_payload["stability_evidence"]["sample_datetimes_utc"] = [
        "2021-05-12T08:59:59+00:00",
        "2021-05-12T09:00:00+00:00",
        "2021-05-12T09:00:01+00:00",
    ]

    results = _score(chart)

    assert all(result.score == 50 and result.confidence == 0 for result in results)
    assert all(not result.supports and not result.counters for result in results)


def test_stability_observations_must_match_persisted_fact_value() -> None:
    chart = _chart("approximate")
    chart.calculation_payload["stability_evidence"]["facts"]["planet_sign:Moon"]["observed_values"] = ["Leo"] * 5
    chart.calculation_payload["stability_evidence"]["facts"]["aspect:Moon:Venus:trine"]["observed_values"] = [
        "present"
    ] * 5

    results = _score(chart)

    assert all(
        not any(
            item.factor_key.startswith(("placement:moon:", "aspect:moon:venus:"))
            for item in (*result.supports, *result.counters)
        )
        for result in results
    )


def test_unknown_moon_and_moon_aspects_are_rejected_even_with_malicious_stable_proof() -> None:
    chart = _chart("unknown")
    chart.calculation_payload["planet_positions"].append({"body": "Moon", "sign": "Cancer", "house_number": None})
    chart.calculation_payload["aspects"].append({"body_a": "Moon", "body_b": "Venus", "aspect_code": "trine"})
    moon = chart.calculation_payload["stability_evidence"]["facts"]["planet_sign:Moon"]
    moon.update({"stable": True, "confidence": 1.0, "observed_values": ["Cancer"] * 3, "sample_count": 3})
    chart.calculation_payload["stability_evidence"]["facts"]["aspect:Moon:Venus:trine"].update(
        {"stable": True, "confidence": 1.0, "observed_values": [True] * 3, "sample_count": 3}
    )
    chart.excluded_fact_families = list(resolve_birth_time_policy("unknown").excluded_fact_families)
    chart.calculation_payload["exclusions"] = list(resolve_birth_time_policy("unknown").excluded_fact_families)

    results = _score(chart)

    assert any(result.supports or result.counters for result in results)
    assert all(
        not any("moon" in item.factor_key for item in (*result.supports, *result.counters)) for result in results
    )


def test_duplicate_moon_position_and_aspect_do_not_change_scores_or_independence() -> None:
    chart = _chart()
    duplicate = copy.deepcopy(chart)
    duplicate.calculation_payload["planet_positions"].append(
        copy.deepcopy(duplicate.calculation_payload["planet_positions"][1])
    )
    duplicate.calculation_payload["aspects"].append(copy.deepcopy(duplicate.calculation_payload["aspects"][0]))

    assert _score(duplicate) == _score(chart)


@pytest.mark.parametrize("duplicate_first", [False, True])
def test_approximate_case_variant_duplicate_position_is_order_independent(duplicate_first: bool) -> None:
    baseline = _score(_chart("approximate"))
    chart = _chart("approximate")
    canonical = next(row for row in chart.calculation_payload["planet_positions"] if row["body"] == "Mercury")
    duplicate = copy.deepcopy(canonical)
    duplicate.update({"body": "  mErCuRy  ", "sign": "  gEmInI  "})
    if duplicate_first:
        chart.calculation_payload["planet_positions"].insert(0, duplicate)
    else:
        chart.calculation_payload["planet_positions"].append(duplicate)

    assert _score(chart) == baseline
    assert len(_score(chart)) == 10


@pytest.mark.parametrize("duplicate_first", [False, True])
def test_approximate_reversed_case_variant_aspect_is_order_independent(duplicate_first: bool) -> None:
    baseline = _score(_chart("approximate"))
    chart = _chart("approximate")
    canonical = next(
        row for row in chart.calculation_payload["aspects"] if row["body_a"] == "Mercury" and row["body_b"] == "Saturn"
    )
    duplicate = copy.deepcopy(canonical)
    duplicate.update({"body_a": "  sAtUrN  ", "body_b": "  mErCuRy  ", "aspect_code": "  TrInE  "})
    if duplicate_first:
        chart.calculation_payload["aspects"].insert(0, duplicate)
    else:
        chart.calculation_payload["aspects"].append(duplicate)

    actual = _score(chart)
    assert actual == baseline
    assert next(result for result in actual if result.dimension.value == "verbal_explanation") == next(
        result for result in baseline if result.dimension.value == "verbal_explanation"
    )


def test_conflicting_duplicate_position_fails_closed() -> None:
    chart = _chart()
    duplicate = copy.deepcopy(chart.calculation_payload["planet_positions"][1])
    duplicate["sign"] = "Leo"
    chart.calculation_payload["planet_positions"].append(duplicate)

    assert all(result.score == 50 and result.confidence == 0 for result in _score(chart))


def test_conflicting_duplicate_aspect_fails_closed() -> None:
    chart = _chart()
    duplicate = copy.deepcopy(chart.calculation_payload["aspects"][0])
    duplicate["orb_degrees"] = 2.0
    chart.calculation_payload["aspects"].append(duplicate)

    assert all(result.score == 50 and result.confidence == 0 for result in _score(chart))


def test_duplicate_positions_cannot_fabricate_a_balance_fact() -> None:
    chart = _chart()
    moon = next(row for row in chart.calculation_payload["planet_positions"] if row["body"] == "Moon")
    chart.calculation_payload["planet_positions"] = [copy.deepcopy(moon) for _ in range(4)]
    chart.calculation_payload["aspects"] = []

    results = _score(chart)

    assert all(
        not any(item.factor_key.startswith("balance:") for item in (*result.supports, *result.counters))
        for result in results
    )


def test_balance_evidence_uses_only_underlying_planet_position_lineages() -> None:
    results = _score(_chart())
    balances = [
        item
        for result in results
        for item in (*result.supports, *result.counters)
        if item.factor_key.startswith("balance:")
    ]

    assert balances
    assert all(len(item.lineage_refs) > 1 for item in balances)
    assert all(
        ref.startswith("child_chart_versions:key:planet_positions:") for item in balances for ref in item.lineage_refs
    )
    assert all("derived_balance" not in ref for item in balances for ref in item.lineage_refs)


def test_house_rules_match_exact_house_token_not_house_number_prefix() -> None:
    chart = _chart()
    chart.calculation_payload["planet_positions"] = [
        row for row in chart.calculation_payload["planet_positions"] if row["house_number"] in {10, 11, 12}
    ]
    chart.calculation_payload["aspects"] = []

    autonomy = next(result for result in _score(chart) if result.dimension.value == "autonomy")

    assert not any(item.correlation_family == "house:1" for item in (*autonomy.supports, *autonomy.counters))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda chart: setattr(chart, "birth_time_confidence", "approximate"),
        lambda chart: chart.calculation_payload.pop("technical_reference"),
        lambda chart: chart.calculation_payload.__setitem__("technical_reference", "bad"),
        lambda chart: chart.calculation_payload["technical_reference"].__setitem__("synthetic_noon", True),
        lambda chart: chart.calculation_payload["stability_evidence"].__setitem__("policy_version", "stale"),
    ],
)
def test_missing_malformed_or_contradictory_confidence_provenance_fails_closed(
    mutation: Callable[[ChildChartVersion], object],
) -> None:
    chart = _chart()
    mutation(chart)

    results = _score(chart)

    assert all(result.score == 50 and result.confidence == 0 for result in results)
    assert all(not result.supports and not result.counters for result in results)


def test_one_fact_matching_multiple_families_stays_neutral() -> None:
    chart = _chart()
    chart.calculation_payload["planet_positions"] = [
        next(row for row in chart.calculation_payload["planet_positions"] if row["body"] == "Saturn")
    ]
    chart.calculation_payload["aspects"] = []

    results = _score(chart)

    assert all(result.score == 50 and result.confidence == 0 for result in results)


def test_shared_source_lineage_and_duplicate_evidence_do_not_create_independence() -> None:
    from app.modules.child.scoring.engine import score_dimensions
    from app.modules.child.scoring.types import ChildNeedDimension, ScoringEvidence, ScoringFact
    from app.reference_data.child.child_needs_v1 import (
        CHILD_NEEDS_POLICY,
        CHILD_NEEDS_SCALES,
        CHILD_NEEDS_SCORING_VERSION,
    )

    fact_one = ScoringFact(uuid.UUID(int=1), "placement:moon:cancer:no_house", "placement", 1.0, 1.0)
    fact_two = ScoringFact(uuid.UUID(int=2), "balance:element:water", "balance", 1.0, 1.0)
    shared = "child_chart_versions:key:shared"
    result = score_dimensions(
        dimensions=(ChildNeedDimension.REASSURANCE,),
        facts=(fact_one, fact_two),
        evidence=(
            ScoringEvidence(
                uuid.UUID(int=11),
                fact_one.id,
                uuid.UUID(int=9),
                "child_chart_versions",
                uuid.UUID(int=9),
                "shared",
                1.0,
            ),
            ScoringEvidence(
                uuid.UUID(int=12), fact_two.id, uuid.UUID(int=9), "child_chart_versions", None, "shared", 1.0
            ),
            ScoringEvidence(
                uuid.UUID(int=13),
                fact_one.id,
                uuid.UUID(int=9),
                "child_chart_versions",
                uuid.UUID(int=9),
                "shared",
                0.5,
            ),
        ),
        rules=tuple(
            rule
            for rule in __import__(
                "app.reference_data.child.child_needs_v1", fromlist=["CHILD_NEEDS_RULES"]
            ).CHILD_NEEDS_RULES
            if rule.dimension is ChildNeedDimension.REASSURANCE
        ),
        scale_semantics=CHILD_NEEDS_SCALES,
        scoring_version=CHILD_NEEDS_SCORING_VERSION,
        policy=CHILD_NEEDS_POLICY,
        allow_time_sensitive=False,
    )[0]

    assert result.breakdown.independent_lineage_refs == (shared,)
    assert result.score == 50
    assert result.confidence == 0


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_numeric_chart_evidence_is_rejected(value: float) -> None:
    chart = _chart("approximate")
    chart.calculation_payload["stability_evidence"]["facts"]["planet_sign:Moon"]["confidence"] = value

    with pytest.raises(ValueError, match="finite"):
        _score(chart)


def test_opposite_sign_inputs_change_at_least_one_need_dimension() -> None:
    first = _chart()
    second = _chart()
    opposites = {
        "Cancer": "Capricorn",
        "Libra": "Aries",
        "Gemini": "Sagittarius",
        "Aquarius": "Taurus",
        "Pisces": "Virgo",
        "Leo": "Aquarius",
        "Aries": "Libra",
        "Capricorn": "Cancer",
        "Sagittarius": "Gemini",
        "Scorpio": "Taurus",
    }
    for row in second.calculation_payload["planet_positions"]:
        row["sign"] = opposites[row["sign"]]

    assert tuple(item.score for item in _score(first)) != tuple(item.score for item in _score(second))


def test_child_needs_engine_source_has_no_forbidden_context_or_runtime_dependency() -> None:
    root = Path(__file__).resolve().parents[3] / "app"
    source = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "modules/child/child_needs.py",
            "modules/child/scoring/engine.py",
            "reference_data/child/child_needs_v1.py",
        )
    ).lower()
    for forbidden in (
        "child_gender",
        "caregiver_context",
        "questionnaire",
        "parent_style",
        "narrative",
        "report_payload",
        "modules.llm",
        "httpx",
        "requests",
        "openai",
    ):
        assert forbidden not in source


def test_child_need_rows_are_complete_versioned_and_semantically_valid() -> None:
    from app.modules.child.repository import ChildRepository
    from app.modules.child.scoring.types import ChildNeedDimension

    rows = _rows()
    chart = _chart()
    ChildRepository._validate_child_need_profile(rows, child_chart_version_id=chart.id)

    assert [row.dimension for row in rows] == [dimension.value for dimension in ChildNeedDimension]
    assert len(rows) == 10
    assert all(row.scoring_version == "child-needs-mvp-1" for row in rows)
    assert all(row.breakdown["reference_version"] == "child-needs-reference-1" for row in rows)
    assert all(row.child_chart_version_id == chart.id for row in rows)


def test_child_need_validator_rejects_corrupt_json_numbers_refs_and_dimensions() -> None:
    from app.modules.child.repository import ChildLineageMismatchError, ChildRepository

    chart = _chart()
    corruptions = []
    rows = _rows()
    rows[0].dimension = "unknown"
    corruptions.append(rows)
    rows = _rows()
    rows[0].breakdown["confidence_components"]["coverage"] = math.nan
    corruptions.append(rows)
    rows = _rows()
    rows[0].breakdown["supports"][0]["lineage_refs"] = []
    corruptions.append(rows)
    rows = _rows()
    rows[0].score += 0.01
    corruptions.append(rows)
    rows = _rows()
    rows[0].evidence_refs.append(rows[0].evidence_refs[0])
    corruptions.append(rows)
    rows = _rows()
    rows[0].breakdown["supports"][0]["correlation_family"] = "invented:family"
    corruptions.append(rows)
    rows = _rows()
    rows[0].breakdown["supports"][0]["weight"] = 0.99
    corruptions.append(rows)
    rows = _rows()
    original = rows[0].breakdown["supports"][0]
    duplicate = copy.deepcopy(original)
    original["factor_value"] /= 2
    original["contribution"] /= 2
    duplicate["factor_value"] /= 2
    duplicate["contribution"] /= 2
    rows[0].breakdown["supports"].append(duplicate)
    corruptions.append(rows)

    for malformed in corruptions:
        with pytest.raises(ChildLineageMismatchError):
            ChildRepository._validate_child_need_profile(malformed, child_chart_version_id=chart.id)
