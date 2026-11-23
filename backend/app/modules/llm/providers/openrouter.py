"""OpenRouter adapter behind the generic LLM provider boundary."""

from __future__ import annotations

import json
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.modules.llm.exceptions import (
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMTimeoutError,
)
from app.modules.llm.usage import track_http_attempt
from app.modules.report_narratives.schemas import NarrativeInput

StructuredSchemaT = TypeVar("StructuredSchemaT", bound=BaseModel)


class OpenRouterProvider:
    """Minimal OpenRouter provider using the OpenAI-compatible HTTP API."""

    supports_staged_pipeline = True

    def __init__(self, *, api_key: str, model: str, timeout_seconds: int, max_retries: int) -> None:
        self._api_key = api_key
        self.model_name = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        request_payload = {
            "model": self.model_name,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": narrative_input.model_dump_json(indent=2)},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with track_http_attempt("openrouter", self.model_name) as tracking:
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout_seconds, event_hooks={"request": [tracking.admit]}
                ) as client:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=request_payload,
                    )
                    tracking.received = True
                    response.raise_for_status()
            except httpx.TimeoutException as exc:
                raise LLMTimeoutError("LLM provider request timed out", code="llm_timeout") from exc
            except httpx.HTTPStatusError as exc:
                tracking.error_response(exc.response)
                raise LLMProviderUnavailableError(
                    f"LLM provider request failed with status {exc.response.status_code}",
                    code="llm_provider_unavailable",
                ) from exc
            except httpx.HTTPError as exc:
                raise LLMProviderUnavailableError(
                    "LLM provider request failed",
                    code="llm_provider_unavailable",
                ) from exc
            response_payload = response.json()
            tracking.response(response_payload)
            parsed = self._parse_response(response_payload, schema)
            tracking.accepted = True
            return parsed

    def _parse_response(self, response_payload: dict[str, Any], schema: type[StructuredSchemaT]) -> StructuredSchemaT:
        try:
            content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMInvalidResponseError(
                "LLM provider response did not contain structured content",
                code="llm_invalid_response",
            ) from exc

        try:
            parsed_content = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMInvalidResponseError(
                "LLM provider returned non-JSON content",
                code="llm_invalid_response",
            ) from exc

        try:
            return schema.model_validate(parsed_content)
        except ValidationError as exc:
            raise LLMInvalidResponseError(
                "LLM provider returned JSON that does not match schema",
                code="llm_invalid_response",
            ) from exc
