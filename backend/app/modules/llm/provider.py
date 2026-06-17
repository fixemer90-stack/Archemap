"""Generic LLM provider boundary and provider factory."""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.config import Settings, settings
from app.modules.llm.exceptions import LLMDisabledError, LLMProviderUnavailableError
from app.modules.llm.providers.deepseek import DeepSeekProvider
from app.modules.llm.providers.mock import MockLLMProvider
from app.modules.llm.providers.openrouter import OpenRouterProvider
from app.modules.report_narratives.schemas import NarrativeInput

StructuredSchemaT = TypeVar("StructuredSchemaT", bound=BaseModel)


class LLMProvider(Protocol):
    """Provider contract for structured narrative generation."""

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        """Generate structured JSON and validate it against the given schema."""


class DisabledLLMProvider:
    """Controlled provider returned when the LLM layer is disabled."""

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        del prompt
        del narrative_input
        del schema
        raise LLMDisabledError("LLM narrative generation is disabled", code="llm_disabled")


def get_llm_provider(app_settings: Settings | None = None) -> LLMProvider:
    """Resolve the configured provider implementation."""
    current_settings = app_settings or settings

    if not current_settings.LLM_ENABLED:
        return DisabledLLMProvider()

    if current_settings.LLM_PROVIDER == "mock":
        return MockLLMProvider()

    if current_settings.LLM_PROVIDER == "openrouter":
        if not current_settings.LLM_API_KEY:
            raise LLMProviderUnavailableError(
                "LLM API key is required for openrouter provider",
                code="llm_provider_unavailable",
            )
        return OpenRouterProvider(
            api_key=current_settings.LLM_API_KEY,
            model=current_settings.LLM_MODEL,
            timeout_seconds=current_settings.LLM_TIMEOUT_SECONDS,
            max_retries=current_settings.LLM_MAX_RETRIES,
        )

    if current_settings.LLM_PROVIDER == "deepseek":
        if not current_settings.LLM_API_KEY:
            raise LLMProviderUnavailableError(
                "LLM API key is required for deepseek provider",
                code="llm_provider_unavailable",
            )
        return DeepSeekProvider(
            api_key=current_settings.LLM_API_KEY,
            model=current_settings.LLM_MODEL,
            timeout_seconds=current_settings.LLM_TIMEOUT_SECONDS,
            max_retries=current_settings.LLM_MAX_RETRIES,
        )

    raise LLMProviderUnavailableError(
        f"Unsupported LLM provider: {current_settings.LLM_PROVIDER}",
        code="llm_provider_unavailable",
    )
