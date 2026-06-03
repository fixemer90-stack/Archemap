"""Regression tests for socionics scoring calibration."""

from __future__ import annotations

from datetime import UTC, datetime

from app.chart_engine.chart import build_chart
from app.chart_engine.features import extract_features
from app.chart_engine.socionics import _compute_function_strengths, evaluate_socionics
from app.chart_engine.types import ChartData, HousePosition, PlanetPosition


def _planet(
    name: str,
    sign: str,
    house: int,
    degree: float = 0.0,
    *,
    retrograde: bool = False,
) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=0.0,
        latitude=0.0,
        speed=-1.0 if retrograde else 1.0,
        sign=sign,
        sign_degree=degree,
        house=house,
    )


def _house(number: int, sign: str) -> HousePosition:
    return HousePosition(number=number, longitude=0.0, sign=sign)


def test_retrograde_internalizes_extroverted_functions_without_externalizing_introverted_ones() -> None:
    chart = ChartData(
        birth_datetime=datetime(1990, 1, 1, tzinfo=UTC),
        latitude=0.0,
        longitude=0.0,
        timezone="UTC",
        planets=[_planet("Saturn", "Capricorn", 2, retrograde=True)],
        houses=[_house(i, "Aries") for i in range(1, 13)],
        aspects=[],
    )

    strengths = _compute_function_strengths(chart)

    assert strengths["Ti"] > strengths["Te"]
    assert strengths["Si"] > strengths["Se"]


def test_reference_profile_is_not_overclassified_as_lie_from_retrograde_saturn_te_spillover() -> None:
    chart = build_chart(
        birth_datetime=datetime(1990, 8, 24, 14, 11, tzinfo=UTC),
        latitude=55.7505412,
        longitude=37.6174782,
        timezone_name="Europe/Moscow",
    )

    strengths = _compute_function_strengths(chart)
    results = evaluate_socionics(extract_features(chart), chart)
    lsi_score = next(r.score for r in results if r.type_code == "LSI")
    lie_score = next(r.score for r in results if r.type_code == "LIE")

    assert strengths["Ti"] > strengths["Te"]
    assert strengths["Ti"] > strengths["Ni"]
    assert strengths["Ni"] < 0.85
    assert results[0].type_code == "LSI"
    assert lsi_score > lie_score


def test_leo_eighth_house_ethic_intuitive_profile_classifies_as_eie() -> None:
    chart = build_chart(
        birth_datetime=datetime(1991, 8, 29, 11, 30, tzinfo=UTC),
        latitude=55.7505412,
        longitude=37.6174782,
        timezone_name="Europe/Moscow",
    )

    strengths = _compute_function_strengths(chart)
    results = evaluate_socionics(extract_features(chart), chart)
    top_codes = [result.type_code for result in results[:4]]
    eie_score = next(r.score for r in results if r.type_code == "EIE")
    sli_score = next(r.score for r in results if r.type_code == "SLI")
    lsi_score = next(r.score for r in results if r.type_code == "LSI")

    assert strengths["Fe"] > strengths["Si"]
    assert strengths["Ni"] > strengths["Te"]
    assert results[0].type_code == "EIE"
    assert eie_score > sli_score
    assert eie_score > lsi_score
    assert "SLI" not in top_codes
