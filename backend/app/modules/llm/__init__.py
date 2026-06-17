"""LLM provider abstraction for report narratives."""

from app.modules.llm.exceptions import (
    LLMDisabledError,
    LLMError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMTimeoutError,
)
from app.modules.llm.provider import LLMProvider, get_llm_provider
from app.modules.llm.providers.deepseek import DeepSeekProvider
from app.modules.llm.providers.mock import MockLLMProvider
from app.modules.llm.providers.openrouter import OpenRouterProvider

__all__ = [
    "DeepSeekProvider",
    "LLMDisabledError",
    "LLMError",
    "LLMInvalidResponseError",
    "LLMProvider",
    "LLMProviderUnavailableError",
    "LLMTimeoutError",
    "MockLLMProvider",
    "OpenRouterProvider",
    "get_llm_provider",
]
