# ruff: noqa: RUF001
"""Unit tests for report narrative prompt contracts."""

from __future__ import annotations

from app.modules.report_narratives.prompts import (
    SELF_STORY_PROMPT_VERSION,
    build_self_story_prompt,
    load_prompt_template,
)
from app.modules.report_narratives.schemas import NarrativeInput


def make_narrative_input() -> NarrativeInput:
    """Create a valid NarrativeInput payload for prompt tests."""
    return NarrativeInput.model_validate(
        {
            "product": "self",
            "language": "ru",
            "profile": {
                "name": "Алексей",
                "birth_date": "1991-08-29",
                "birth_time_quality": "exact",
                "birth_place": "Москва",
            },
            "calculation_quality": {
                "has_exact_birth_time": True,
                "has_known_birth_time": True,
                "quality_label": "Высокая точность времени рождения",
                "warning": None,
            },
            "key_facts": [
                {
                    "id": "mercury_venus_jupiter_leo_8",
                    "label": "Меркурий, Венера и Юпитер во Льве в 8 доме",
                    "meaning": "Выразительное мышление и эмоциональное влияние.",
                }
            ],
            "key_aspects": [
                {
                    "id": "moon_trine_mercury",
                    "label": "Луна тригон Меркурий",
                    "orb": "0°50′",
                    "meaning": "Связь эмоций и речи.",
                }
            ],
            "dominants": [
                {
                    "id": "dominant_fire",
                    "title": "Доминирующая стихия: Огонь",
                    "body": "Огонь задаёт способ быстро включаться через инициативу и выразительность.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                }
            ],
            "inner_mechanism": {
                "title": "Внутренний механизм личности",
                "summary": "Паттерн разворачивается от импульса к выражению и затем к осмыслению реакции среды.",
                "steps": [
                    {
                        "id": "mechanism_notice",
                        "title": "Сначала вы считываете эмоциональный фон",
                        "body": "Вы быстро замечаете настроение и скрытый смысл ситуации.",
                        "evidence_ids": ["moon_trine_mercury"],
                    },
                    {
                        "id": "mechanism_express",
                        "title": "Затем формулируете образно и заразительно",
                        "body": "Смысл становится заметным через речь, интонацию и образ.",
                        "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                    },
                    {
                        "id": "mechanism_integrate",
                        "title": "После этого ищете форму для переживания",
                        "body": (
                            "Внутреннее напряжение легче выдерживать, когда оно названо и собрано в понятную историю."
                        ),
                        "evidence_ids": ["moon_trine_mercury"],
                    },
                ],
            },
            "house_scenarios": [
                {
                    "id": "house_scenario_sun_9",
                    "title": "Солнце в 9 доме",
                    "placement": "Солнце в Деве в 9 доме",
                    "need": "Иметь собственную систему смысла.",
                    "manifestation": "Вы ищете методологии и объяснения.",
                    "shadow": "Можно откладывать действие ради идеальной системы.",
                    "mature_expression": "Зрелая форма — применять знание в выборе.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                }
            ],
            "socionics": {
                "type": "EIE",
                "type_ru": "ЭИЭ",
                "confidence_label": "средняя",
                "explanation": "Этико-интуитивная выразительность.",
            },
            "archetype": {
                "primary": "Наставник",
                "confidence_label": "высокая",
                "explanation": "Склонность собирать людей вокруг смысла.",
            },
            "strengths": [
                {
                    "id": "strength_expression",
                    "claim": "Вы умеете заражать идеей.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
                }
            ],
            "risks": [
                {
                    "id": "risk_overload",
                    "claim": "Иногда эмоции перегружают речь.",
                    "evidence_ids": ["moon_trine_mercury"],
                }
            ],
            "relationship_patterns": [
                {
                    "id": "relationships_depth",
                    "claim": "Вам важна эмоциональная интенсивность и глубина доверия.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                }
            ],
            "sexuality_patterns": [
                {
                    "id": "sexuality_intensity",
                    "claim": "Близость раскрывается через доверие и внутреннюю вовлечённость.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                }
            ],
            "development_recommendations": [
                {
                    "id": "development_grounding",
                    "claim": "Полезно давать себе паузу перед эмоционально важным разговором.",
                    "evidence_ids": ["moon_trine_mercury"],
                }
            ],
            "product_boundaries": {
                "career_policy": "В Self-отчёте карьеру затрагивать кратко и завершать CTA на Career.",
                "allowed_sections": [
                    "main_formula",
                    "world_perception",
                    "emotions_and_communication",
                    "strengths",
                    "vulnerabilities",
                    "relationships",
                    "sexuality",
                    "development",
                ],
            },
        }
    )


class TestPromptTemplate:
    def test_version_constant_is_stable(self) -> None:
        assert SELF_STORY_PROMPT_VERSION == "self_story_v3"

    def test_template_contains_required_guardrails(self) -> None:
        template = load_prompt_template(SELF_STORY_PROMPT_VERSION)

        assert "не рассчитываешь астрологию" in template
        assert "не добавляй новые факты" in template
        assert "JSON" in template
        assert "SelfNarrative" in template
        assert "Career CTA обязателен" in template
        assert "не давай список профессий" in template
        assert "не описывай сексуальность графично" in template
        assert "только для взрослых пользователей" in template
        assert "house_scenarios" in template
        assert "потребность, жизненное проявление, тень/риск и зрелую форму" in template
        assert "self_story_v3" in template


class TestBuildSelfStoryPrompt:
    def test_builder_embeds_serialized_narrative_input(self) -> None:
        prompt = build_self_story_prompt(make_narrative_input())

        assert '"product": "self"' in prompt
        assert '"name": "Алексей"' in prompt
        assert '"career_policy": "В Self-отчёте карьеру затрагивать кратко и завершать CTA на Career."' in prompt
        assert '"house_scenarios": [' in prompt

    def test_builder_keeps_required_output_and_safety_rules(self) -> None:
        prompt = build_self_story_prompt(make_narrative_input())

        assert "Верни только JSON-объект без Markdown" in prompt
        assert "main_formula" in prompt
        assert "sexuality" in prompt
        assert "не ставь диагнозы" in prompt
        assert "без фатализма" in prompt
