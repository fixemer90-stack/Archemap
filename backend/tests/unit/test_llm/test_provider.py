# ruff: noqa: RUF001
"""Unit tests for the LLM provider abstraction."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.modules.llm.exceptions import LLMDisabledError, LLMProviderUnavailableError
from app.modules.llm.provider import get_llm_provider
from app.modules.llm.providers.deepseek import DeepSeekProvider
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
