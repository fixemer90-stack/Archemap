from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.modules.astrotype_v2.models import NatalFact


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
        summary=key,
        weight=weight,
        confidence=confidence,
        source_version="v2.0",
    )


def _golden_facts() -> list[NatalFact]:
    return [
        _fact("placement:sun:leo:house_10"),
        _fact("placement:moon:libra:house_7"),
        _fact("placement:mercury:virgo:house_6"),
        _fact("placement:venus:libra:house_11"),
        _fact("placement:mars:aries:house_1"),
        _fact("placement:saturn:capricorn:house_10"),
        _fact("placement:uranus:aquarius:house_11"),
        _fact("placement:neptune:pisces:house_5"),
        _fact("balance:element:earth", fact_type="balance", weight=0.8),
        _fact("balance:element:air", fact_type="balance", weight=0.6),
        _fact("balance:modality:cardinal", fact_type="balance", weight=0.7),
        _fact("balance:modality:fixed", fact_type="balance", weight=0.6),
    ]


def test_engine_returns_all_dimensions_with_deterministic_golden_output() -> None:
    from app.modules.career.dimension_engine import score_career_dimensions
    from app.modules.career.factor_catalog import CAREER_SCORING_VERSION
    from app.modules.career.schemas import CareerDimensionKey

    first = score_career_dimensions(_golden_facts())
    second = score_career_dimensions(list(reversed(_golden_facts())))

    assert first == second
    assert {result.dimension for result in first} == set(CareerDimensionKey)
    assert all(result.scoring_version == CAREER_SCORING_VERSION for result in first)
    assert all(0 <= result.score <= 100 for result in first)
    assert all(0 <= result.confidence <= 1 for result in first)
    assert all(result.evidence for result in first)

    snapshot = {result.dimension.value: (result.score, result.confidence, len(result.evidence)) for result in first}
    # `people_orientation` holds three distinct sources: the Moon placement in house 7 matches both
    # the Moon rule and the house_7 rule and is aggregated into one evidence row, so its score and
    # confidence are unchanged while the persisted row count reflects distinct sources only.
    assert snapshot == {
        "analytical_thinking": (67.0, 1.0, 3),
        "autonomy": (72.0, 1.0, 3),
        "communication": (68.0, 1.0, 3),
        "creativity": (68.0, 1.0, 3),
        "execution": (71.0, 1.0, 4),
        "innovation": (64.0, 0.6667, 2),
        "leadership": (70.5, 1.0, 4),
        "long_term_focus": (67.0, 1.0, 3),
        "people_orientation": (68.0, 1.0, 3),
        "risk_tolerance": (52.0, 0.6667, 3),
        "structure": (67.0, 1.0, 3),
        "systems_thinking": (69.0, 1.0, 3),
    }


def test_one_factor_cannot_move_a_dimension_from_neutral() -> None:
    from app.modules.career.dimension_engine import score_career_dimensions
    from app.modules.career.schemas import CareerDimensionKey

    results = {
        result.dimension: result for result in score_career_dimensions([_fact("placement:mercury:virgo:no_house")])
    }

    analytical = results[CareerDimensionKey.ANALYTICAL_THINKING]
    assert analytical.score == 50
    assert analytical.confidence == 0
    assert len(analytical.evidence) == 1


def test_source_quality_reduces_confidence_without_changing_score() -> None:
    from app.modules.career.dimension_engine import score_career_dimensions
    from app.modules.career.schemas import CareerDimensionKey

    high_quality = [
        _fact("placement:mercury:virgo:no_house"),
        _fact("placement:saturn:capricorn:no_house"),
        _fact("balance:element:earth", fact_type="balance", weight=0.8),
    ]
    low_quality = [
        _fact(fact.fact_key, fact_type=fact.fact_type, weight=fact.weight, confidence=0.4) for fact in high_quality
    ]

    high = next(
        result
        for result in score_career_dimensions(high_quality)
        if result.dimension is CareerDimensionKey.ANALYTICAL_THINKING
    )
    low = next(
        result
        for result in score_career_dimensions(low_quality)
        if result.dimension is CareerDimensionKey.ANALYTICAL_THINKING
    )

    assert low.score == high.score
    assert low.confidence == round(high.confidence * 0.4, 4)


def test_dimension_results_build_persistable_scores_and_evidence() -> None:
    from app.modules.career.dimension_engine import score_career_dimensions
    from app.modules.career.dimension_persistence import build_dimension_rows
    from app.modules.career.schemas import CareerDimensionKey

    chart_id = uuid.uuid4()
    career_profile_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    scores, evidence = build_dimension_rows(
        career_profile_id=career_profile_id,
        chart_id=chart_id,
        generation_id=generation_id,
        results=score_career_dimensions(_golden_facts()),
    )

    assert len(scores) == len(CareerDimensionKey)
    assert evidence
    assert all(row.id is not None for row in scores)
    assert all(row.chart_id == chart_id for row in scores)
    assert all(row.generation_id == generation_id for row in scores)
    assert all(row.scoring_version == "career-mvp-1" for row in scores)
    score_ids = {row.id for row in scores}
    assert all(row.dimension_score_id in score_ids for row in evidence)
    assert all(row.source_id is not None for row in evidence)
    evidence_keys = [(row.dimension_score_id, row.source_type, row.source_id) for row in evidence]
    assert len(evidence_keys) == len(set(evidence_keys))


def test_one_natal_fact_matched_by_two_rules_persists_as_a_single_evidence_row() -> None:
    """A fact matched by several rules of one dimension must survive the unique key.

    `career_dimension_evidence` is unique per (dimension_score_id, source_type, source_id).
    `placement:moon:libra:house_7` matches both the Moon rule and the house_7 rule of
    PEOPLE_ORIENTATION, and `placement:saturn:capricorn:house_2` matches the Saturn rule and
    the house_2 rule of STRUCTURE, so the matched rules must aggregate into one row instead of
    aborting the generation with an IntegrityError.
    """

    from app.modules.career.dimension_engine import score_career_dimensions
    from app.modules.career.dimension_persistence import build_dimension_rows
    from app.modules.career.schemas import CareerDimensionKey

    moon_house_seven = _fact("placement:moon:libra:house_7")
    saturn_house_two = _fact("placement:saturn:capricorn:house_2")
    scores, evidence = build_dimension_rows(
        career_profile_id=uuid.uuid4(),
        chart_id=uuid.UUID(int=1),
        generation_id=uuid.uuid4(),
        results=score_career_dimensions([moon_house_seven, saturn_house_two]),
    )

    evidence_keys = [(row.dimension_score_id, row.source_type, row.source_id) for row in evidence]
    assert len(evidence_keys) == len(set(evidence_keys))

    score_ids = {
        CareerDimensionKey.STRUCTURE.value: next(
            row.id for row in scores if row.dimension == CareerDimensionKey.STRUCTURE.value
        ),
        CareerDimensionKey.PEOPLE_ORIENTATION.value: next(
            row.id for row in scores if row.dimension == CareerDimensionKey.PEOPLE_ORIENTATION.value
        ),
    }
    moon_rows = [
        row
        for row in evidence
        if row.source_id == moon_house_seven.id
        and row.dimension_score_id == score_ids[CareerDimensionKey.PEOPLE_ORIENTATION.value]
    ]
    saturn_rows = [
        row
        for row in evidence
        if row.source_id == saturn_house_two.id
        and row.dimension_score_id == score_ids[CareerDimensionKey.STRUCTURE.value]
    ]
    assert len(moon_rows) == 1
    assert len(saturn_rows) == 1
    # Both matching rules keep contributing: 0.10 (placement:moon:) + 0.08 (house_7)
    assert moon_rows[0].payload["weight"] == pytest.approx(0.18)
    # 0.12 (placement:saturn:) + 0.08 (house_2)
    assert saturn_rows[0].payload["weight"] == pytest.approx(0.20)
    assert moon_rows[0].payload["factor_key"] == "placement:moon:libra:house_7"


def test_correlated_family_is_capped_and_evidence_order_is_stable() -> None:
    from app.modules.career.dimension_engine import score_career_dimensions
    from app.modules.career.schemas import CareerDimensionKey

    facts = [_fact(f"aspect:mercury:saturn:conjunction:{index}", fact_type="aspect") for index in range(10)] + [
        _fact("balance:element:earth", fact_type="balance", weight=1.0),
    ]
    result = next(
        item for item in score_career_dimensions(facts) if item.dimension is CareerDimensionKey.ANALYTICAL_THINKING
    )

    assert result.score <= 77.5
    assert [item.factor_key for item in result.evidence] == sorted(
        [item.factor_key for item in result.evidence],
        key=lambda key: (
            -abs(next(e.contribution for e in result.evidence if e.factor_key == key)),
            key,
        ),
    )


def test_missing_houses_are_not_invented_and_engine_has_no_llm_or_socionics_dependency() -> None:
    from app.modules.career.dimension_engine import score_career_dimensions

    results = score_career_dimensions(
        [
            _fact("placement:sun:leo:no_house"),
            _fact("balance:modality:cardinal", fact_type="balance", weight=0.8),
        ]
    )
    evidence_keys = {e.factor_key for result in results for e in result.evidence}
    assert all("house_" not in key for key in evidence_keys)

    root = Path(__file__).resolve().parents[3] / "app" / "modules" / "career"
    source = (root / "dimension_engine.py").read_text(encoding="utf-8") + (root / "factor_catalog.py").read_text(
        encoding="utf-8"
    )
    assert "modules.llm" not in source
    assert "socionics" not in source.lower()
