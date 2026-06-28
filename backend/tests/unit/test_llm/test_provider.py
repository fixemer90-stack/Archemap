# ruff: noqa: RUF001
"""Unit tests for the LLM provider abstraction."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.modules.llm.exceptions import LLMDisabledError, LLMProviderUnavailableError
from app.modules.llm.provider import get_llm_provider
from app.modules.llm.providers.deepseek import DeepSeekProvider, _normalize_self_narrative_shape
from app.modules.llm.providers.openrouter import OpenRouterProvider
from app.modules.report_narratives.schemas import NarrativeInput, SelfNarrative


def make_narrative_input() -> NarrativeInput:
    """Create a valid NarrativeInput payload for provider tests."""
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
                    "id": "house_8_focus",
                    "title": "Сценарий 8 дома",
                    "placement": "Лев в 8 доме",
                    "need": "Проживать интенсивность через доверие и честность",
                    "manifestation": "Вы углубляете контакт, когда чувствуете эмоциональную включённость.",
                    "shadow": "При перегрузе можете драматизировать или закрываться.",
                    "mature_expression": "Глубина становится ресурсом, когда есть ритм и границы.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                    "evidence_notes": [
                        {
                            "claim": "Интенсивность включается через доверительный контакт.",
                            "fact_ids": ["mercury_venus_jupiter_leo_8"],
                        }
                    ],
                }
            ],
            "calibration_questions": [
                {
                    "id": "cq_1",
                    "question": "Замечаете ли вы эмоциональный фон до того, как включитесь в разговор?",
                    "evidence_ids": ["moon_trine_mercury"],
                    "answer_type": "yes_no",
                },
                {
                    "id": "cq_2",
                    "question": "Насколько важно вам найти точную формулировку переживания?",
                    "evidence_ids": ["moon_trine_mercury"],
                    "answer_type": "scale_1_5",
                },
                {
                    "id": "cq_3",
                    "question": "Бывает ли, что сильные эмоции сначала усиливают выразительность, а потом истощают?",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                    "answer_type": "yes_no",
                },
                {
                    "id": "cq_4",
                    "question": "Что помогает вам проживать интенсивные разговоры без перегруза?",
                    "evidence_ids": ["moon_trine_mercury"],
                    "answer_type": "free_text",
                },
                {
                    "id": "cq_5",
                    "question": "Чувствуете ли вы потребность в глубоком доверии перед настоящей близостью?",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                    "answer_type": "yes_no",
                },
            ],
            "contradictions": [
                {
                    "id": "contr_1",
                    "title": "Яркость и уязвимость",
                    "tension": "Хочется проявляться ярко, но не потерять внутреннюю безопасность.",
                    "manifestation": "Вы то усиливаете выражение, то резко отступаете.",
                    "mature_expression": "Яркость работает лучше, когда у неё есть контейнер и границы.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
                    "evidence_notes": [
                        {
                            "claim": "Выразительность и чувствительность включаются одновременно.",
                            "fact_ids": ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
                        }
                    ],
                },
                {
                    "id": "contr_2",
                    "title": "Импульс и осмысление",
                    "tension": "Сначала хочется ответить сразу, но потом нужно осмыслить впечатление.",
                    "manifestation": "После сильного контакта может понадобиться откат и тишина.",
                    "mature_expression": "Ритм пауза → формулировка делает контакт устойчивее.",
                    "evidence_ids": ["moon_trine_mercury"],
                    "evidence_notes": [],
                },
                {
                    "id": "contr_3",
                    "title": "Близость и контроль",
                    "tension": "Есть тяга к глубине, но и настороженность к потере контроля.",
                    "manifestation": "Вы раскрываетесь только там, где чувствуете безопасный контур.",
                    "mature_expression": "Контроль ослабевает, когда доверие строится постепенно.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                    "evidence_notes": [],
                },
            ],
            "failure_modes": [
                {
                    "id": "fm_1",
                    "title": "Эмоциональный перегрев",
                    "trigger": "Слишком интенсивный обмен без паузы.",
                    "manifestation": "Речь ускоряется, а точность падает.",
                    "supportive_reframe": "Лучше остановиться и вернуться к сути после короткой паузы.",
                    "evidence_ids": ["moon_trine_mercury"],
                    "evidence_notes": [],
                },
                {
                    "id": "fm_2",
                    "title": "Драматизация контакта",
                    "trigger": "Когда ставка на отношения кажется слишком высокой.",
                    "manifestation": "Мелкий сигнал воспринимается как большой смысловой поворот.",
                    "supportive_reframe": "Полезно сначала проверить факты, а потом уже строить интерпретацию.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                    "evidence_notes": [],
                },
                {
                    "id": "fm_3",
                    "title": "Уход в молчание",
                    "trigger": "После перегруза или ощущения непонятости.",
                    "manifestation": "Контакт резко обрывается, хотя потребность в связи остаётся.",
                    "supportive_reframe": "Можно не исчезать полностью, а назвать своё состояние простыми словами.",
                    "evidence_ids": ["moon_trine_mercury"],
                    "evidence_notes": [],
                },
            ],
            "maturity_levels": {
                "low": {
                    "title": "Низкая зрелость",
                    "body": "Эмоции ведут форму, а не наоборот, поэтому контакт часто перегревается.",
                    "evidence_ids": ["moon_trine_mercury"],
                    "evidence_notes": [],
                },
                "medium": {
                    "title": "Средняя зрелость",
                    "body": "Вы уже умеете замечать перегруз и иногда останавливать его до срыва.",
                    "evidence_ids": ["moon_trine_mercury"],
                    "evidence_notes": [],
                },
                "high": {
                    "title": "Высокая зрелость",
                    "body": "Вы соединяете глубину чувств и ясность формулировки без потери контакта.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
                    "evidence_notes": [],
                },
            },
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


class TestMockProvider:
    async def test_mock_provider_returns_valid_self_narrative(self) -> None:
        provider = get_llm_provider(
            Settings(
                LLM_ENABLED=True,
                LLM_PROVIDER="mock",
                LLM_MODEL="mock-self-v1",
                LLM_API_KEY="",
                LLM_TIMEOUT_SECONDS=12,
                LLM_MAX_RETRIES=0,
            )
        )

        result = await provider.generate_structured(
            prompt="self_story_v1",
            narrative_input=make_narrative_input(),
            schema=SelfNarrative,
        )

        assert isinstance(result, SelfNarrative)
        assert result.hero.id == "hero"
        assert result.sections[0].id == "main_formula"
        assert result.career_cta.button_label == "Открыть Career"


class TestDeepSeekNormalization:
    def test_fills_missing_career_cta_body_with_safe_default(self) -> None:
        normalized = _normalize_self_narrative_shape(
            {
                "title": "Ваш разбор",
                "hero": {"id": "hero", "title": "Hero", "body": "Text"},
                "sections": [
                    {
                        "id": "main_formula",
                        "title": "Главная формула",
                        "body": ["Body line 1", "Body line 2"],
                    }
                ],
                "career_cta": {
                    "title": "Career",
                    "body": "",
                    "button_label": "",
                },
                "final_summary": "Итог",
            }
        )

        assert normalized["sections"][0]["body"] == "Body line 1\n\nBody line 2"
        assert normalized["career_cta"]["body"]
        assert normalized["career_cta"]["button_label"] == "Перейти в Career"

    def test_normalizes_final_summary_object_to_body_text(self) -> None:
        normalized = _normalize_self_narrative_shape(
            {
                "title": "Ваш разбор",
                "hero": {"id": "hero", "title": "Hero", "body": "Text"},
                "sections": [
                    {
                        "id": "main_formula",
                        "title": "Главная формула",
                        "body": "Body",
                    }
                ],
                "career_cta": "Career",
                "final_summary": {
                    "title": "Резюме",
                    "body": "Вы строите себя через отношения и осмысленный порядок.",
                },
            }
        )

        assert normalized["final_summary"] == "Вы строите себя через отношения и осмысленный порядок."

    def test_normalizes_sections_object_to_section_list(self) -> None:
        normalized = _normalize_self_narrative_shape(
            {
                "title": "Ваш разбор",
                "hero": {"id": "hero", "title": "Hero", "body": "Text"},
                "sections": {
                    "main_formula": {
                        "title": "Главная формула",
                        "body": "Body",
                    },
                    "world_perception": "World body",
                },
                "career_cta": "Career",
                "final_summary": "Итог",
            }
        )

        assert normalized["sections"] == [
            {
                "id": "main_formula",
                "title": "Главная формула",
                "body": "Body",
                "bullets": [],
                "evidence_notes": [],
            },
            {
                "id": "world_perception",
                "title": "Как вы воспринимаете мир",
                "body": "World body",
                "bullets": [],
                "evidence_notes": [],
            },
        ]


class TestProviderFactory:
    async def test_disabled_flag_returns_controlled_provider(self) -> None:
        provider = get_llm_provider(
            Settings(
                LLM_ENABLED=False,
                LLM_PROVIDER="openrouter",
                LLM_MODEL="openai/gpt-4.1-mini",
                LLM_API_KEY="super-secret-key",
                LLM_TIMEOUT_SECONDS=30,
                LLM_MAX_RETRIES=2,
            )
        )

        with pytest.raises(LLMDisabledError, match="disabled"):
            await provider.generate_structured(
                prompt="self_story_v1",
                narrative_input=make_narrative_input(),
                schema=SelfNarrative,
            )

    def test_openrouter_factory_reads_timeout_retry_and_model_from_settings(self) -> None:
        provider = get_llm_provider(
            Settings(
                LLM_ENABLED=True,
                LLM_PROVIDER="openrouter",
                LLM_MODEL="openai/gpt-4.1-mini",
                LLM_API_KEY="test-key",
                LLM_TIMEOUT_SECONDS=17,
                LLM_MAX_RETRIES=4,
            )
        )

        assert isinstance(provider, OpenRouterProvider)
        assert provider.model_name == "openai/gpt-4.1-mini"
        assert provider.timeout_seconds == 17
        assert provider.max_retries == 4

    def test_openrouter_requires_api_key(self) -> None:
        with pytest.raises(LLMProviderUnavailableError, match="API key"):
            get_llm_provider(
                Settings(
                    LLM_ENABLED=True,
                    LLM_PROVIDER="openrouter",
                    LLM_MODEL="openai/gpt-4.1-mini",
                    LLM_API_KEY="",
                    LLM_TIMEOUT_SECONDS=30,
                    LLM_MAX_RETRIES=2,
                )
            )

    def test_deepseek_factory_reads_timeout_retry_and_model_from_settings(self) -> None:
        provider = get_llm_provider(
            Settings(
                LLM_ENABLED=True,
                LLM_PROVIDER="deepseek",
                LLM_MODEL="deepseek-v4-flash",
                LLM_API_KEY="test-key",
                LLM_TIMEOUT_SECONDS=19,
                LLM_MAX_RETRIES=3,
            )
        )

        assert isinstance(provider, DeepSeekProvider)
        assert provider.model_name == "deepseek-v4-flash"
        assert provider.timeout_seconds == 19
        assert provider.max_retries == 3

    def test_deepseek_requires_api_key(self) -> None:
        with pytest.raises(LLMProviderUnavailableError, match="API key"):
            get_llm_provider(
                Settings(
                    LLM_ENABLED=True,
                    LLM_PROVIDER="deepseek",
                    LLM_MODEL="deepseek-v4-flash",
                    LLM_API_KEY="",
                    LLM_TIMEOUT_SECONDS=30,
                    LLM_MAX_RETRIES=2,
                )
            )

    def test_settings_expose_llm_fields(self) -> None:
        settings = Settings(
            LLM_ENABLED=True,
            LLM_PROVIDER="mock",
            LLM_MODEL="mock-self-v1",
            LLM_API_KEY="",
            LLM_TIMEOUT_SECONDS=17,
            LLM_MAX_RETRIES=4,
        )

        assert settings.LLM_ENABLED is True
        assert settings.LLM_PROVIDER == "mock"
        assert settings.LLM_MODEL == "mock-self-v1"
        assert settings.LLM_TIMEOUT_SECONDS == 17
        assert settings.LLM_MAX_RETRIES == 4
