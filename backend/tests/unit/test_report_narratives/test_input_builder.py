# ruff: noqa: RUF001
"""Unit tests for NarrativeInput builder, hashing, and cache lookup."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.report_narratives.hash import compute_input_hash
from app.modules.report_narratives.input_builder import build_narrative_input
from app.modules.report_narratives.models import ReportNarrative
from app.modules.report_narratives.prompts import SELF_STORY_PROMPT_VERSION
from app.modules.report_narratives.service import find_cached_narrative


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
                "elements": {
                    "fire": 0.35,
                    "earth": 0.25,
                    "air": 0.20,
                    "water": 0.20,
                },
                "modalities": {
                    "cardinal": 0.20,
                    "fixed": 0.45,
                    "mutable": 0.35,
                },
                "planets": [
                    {
                        "name": "Sun",
                        "sign": "Virgo",
                        "house": 9,
                    },
                    {
                        "name": "Moon",
                        "sign": "Leo",
                        "house": 8,
                    },
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
                {
                    "claim_id": "sexuality_intensity",
                    "section": "sexuality",
                    "message": "Близость раскрывается через доверие и внутреннюю вовлечённость.",
                    "basis": [
                        {
                            "rule_id": "moon_leo_house_8",
                            "feature": "moon_house",
                            "value": "Moon Leo 8",
                            "contribution": 0.6,
                        }
                    ],
                },
                {
                    "claim_id": "development_grounding",
                    "section": "development",
                    "message": "Полезно давать себе паузу перед эмоционально важным разговором.",
                    "basis": [
                        {
                            "rule_id": "moon_trine_mercury",
                            "feature": "aspect",
                            "value": "Moon trine Mercury",
                            "contribution": 0.3,
                        }
                    ],
                },
            ],
            "quality_warning": None,
        },
    )


class TestNarrativeInputBuilder:
    def test_builds_self_narrative_input_and_localizes_chart_labels(self, report_fixture: SimpleNamespace) -> None:
        result = build_narrative_input(report_fixture)

        assert result.product == "self"
        assert result.language == "ru"
        assert result.profile.name == "Алексей"
        assert result.profile.birth_time_quality == "exact"
        assert result.calculation_quality.has_exact_birth_time is True
        assert result.key_facts[0].id == "sun_virgo_house_9"
        assert result.key_facts[0].label == "Солнце в Деве в 9 доме"
        assert result.key_aspects[0].id == "moon_trine_mercury"
        assert result.key_aspects[0].label == "Луна тригон Меркурий"
        assert result.deep_natal_synthesis is not None
        assert result.deep_natal_synthesis.contract_version == "deep_natal_synthesis_v1"
        assert result.deep_natal_synthesis.evidence_map
        assert result.strengths[0].evidence_ids == ["sun_virgo_house_9"]
        assert result.relationship_patterns[0].evidence_ids == ["moon_leo_house_8"]
        assert result.product_boundaries.allowed_sections[-1] == "development"
        assert result.dominants[0].id == "dominant_element_fire"
        assert result.dominants[0].evidence_ids
        assert len(result.inner_mechanism.steps) == 3
        assert result.inner_mechanism.steps[0].evidence_ids
        assert result.house_scenarios[0].id == "house_scenario_sun_9"
        assert result.house_scenarios[0].placement == "Солнце в Деве в 9 доме"
        assert "систем" in result.house_scenarios[0].need.lower()
        assert result.house_scenarios[0].manifestation
        assert result.house_scenarios[0].shadow
        assert result.house_scenarios[0].mature_expression
        assert result.house_scenarios[0].evidence_ids == ["sun_virgo_house_9"]
        assert len(result.contradictions) == 3
        assert result.contradictions[0].mature_expression
        assert len(result.failure_modes) >= 3
        assert result.failure_modes[0].supportive_reframe
        assert result.maturity_levels.high.body
        assert "Virgo" not in result.house_scenarios[0].placement
        assert "Sun" not in result.house_scenarios[0].placement
        assert "Virgo" not in result.key_facts[0].label
        assert "Sun" not in result.key_facts[0].label
        assert "trine" not in result.key_aspects[0].label

    def test_missing_optional_blocks_do_not_break_builder(self, report_fixture: SimpleNamespace) -> None:
        report = deepcopy(report_fixture)
        report.report_data["profile"]["birth_time_quality"] = "unknown"
        report.report_data["chart"] = {"planets": []}
        report.report_data.pop("socionics")
        report.report_data["quality_warning"] = "Время рождения неизвестно"

        result = build_narrative_input(report)

        assert result.calculation_quality.has_exact_birth_time is False
        assert result.calculation_quality.has_known_birth_time is False
        assert result.calculation_quality.warning == "Время рождения неизвестно"
        assert result.key_facts == []
        assert result.key_aspects == []
        assert result.house_scenarios == []
        assert len(result.contradictions) == 3
        assert len(result.failure_modes) >= 3
        assert result.maturity_levels.low.evidence_ids
        assert result.socionics.type == "unknown"
        assert result.socionics.type_ru == "Не определено"

    def test_missing_relationship_claims_get_grounded_chart_fallbacks(self, report_fixture: SimpleNamespace) -> None:
        report = deepcopy(report_fixture)
        report.report_data["claims"] = [
            claim
            for claim in report.report_data["claims"]
            if claim["section"] not in {"relationships", "sexuality"}
        ]
        report.report_data["chart"]["planets"].extend(
            [
                {"name": "Venus", "sign": "Leo", "house": 9},
                {"name": "Mars", "sign": "Taurus", "house": 7},
            ]
        )

        result = build_narrative_input(report)

        assert result.relationship_patterns
        assert result.sexuality_patterns
        assert "диалог" in result.relationship_patterns[0].claim
        assert "границ" in result.sexuality_patterns[0].claim
        assert "mars_taurus_house_7" in result.relationship_patterns[0].evidence_ids
        assert "mars_taurus_house_7" in result.sexuality_patterns[0].evidence_ids


class TestNarrativeInputHash:
    def test_hash_is_stable_for_semantically_identical_input(self, report_fixture: SimpleNamespace) -> None:
        first = build_narrative_input(report_fixture)
        second_report = deepcopy(report_fixture)
        second_report.report_data["claims"] = list(reversed(second_report.report_data["claims"]))
        second = build_narrative_input(second_report)

        assert compute_input_hash(first) == compute_input_hash(second)

    def test_hash_changes_when_product_boundaries_change(self, report_fixture: SimpleNamespace) -> None:
        narrative_input = build_narrative_input(report_fixture)
        modified = narrative_input.model_copy(deep=True)
        modified.product_boundaries.career_policy = "Полностью другой policy"

        assert compute_input_hash(narrative_input) != compute_input_hash(modified)


class TestNarrativeCacheLookup:
    @pytest.mark.asyncio
    async def test_finds_ready_cached_narrative_by_cache_key(self) -> None:
        db = AsyncMock()
        cached = ReportNarrative(
            report_id=uuid4(),
            product="self",
            prompt_version=SELF_STORY_PROMPT_VERSION,
            model_provider="mock",
            model_name="mock-self-v1",
            status="ready",
            content={"title": "Ваш внутренний портрет", "sections": []},
            input_hash="abc123",
        )
        result = MagicMock()
        result.scalar_one_or_none.return_value = cached
        db.execute.return_value = result

        found = await find_cached_narrative(
            db=db,
            report_id=cached.report_id,
            product="self",
            prompt_version=SELF_STORY_PROMPT_VERSION,
            input_hash="abc123",
            model_name="mock-self-v1",
        )

        assert found is cached

    @pytest.mark.asyncio
    async def test_returns_none_when_cache_misses(self) -> None:
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result

        found = await find_cached_narrative(
            db=db,
            report_id=uuid4(),
            product="self",
            prompt_version=SELF_STORY_PROMPT_VERSION,
            input_hash="different",
            model_name="mock-self-v1",
        )

        assert found is None
