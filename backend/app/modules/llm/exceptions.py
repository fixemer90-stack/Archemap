"""Exceptions raised by the LLM provider layer."""

from __future__ import annotations

from app.core.exceptions import ArchemapError


class LLMError(ArchemapError):
    """Base exception for LLM provider failures."""


class LLMDisabledError(LLMError):
    """LLM generation is disabled by configuration."""


class LLMTimeoutError(LLMError):
    """LLM request timed out."""


class LLMProviderUnavailableError(LLMError):
    """The configured LLM provider is unavailable."""


class LLMInvalidResponseError(LLMError):
    """The provider returned an invalid or unparseable response."""
