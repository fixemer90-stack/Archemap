from __future__ import annotations

import copy
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.modules.astrotype_v2.models import NatalChart, NatalFact, NatalFactEvidence
from app.modules.child.models import ChildParentStyleScore

FIXTURE = Path(__file__).parent / "fixtures" / "parent_style_golden.json"


def _chart(*, exact_timing_proof: bool = False) -> NatalChart:
    technical_reference = (
        {"synthetic_noon": False, "user_supplied_time": True, "birth_time_confidence": "exact"}
        if exact_timing_proof
        else {}
    )
    return NatalChart(
        id=uuid.UUID(int=1),
        user_id=uuid.UUID(int=2),
        profile_id=uuid.UUID(int=3),
        engine_version="test-v1",
        input_hash="a" * 64,
        birth_datetime_utc=datetime(1990, 1, 1, 9, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.7558,
        longitude=37.6173,
        house_system="P",
        calculation_payload={"technical_reference": technical_reference},
    )


def _fact(
    key: str,
    *,
    fact_type: str = "placement",
    weight: float = 1.0,
    confidence: float = 1.0,
) -> NatalFact:
    return NatalFact(
        id=uuid.uuid5(uuid.NAMESPACE_URL, key),
        chart_id=uuid.UUID(int=1),
        fact_type=fact_type,
        fact_key=key,
        title=key,
        summary="persisted summary must not be consumed",
        weight=weight,
        confidence=confidence,
        payload={},
        source_version="v2.0",
    )


def _evidence(facts: list[NatalFact]) -> list[NatalFactEvidence]:
    return [
        NatalFactEvidence(
            id=uuid.uuid5(uuid.NAMESPACE_OID, fact.fact_key),
            fact_id=fact.id,
            chart_id=fact.chart_id,
            source_table=f"astrotype_v2_{fact.fact_type}",
            source_id=uuid.uuid5(uuid.NAMESPACE_DNS, fact.fact_key),
            source_key=fact.fact_key,
            payload={"source_quality": 1.0},
        )
        for fact in facts
    ]


def _evidence_row(
    fact: NatalFact,
    *,
    source_id: uuid.UUID | None,
    source_key: str | None = None,
    source_quality: float = 1.0,
    row_key: str = "default",
) -> NatalFactEvidence:
    return NatalFactEvidence(
        id=uuid.uuid5(uuid.NAMESPACE_OID, f"{fact.fact_key}:{row_key}"),
        fact_id=fact.id,
        chart_id=fact.chart_id,
        source_table=f"astrotype_v2_{fact.fact_type}",
        source_id=source_id,
        source_key=source_key,
        payload={"source_quality": source_quality},
    )


def _golden_facts() -> list[NatalFact]:
    return [
        _fact("placement:moon:cancer:house_4"),
        _fact("placement:venus:libra:house_7"),
        _fact("placement:mercury:gemini:house_3"),
        _fact("placement:mars:aries:house_1"),
        _fact("placement:saturn:capricorn:house_10"),
        _fact("placement:uranus:aquarius:house_11"),
        _fact("placement:sun:leo:house_5"),
        _fact("balance:element:water", fact_type="balance", weight=0.8),
        _fact("balance:element:air", fact_type="balance", weight=0.7),
        _fact("balance:element:earth", fact_type="balance", weight=0.9),
        _fact("balance:modality:fixed", fact_type="balance", weight=0.6),
        _fact("balance:modality:mutable", fact_type="balance", weight=0.7),
    ]


def _parent_style_rows_for_validation() -> list[ChildParentStyleScore]:
    from app.modules.child.parent_style import build_parent_style_rows, score_parent_style

    facts = _golden_facts()
    return list(
        build_parent_style_rows(
            child_profile_id=uuid.uuid4(),
            generation_id=uuid.uuid4(),
            parent_chart_id=_chart().id,
            results=score_parent_style(chart=_chart(), facts=facts, evidence=_evidence(facts)),
        )
    )


def _validate_parent_style_rows(rows: list[ChildParentStyleScore]) -> None:
    from app.modules.child.repository import ChildRepository

    ChildRepository._validate_parent_style_profile(rows, parent_chart_id=_chart().id)


def test_parent_style_returns_exactly_eight_canonical_dimensions_with_golden_output() -> None:
    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    facts = _golden_facts()
    first = score_parent_style(chart=_chart(), facts=facts, evidence=_evidence(facts))
    second = score_parent_style(
        chart=_chart(),
        facts=list(reversed(facts)),
        evidence=list(reversed(_evidence(facts))),
    )

    assert first == second
    assert tuple(result.dimension for result in first) == tuple(ParentStyleDimension)
    assert len(first) == 8
    assert all(0 <= result.score <= 100 for result in first)
    assert all(0 <= result.confidence <= 1 for result in first)
    assert all(result.scoring_version == "parent-style-mvp-1" for result in first)

    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
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
    assert actual == expected


def test_low_evidence_stays_neutral_with_zero_confidence_and_missing_families() -> None:
    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    facts = [_fact("placement:moon:cancer:no_house")]
    result = next(
        item
        for item in score_parent_style(chart=_chart(), facts=facts, evidence=_evidence(facts))
        if item.dimension is ParentStyleDimension.EMOTIONAL_RESPONSIVENESS
    )

    assert result.score == 50
    assert result.confidence == 0
    assert [item.correlation_family for item in result.supports] == ["body:moon"]
    assert result.counters == ()
    assert result.missing_families == ("balance:water", "body:venus", "pair:moon-saturn", "pair:moon-venus")
    assert result.breakdown.independent_family_count == 1
    assert result.breakdown.required_family_count == 2


def test_one_saturn_house_fact_cannot_satisfy_two_family_threshold() -> None:
    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    facts = [_fact("placement:saturn:capricorn:house_10")]
    result = next(
        item
        for item in score_parent_style(
            chart=_chart(exact_timing_proof=True),
            facts=facts,
            evidence=_evidence(facts),
        )
        if item.dimension is ParentStyleDimension.STRUCTURE
    )

    assert result.breakdown.independent_family_count == 2
    assert result.breakdown.independent_lineage_count == 1
    assert result.breakdown.required_lineage_count == 2
    assert result.score == 50
    assert result.confidence == 0


def test_two_facts_from_the_same_persisted_source_lineage_stay_neutral() -> None:
    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    moon = _fact("placement:moon:cancer:no_house")
    venus = _fact("placement:venus:libra:no_house")
    shared_source_id = uuid.uuid4()
    result = next(
        item
        for item in score_parent_style(
            chart=_chart(),
            facts=[moon, venus],
            evidence=[
                _evidence_row(moon, source_id=shared_source_id),
                _evidence_row(venus, source_id=shared_source_id),
            ],
        )
        if item.dimension is ParentStyleDimension.EMOTIONAL_RESPONSIVENESS
    )

    assert result.breakdown.independent_family_count == 1
    assert result.breakdown.independent_lineage_count == 1
    assert result.breakdown.independent_lineage_refs == (f"astrotype_v2_placement:id:{shared_source_id}",)
    assert result.score == 50
    assert result.confidence == 0


def test_source_key_is_canonical_when_mixed_id_and_key_rows_share_the_same_source() -> None:
    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    moon = _fact("placement:moon:cancer:no_house")
    venus = _fact("placement:venus:libra:no_house")
    shared_source_key = "shared-placement-row"
    result = next(
        item
        for item in score_parent_style(
            chart=_chart(),
            facts=[moon, venus],
            evidence=[
                _evidence_row(moon, source_id=uuid.uuid4(), source_key=shared_source_key),
                _evidence_row(venus, source_id=None, source_key=shared_source_key),
            ],
        )
        if item.dimension is ParentStyleDimension.EMOTIONAL_RESPONSIVENESS
    )

    assert result.breakdown.independent_family_count == 1
    assert result.breakdown.independent_lineage_count == 1
    assert result.breakdown.independent_lineage_refs == (f"astrotype_v2_placement:key:{shared_source_key}",)
    assert result.score == 50
    assert result.confidence == 0


def test_duplicate_and_unidentified_evidence_do_not_inflate_quality_or_independence() -> None:
    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    moon = _fact("placement:moon:cancer:no_house")
    venus = _fact("placement:venus:libra:no_house")
    moon_source_id = uuid.uuid4()
    evidence = [
        _evidence_row(moon, source_id=moon_source_id, source_quality=0.4, row_key="one"),
        _evidence_row(moon, source_id=moon_source_id, source_quality=1.0, row_key="duplicate"),
        _evidence_row(venus, source_id=None, source_key=None, source_quality=1.0),
    ]
    result = next(
        item
        for item in score_parent_style(chart=_chart(), facts=[moon, venus], evidence=evidence)
        if item.dimension is ParentStyleDimension.EMOTIONAL_RESPONSIVENESS
    )

    assert result.breakdown.independent_lineage_count == 1
    assert result.breakdown.source_quality == 0.4
    assert result.score == 50
    assert result.confidence == 0


def test_distinct_source_lineages_satisfy_independence_threshold() -> None:
    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    moon = _fact("placement:moon:cancer:no_house")
    venus = _fact("placement:venus:libra:no_house")
    result = next(
        item
        for item in score_parent_style(
            chart=_chart(),
            facts=[moon, venus],
            evidence=[
                _evidence_row(moon, source_id=uuid.uuid4()),
                _evidence_row(venus, source_id=None, source_key="venus-row"),
            ],
        )
        if item.dimension is ParentStyleDimension.EMOTIONAL_RESPONSIVENESS
    )

    assert result.breakdown.independent_lineage_count == 2
    assert result.score > 50
    assert result.confidence > 0


def test_opposite_sign_charts_do_not_produce_identical_parent_style_profiles() -> None:
    from app.modules.child.parent_style import score_parent_style

    receptive_facts = [
        _fact("placement:moon:cancer:no_house"),
        _fact("placement:venus:libra:no_house"),
        _fact("placement:mercury:gemini:no_house"),
        _fact("placement:saturn:capricorn:no_house"),
    ]
    contrasting_facts = [
        _fact("placement:moon:capricorn:no_house"),
        _fact("placement:venus:aries:no_house"),
        _fact("placement:mercury:pisces:no_house"),
        _fact("placement:saturn:cancer:no_house"),
    ]

    receptive = score_parent_style(chart=_chart(), facts=receptive_facts, evidence=_evidence(receptive_facts))
    contrasting = score_parent_style(chart=_chart(), facts=contrasting_facts, evidence=_evidence(contrasting_facts))

    assert tuple(result.score for result in receptive) != tuple(result.score for result in contrasting)


def test_confidence_is_separate_from_score_and_explains_quality_coverage_and_agreement() -> None:
    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    high_facts = [
        _fact("placement:moon:cancer:no_house"),
        _fact("placement:venus:libra:no_house"),
        _fact("balance:element:water", fact_type="balance", weight=0.8),
    ]
    low_facts = [
        _fact(fact.fact_key, fact_type=fact.fact_type, weight=fact.weight, confidence=0.4) for fact in high_facts
    ]
    high = next(
        item
        for item in score_parent_style(chart=_chart(), facts=high_facts, evidence=_evidence(high_facts))
        if item.dimension is ParentStyleDimension.EMOTIONAL_RESPONSIVENESS
    )
    low = next(
        item
        for item in score_parent_style(chart=_chart(), facts=low_facts, evidence=_evidence(low_facts))
        if item.dimension is ParentStyleDimension.EMOTIONAL_RESPONSIVENESS
    )

    assert low.score == high.score
    assert low.confidence == round(high.confidence * 0.4, 4)
    assert high.breakdown.coverage == 0.75
    assert high.breakdown.agreement == 1
    assert high.breakdown.source_quality == 1
    assert low.breakdown.source_quality == 0.4


def test_duplicate_correlated_moon_signals_are_capped_and_order_is_stable() -> None:
    import pytest

    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    moon_facts = [_fact(f"placement:moon:cancer:no_house:{index}") for index in range(12)]
    water = _fact("balance:element:water", fact_type="balance")
    facts = [*moon_facts, water]
    result = next(
        item
        for item in score_parent_style(chart=_chart(), facts=facts, evidence=_evidence(facts))
        if item.dimension is ParentStyleDimension.EMOTIONAL_RESPONSIVENESS
    )

    moon_total = sum(item.contribution for item in result.supports if item.correlation_family == "body:moon")
    assert moon_total == pytest.approx(0.30)
    assert result.score == 74
    assert [item.factor_key for item in result.supports] == [
        item.factor_key
        for item in sorted(
            result.supports,
            key=lambda item: (-abs(item.contribution), item.factor_key, item.correlation_family, str(item.fact_id)),
        )
    ]


def test_time_sensitive_facts_fail_closed_without_explicit_exact_timing_proof() -> None:
    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    facts = [
        _fact("placement:saturn:capricorn:house_10"),
        _fact("balance:element:earth", fact_type="balance"),
    ]
    evidence = _evidence(facts)
    historical = next(
        item
        for item in score_parent_style(chart=_chart(), facts=facts, evidence=evidence)
        if item.dimension is ParentStyleDimension.STRUCTURE
    )
    exact = next(
        item
        for item in score_parent_style(chart=_chart(exact_timing_proof=True), facts=facts, evidence=evidence)
        if item.dimension is ParentStyleDimension.STRUCTURE
    )

    assert "house:10" in historical.missing_families
    assert historical.breakdown.excluded_time_sensitive_refs
    assert "house:10" not in exact.missing_families
    assert exact.score > historical.score
    assert exact.breakdown.excluded_time_sensitive_refs == ()


def test_canonical_adapter_timing_payload_accepts_exact_and_excludes_inexact_timing() -> None:
    from app.modules.astrotype_v2.chart_adapter import NatalTimingProvenance
    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    exact_chart = _chart()
    exact_chart.calculation_payload = {
        "ayanamsa": 0.0,
        "birth_time_proof": NatalTimingProvenance(
            birth_time_accuracy="exact",
            birth_time=datetime(1990, 1, 1, 9, tzinfo=UTC).time(),
        ).as_payload(),
    }
    unknown_chart = _chart()
    unknown_chart.calculation_payload = {
        "ayanamsa": 0.0,
        "birth_time_proof": NatalTimingProvenance(
            birth_time_accuracy="unknown",
            birth_time=None,
        ).as_payload(),
    }
    approximate_chart = _chart()
    approximate_chart.calculation_payload = {
        "ayanamsa": 0.0,
        "birth_time_proof": NatalTimingProvenance(
            birth_time_accuracy="approximate",
            birth_time=datetime(1990, 1, 1, 9, tzinfo=UTC).time(),
        ).as_payload(),
    }
    facts = [
        _fact("placement:saturn:capricorn:house_10"),
        _fact("balance:element:earth", fact_type="balance"),
    ]
    evidence = _evidence(facts)

    exact = next(
        item
        for item in score_parent_style(chart=exact_chart, facts=facts, evidence=evidence)
        if item.dimension is ParentStyleDimension.STRUCTURE
    )
    unknown = next(
        item
        for item in score_parent_style(chart=unknown_chart, facts=facts, evidence=evidence)
        if item.dimension is ParentStyleDimension.STRUCTURE
    )
    approximate = next(
        item
        for item in score_parent_style(chart=approximate_chart, facts=facts, evidence=evidence)
        if item.dimension is ParentStyleDimension.STRUCTURE
    )

    assert "house:10" not in exact.missing_families
    assert exact.breakdown.excluded_time_sensitive_refs == ()
    for excluded in (unknown, approximate):
        assert "house:10" in excluded.missing_families
        assert excluded.breakdown.excluded_time_sensitive_refs


def test_timing_proof_fails_closed_when_any_recognized_block_contradicts_exact_time() -> None:
    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    chart = _chart(exact_timing_proof=True)
    chart.calculation_payload = {
        "birth_time_proof": {
            "synthetic_noon": False,
            "user_supplied_time": True,
            "birth_time_confidence": "exact",
        },
        "technical_reference": {
            "synthetic_noon": True,
            "user_supplied_time": False,
            "birth_time_confidence": "unknown",
        },
    }
    facts = [
        _fact("placement:saturn:capricorn:house_10"),
        _fact("balance:element:earth", fact_type="balance"),
    ]
    result = next(
        item
        for item in score_parent_style(chart=chart, facts=facts, evidence=_evidence(facts))
        if item.dimension is ParentStyleDimension.STRUCTURE
    )

    assert "house:10" in result.missing_families
    assert result.breakdown.excluded_time_sensitive_refs


@pytest.mark.parametrize("malformed", [None, "exact", [], 1])
def test_timing_proof_fails_closed_when_a_recognized_block_is_malformed(malformed: object) -> None:
    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    chart = _chart(exact_timing_proof=True)
    chart.calculation_payload = {
        "birth_time_proof": malformed,
        "technical_reference": {
            "synthetic_noon": False,
            "user_supplied_time": True,
            "birth_time_confidence": "exact",
        },
    }
    facts = [
        _fact("placement:saturn:capricorn:house_10"),
        _fact("balance:element:earth", fact_type="balance"),
    ]
    result = next(
        item
        for item in score_parent_style(chart=chart, facts=facts, evidence=_evidence(facts))
        if item.dimension is ParentStyleDimension.STRUCTURE
    )

    assert "house:10" in result.missing_families
    assert result.breakdown.excluded_time_sensitive_refs


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("weight", -0.01),
        ("weight", 1.01),
        ("weight", float("nan")),
        ("weight", float("inf")),
        ("confidence", -0.01),
        ("confidence", 1.01),
        ("confidence", float("nan")),
        ("confidence", float("inf")),
    ],
)
def test_invalid_fact_numbers_are_rejected_before_scoring(field: str, value: float) -> None:
    from app.modules.child.parent_style import score_parent_style

    fact = _fact(
        "placement:moon:cancer:no_house",
        weight=value if field == "weight" else 1.0,
        confidence=value if field == "confidence" else 1.0,
    )

    with pytest.raises(ValueError, match=field):
        score_parent_style(chart=_chart(), facts=[fact], evidence=_evidence([fact]))


@pytest.mark.parametrize("value", [-0.01, 1.01, float("nan"), float("inf")])
def test_invalid_evidence_source_quality_is_rejected_before_scoring(value: float) -> None:
    from app.modules.child.parent_style import score_parent_style

    fact = _fact("placement:moon:cancer:no_house")
    with pytest.raises(ValueError, match="source_quality"):
        score_parent_style(
            chart=_chart(),
            facts=[fact],
            evidence=[_evidence_row(fact, source_id=uuid.uuid4(), source_quality=value)],
        )


def test_unpersisted_or_cross_chart_evidence_is_rejected_and_unlinked_facts_are_ignored() -> None:
    import pytest

    from app.modules.child.parent_style import score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    linked = _fact("placement:moon:cancer:no_house")
    unlinked = _fact("placement:venus:libra:no_house")
    result = next(
        item
        for item in score_parent_style(chart=_chart(), facts=[linked, unlinked], evidence=_evidence([linked]))
        if item.dimension is ParentStyleDimension.EMOTIONAL_RESPONSIVENESS
    )
    assert result.score == 50
    assert result.confidence == 0
    assert [item.factor_key for item in result.supports] == [linked.fact_key]

    wrong = _evidence([linked])[0]
    wrong.chart_id = uuid.UUID(int=999)
    with pytest.raises(ValueError, match="supplied parent chart"):
        score_parent_style(chart=_chart(), facts=[linked], evidence=[wrong])


def test_engine_source_has_no_gender_narrative_llm_network_or_report_payload_dependency() -> None:
    root = Path(__file__).resolve().parents[3] / "app"
    source = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "modules/child/parent_style.py",
            "modules/child/scoring/engine.py",
            "modules/child/scoring/types.py",
            "reference_data/child/parent_style_v1.py",
        )
    ).lower()

    for forbidden in (
        "child_gender",
        "owner_gender",
        "self narrative",
        "report_payload",
        "modules.llm",
        "httpx",
        "requests",
        "openai",
    ):
        assert forbidden not in source


def test_parent_style_results_build_complete_orm_rows_with_stable_breakdown() -> None:
    from app.modules.child.parent_style import build_parent_style_rows, score_parent_style
    from app.modules.child.scoring.types import ParentStyleDimension

    facts = _golden_facts()
    child_profile_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    rows = build_parent_style_rows(
        child_profile_id=child_profile_id,
        generation_id=generation_id,
        parent_chart_id=_chart().id,
        results=score_parent_style(chart=_chart(), facts=facts, evidence=_evidence(facts)),
    )
    replayed_rows = build_parent_style_rows(
        child_profile_id=child_profile_id,
        generation_id=generation_id,
        parent_chart_id=_chart().id,
        results=score_parent_style(
            chart=_chart(), facts=list(reversed(facts)), evidence=list(reversed(_evidence(facts)))
        ),
    )

    assert len(rows) == len(ParentStyleDimension)
    assert [row.dimension for row in rows] == [dimension.value for dimension in ParentStyleDimension]
    assert all(row.id is not None for row in rows)
    assert [row.id for row in replayed_rows] == [row.id for row in rows]
    assert all(row.child_profile_id == child_profile_id for row in rows)
    assert all(row.generation_id == generation_id for row in rows)
    assert all(row.parent_chart_id == _chart().id for row in rows)
    assert all(row.scoring_version == "parent-style-mvp-1" for row in rows)
    assert all(row.evidence_refs == sorted(set(row.evidence_refs)) for row in rows)
    assert all(
        {
            "scale",
            "reference_version",
            "supports",
            "counters",
            "missing_families",
            "confidence_components",
            "correlation_family_totals",
            "excluded_time_sensitive_refs",
            "independent_lineage_count",
            "independent_lineage_refs",
            "required_lineage_count",
        }
        <= set(row.breakdown)
        for row in rows
    )
    assert all(row.breakdown["reference_version"] == "parent-style-reference-1" for row in rows)


def test_parent_style_row_builder_rejects_incomplete_reordered_or_wrong_version_results() -> None:
    import pytest

    from app.modules.child.parent_style import build_parent_style_rows, score_parent_style
    from app.modules.child.scoring.types import DimensionResult

    facts = _golden_facts()
    results = score_parent_style(chart=_chart(), facts=facts, evidence=_evidence(facts))
    identifiers = {
        "child_profile_id": uuid.uuid4(),
        "generation_id": uuid.uuid4(),
        "parent_chart_id": _chart().id,
    }

    with pytest.raises(ValueError, match="all canonical dimensions in order"):
        build_parent_style_rows(**identifiers, results=results[:-1])
    with pytest.raises(ValueError, match="all canonical dimensions in order"):
        build_parent_style_rows(**identifiers, results=tuple(reversed(results)))

    first = results[0]
    wrong_version = DimensionResult(
        dimension=first.dimension,
        score=first.score,
        confidence=first.confidence,
        scoring_version="arbitrary-version",
        scale=first.scale,
        supports=first.supports,
        counters=first.counters,
        missing_families=first.missing_families,
        evidence_refs=first.evidence_refs,
        breakdown=first.breakdown,
    )
    with pytest.raises(ValueError, match="unsupported scoring version"):
        build_parent_style_rows(**identifiers, results=(wrong_version, *results[1:]))


def test_parent_style_profile_validator_rejects_current_contract_and_policy_corruption() -> None:
    from app.modules.child.repository import ChildLineageMismatchError

    _validate_parent_style_rows(_parent_style_rows_for_validation())

    corruptions: list[tuple[str, object]] = [
        ("reference_version", "arbitrary-reference"),
        ("scale", {"zero": "copied", "hundred": "copied", "neutral": "copied"}),
        ("required_family_count", 1),
        ("required_lineage_count", 1),
        ("expected_family_count", 99),
    ]
    for key, value in corruptions:
        rows = copy.deepcopy(_parent_style_rows_for_validation())
        rows[0].breakdown[key] = value
        with pytest.raises(ChildLineageMismatchError, match="breakdown"):
            _validate_parent_style_rows(rows)


def test_parent_style_profile_validator_rejects_noncanonical_evidence_and_lineage_refs() -> None:
    from app.modules.child.repository import ChildLineageMismatchError

    rows = copy.deepcopy(_parent_style_rows_for_validation())
    rows[0].breakdown["supports"][0]["evidence_refs"] = []
    with pytest.raises(ChildLineageMismatchError, match="breakdown"):
        _validate_parent_style_rows(rows)

    rows = copy.deepcopy(_parent_style_rows_for_validation())
    rows[0].breakdown["supports"][0]["lineage_refs"] = []
    with pytest.raises(ChildLineageMismatchError, match="breakdown"):
        _validate_parent_style_rows(rows)

    rows = copy.deepcopy(_parent_style_rows_for_validation())
    first_ref = rows[0].breakdown["supports"][0]["lineage_refs"][0]
    rows[0].breakdown["supports"][0]["lineage_refs"].append(first_ref)
    with pytest.raises(ChildLineageMismatchError, match="breakdown"):
        _validate_parent_style_rows(rows)

    rows = copy.deepcopy(_parent_style_rows_for_validation())
    rows[0].evidence_refs = []
    with pytest.raises(ChildLineageMismatchError, match="evidence refs"):
        _validate_parent_style_rows(rows)

    rows = copy.deepcopy(_parent_style_rows_for_validation())
    rows[0].breakdown["independent_lineage_refs"] = ["arbitrary:lineage"] * rows[0].breakdown[
        "independent_lineage_count"
    ]
    with pytest.raises(ChildLineageMismatchError, match="breakdown"):
        _validate_parent_style_rows(rows)


def test_parent_style_profile_validator_rejects_incoherent_family_totals_and_missing_families() -> None:
    from app.modules.child.repository import ChildLineageMismatchError

    rows = copy.deepcopy(_parent_style_rows_for_validation())
    rows[0].breakdown["independent_family_count"] += 1
    with pytest.raises(ChildLineageMismatchError, match="breakdown"):
        _validate_parent_style_rows(rows)

    rows = copy.deepcopy(_parent_style_rows_for_validation())
    rows[0].breakdown["correlation_family_totals"][0]["contribution"] += 0.1
    with pytest.raises(ChildLineageMismatchError, match="breakdown"):
        _validate_parent_style_rows(rows)

    rows = copy.deepcopy(_parent_style_rows_for_validation())
    rows[0].breakdown["correlation_family_totals"].append(
        copy.deepcopy(rows[0].breakdown["correlation_family_totals"][0])
    )
    with pytest.raises(ChildLineageMismatchError, match="breakdown"):
        _validate_parent_style_rows(rows)

    rows = copy.deepcopy(_parent_style_rows_for_validation())
    rows[0].breakdown["missing_families"] = []
    with pytest.raises(ChildLineageMismatchError, match="breakdown"):
        _validate_parent_style_rows(rows)

    rows = copy.deepcopy(_parent_style_rows_for_validation())
    rows[0].breakdown["raw_delta"] += 0.1
    with pytest.raises(ChildLineageMismatchError, match="breakdown"):
        _validate_parent_style_rows(rows)


def test_parent_style_profile_validator_rejects_incoherent_score_and_confidence() -> None:
    from app.modules.child.parent_style import build_parent_style_rows, score_parent_style
    from app.modules.child.repository import ChildLineageMismatchError

    rows = copy.deepcopy(_parent_style_rows_for_validation())
    rows[0].score += 0.001
    with pytest.raises(ChildLineageMismatchError, match="score"):
        _validate_parent_style_rows(rows)

    rows = copy.deepcopy(_parent_style_rows_for_validation())
    rows[0].confidence = 0.0
    with pytest.raises(ChildLineageMismatchError, match="confidence"):
        _validate_parent_style_rows(rows)

    facts = [_fact("placement:moon:cancer:no_house")]
    low_evidence_rows = list(
        build_parent_style_rows(
            child_profile_id=uuid.uuid4(),
            generation_id=uuid.uuid4(),
            parent_chart_id=_chart().id,
            results=score_parent_style(chart=_chart(), facts=facts, evidence=_evidence(facts)),
        )
    )
    low_evidence_rows[0].score = 51.0
    with pytest.raises(ChildLineageMismatchError, match="score"):
        _validate_parent_style_rows(low_evidence_rows)

    low_evidence_rows = copy.deepcopy(low_evidence_rows)
    low_evidence_rows[0].score = 50.0
    low_evidence_rows[0].confidence = 0.1
    with pytest.raises(ChildLineageMismatchError, match="confidence"):
        _validate_parent_style_rows(low_evidence_rows)
