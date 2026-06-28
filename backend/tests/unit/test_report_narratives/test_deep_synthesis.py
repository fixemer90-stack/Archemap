"""RED tests for E14 S01 DeepNatalSynthesis contract."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.report_narratives.deep_synthesis import (
    DEEP_NATAL_SYNTHESIS_CONTRACT_VERSION,
    build_deep_natal_synthesis,
    compute_deep_synthesis_hash,
)
from app.modules.report_narratives.schemas import DeepNatalSynthesis


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
                "explanation": "Этико-интуитивная выразительность.",
            },
            "chart": {
                "elements": {"fire": 0.35, "earth": 0.25, "air": 0.20, "water": 0.20},
                "modalities": {"cardinal": 0.20, "fixed": 0.45, "mutable": 0.35},
                "planets": [
                    {"name": "Sun", "sign": "Virgo", "house": 9},
                    {"name": "Moon", "sign": "Leo", "house": 8},
                ],
                "aspects": [
                    {
                        "planet_a": "Moon",
                        "planet_b": "Mercury",
                        "aspect_type": "trine",
                        "orb": 0.5,
                        "is_applying": True,
                    }
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
            ],
            "quality_warning": None,
        },
    )


def test_build_deep_natal_synthesis_creates_evidence_backed_contract(report_fixture: SimpleNamespace) -> None:
    synthesis = build_deep_natal_synthesis(report_fixture)

    assert isinstance(synthesis, DeepNatalSynthesis)
    assert synthesis.contract_version == DEEP_NATAL_SYNTHESIS_CONTRACT_VERSION
    assert synthesis.source_chart_snapshot_id == "chart:unknown"
    assert synthesis.evidence_map
    assert synthesis.ranked_aspects
    assert synthesis.aspect_patterns
    assert synthesis.planet_roles
    assert synthesis.chart_dynamics
    assert synthesis.contradictions
    assert synthesis.maturity_levels.low.evidence_ids
    assert synthesis.calibration_hypotheses

    allowed_ids = set(synthesis.evidence_map)
    assert all(item.evidence_ids for item in synthesis.aspect_patterns)
    assert all(item.evidence_ids for item in synthesis.planet_roles)
    assert all(item.evidence_ids for item in synthesis.chart_dynamics)
    assert all(item.evidence_ids for item in synthesis.contradictions)
    assert set(synthesis.maturity_levels.low.evidence_ids) <= allowed_ids
    assert set(synthesis.maturity_levels.medium.evidence_ids) <= allowed_ids
    assert set(synthesis.maturity_levels.high.evidence_ids) <= allowed_ids


def test_deep_synthesis_hash_is_stable_for_semantically_identical_report_data(
    report_fixture: SimpleNamespace,
) -> None:
    report = report_fixture
    same = deepcopy(report_fixture)
    same.report_data["claims"] = list(reversed(same.report_data["claims"]))

    first = build_deep_natal_synthesis(report)
    second = build_deep_natal_synthesis(same)

    assert compute_deep_synthesis_hash(first) == compute_deep_synthesis_hash(second)


def test_deep_synthesis_hash_changes_when_contract_version_or_chart_changes(
    report_fixture: SimpleNamespace,
) -> None:
    report = report_fixture
    changed = deepcopy(report_fixture)
    changed.report_data["chart"]["planets"][0]["house"] = 10

    base = build_deep_natal_synthesis(report)
    modified = build_deep_natal_synthesis(changed)

    assert compute_deep_synthesis_hash(base) != compute_deep_synthesis_hash(modified)
