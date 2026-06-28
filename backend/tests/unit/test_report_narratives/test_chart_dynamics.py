# ruff: noqa: RUF001
"""RED tests for E14 S03 chart dynamics synthesis."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.report_narratives.deep_synthesis import build_deep_natal_synthesis


@pytest.fixture
def report_fixture() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        product="self",
        report_data={
            "profile": {
                "name": "Алексей",
                "birth_date": "1991-08-29",
                "birth_place": "Москва",
                "birth_time_quality": "exact",
            },
            "archetype": {
                "primary": "Наставник",
                "confidence": {"label": "высокая"},
            },
            "socionics": {
                "type": "EIE",
                "type_ru": "ЭИЭ",
                "confidence_label": "средняя",
                "explanation": "Этико-интуитивная выразительность с напряжением между эмоцией и структурой.",
            },
            "chart": {
                "elements": {"fire": 0.35, "earth": 0.25, "air": 0.20, "water": 0.20},
                "modalities": {"cardinal": 0.20, "fixed": 0.45, "mutable": 0.35},
                "planets": [
                    {"name": "Sun", "sign": "Virgo", "house": 9},
                    {"name": "Moon", "sign": "Leo", "house": 8},
                    {"name": "Mercury", "sign": "Aries", "house": 5},
                    {"name": "Venus", "sign": "Libra", "house": 7},
                    {"name": "Mars", "sign": "Cancer", "house": 4},
                    {"name": "Saturn", "sign": "Capricorn", "house": 10},
                ],
                "aspects": [
                    {
                        "planet_a": "Moon",
                        "planet_b": "Mercury",
                        "aspect_type": "trine",
                        "orb": 0.4,
                        "is_applying": True,
                    },
                    {
                        "planet_a": "Moon",
                        "planet_b": "Saturn",
                        "aspect_type": "opposition",
                        "orb": 0.9,
                        "is_applying": True,
                    },
                    {
                        "planet_a": "Venus",
                        "planet_b": "Mars",
                        "aspect_type": "square",
                        "orb": 1.1,
                        "is_applying": True,
                    },
                ],
            },
            "claims": [
                {
                    "claim_id": "strength_expression",
                    "section": "strengths",
                    "message": "Вы умеете заражать идеей.",
                    "basis": [
                        {
                            "rule_id": "sun_virgo_house_9",
                            "feature": "sun_sign_house",
                            "value": "Sun Virgo 9",
                            "contribution": 0.7,
                        }
                    ],
                },
                {
                    "claim_id": "risk_overload",
                    "section": "risks",
                    "message": "Иногда эмоции перегружают речь.",
                    "basis": [
                        {
                            "rule_id": "moon_trine_mercury",
                            "feature": "aspect",
                            "value": "Moon trine Mercury",
                            "contribution": 0.4,
                        }
                    ],
                },
                {
                    "claim_id": "relationships_depth",
                    "section": "relationships",
                    "message": "Вам важна эмоциональная интенсивность и глубина доверия.",
                    "basis": [
                        {
                            "rule_id": "moon_leo_house_8",
                            "feature": "moon_house",
                            "value": "Moon Leo 8",
                            "contribution": 0.5,
                        }
                    ],
                },
            ],
            "quality_warning": None,
        },
    )


def test_build_deep_natal_synthesis_produces_non_generic_chart_dynamics(report_fixture: SimpleNamespace) -> None:
    synthesis = build_deep_natal_synthesis(report_fixture)

    assert len(synthesis.chart_dynamics) >= 3
    assert len(synthesis.contradictions) >= 3
    assert len(synthesis.calibration_hypotheses) >= 5

    dynamic_ids = {item.id for item in synthesis.chart_dynamics}
    assert "chart_dynamic_moon_saturn_regulation" in dynamic_ids
    assert "chart_dynamic_venus_mars_intimacy" in dynamic_ids
    assert "chart_dynamic_identity_depth_axis" in dynamic_ids

    for item in synthesis.chart_dynamics:
        assert item.evidence_ids
        assert item.section_targets
        body = f"{item.title} {item.mechanism} {item.tension} {item.compensation}".lower()
        assert "практич" not in body
        assert "эмоциональ" not in body
        assert "структурн" not in body


def test_contradictions_and_maturity_are_evidence_backed_and_bounded(report_fixture: SimpleNamespace) -> None:
    synthesis = build_deep_natal_synthesis(report_fixture)

    contradiction_ids = {item.id for item in synthesis.contradictions}
    assert "contradiction_moon_saturn_expression_vs_control" in contradiction_ids
    assert "contradiction_venus_mars_closeness_vs_defense" in contradiction_ids

    supported_ids = (
        set(synthesis.evidence_map)
        | {pattern.id for pattern in synthesis.aspect_patterns}
        | {pattern.id for pattern in synthesis.house_axis_patterns}
    )
    for contradiction in synthesis.contradictions:
        assert contradiction.evidence_ids
        assert set(contradiction.evidence_ids) <= supported_ids
        assert "диагноз" not in contradiction.manifestation.lower()
        assert "неизбеж" not in contradiction.mature_expression.lower()

    for level in (
        synthesis.maturity_levels.low,
        synthesis.maturity_levels.medium,
        synthesis.maturity_levels.high,
    ):
        assert level.evidence_ids
        assert set(level.evidence_ids) <= supported_ids
        assert len(level.body) > 40

    calibration_text = " ".join(item.hypothesis for item in synthesis.calibration_hypotheses).lower()
    assert "когда" in calibration_text or "замеча" in calibration_text
