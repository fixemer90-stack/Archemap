"""Provider usage is numeric, request-local evidence, never prompt or credential logging."""

from __future__ import annotations

import asyncio
from typing import Any, cast

import httpx
import pytest
import respx
from pydantic import BaseModel

from app.modules.llm.exceptions import LLMTimeoutError
from app.modules.llm.providers.deepseek import DeepSeekProvider
from app.modules.llm.usage import capture_provider_usage, record_provider_attempt, record_provider_response


class RequestInput(BaseModel):
    scope: str = "synthetic"


class ResponseOutput(BaseModel):
    ok: bool


def response_payload(usage: object) -> dict[str, Any]:
    return {
        "choices": [{"message": {"content": '{"ok":true}'}}],
        "usage": usage,
        "model": "private-provider-field-is-not-usage",
        "request_id": "private-request-id",
    }


@pytest.mark.asyncio
@respx.mock
async def test_success_retains_only_authoritative_numeric_usage() -> None:
    respx.post("https://api.deepseek.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json=response_payload(
                {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                    "prompt_cache_hit_tokens": 60,
                    "prompt_cache_miss_tokens": 40,
                    "secret": "must-not-survive",
                }
            ),
        )
    )
    provider = DeepSeekProvider(api_key="synthetic-not-a-key", model="synthetic", timeout_seconds=2, max_retries=0)
    with capture_provider_usage() as usage:
        result = await provider.generate_structured(
            prompt="private prompt", narrative_input=cast(Any, RequestInput()), schema=ResponseOutput
        )
    assert result.ok
    assert usage.to_payload() == {
        "http_attempts": 1,
        "responses_with_usage": 1,
        "responses_without_usage": 0,
        "prompt_tokens": 100,
        "completion_tokens": 20,
        "total_tokens": 120,
        "prompt_cache_hit_tokens": 60,
        "prompt_cache_miss_tokens": 40,
    }
    assert not any(token in str(usage.to_payload()) for token in ("private", "synthetic", "secret"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw",
    [
        None,
        [],
        {"prompt_tokens": True, "completion_tokens": 2, "total_tokens": 3},
        {"prompt_tokens": -1, "completion_tokens": 2, "total_tokens": 1},
        {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 9},
        {"prompt_tokens": 1, "completion_tokens": "2", "total_tokens": 3},
    ],
)
@respx.mock
async def test_missing_or_malformed_usage_is_unknown_not_fabricated_zero(raw: object) -> None:
    respx.post("https://api.deepseek.com/chat/completions").mock(
        return_value=httpx.Response(200, json=response_payload(raw))
    )
    provider = DeepSeekProvider(api_key="synthetic", model="synthetic", timeout_seconds=2, max_retries=0)
    with capture_provider_usage() as usage:
        await provider.generate_structured(
            prompt="synthetic", narrative_input=cast(Any, RequestInput()), schema=ResponseOutput
        )
    assert usage.to_payload() == {
        "http_attempts": 1,
        "responses_with_usage": 0,
        "responses_without_usage": 1,
    }


@pytest.mark.asyncio
@respx.mock
async def test_concurrent_calls_on_shared_provider_keep_usage_isolated() -> None:
    first_entered = asyncio.Event()
    second_entered = asyncio.Event()

    async def respond(request: httpx.Request) -> httpx.Response:
        import json

        content = json.loads(request.content)["messages"][0]["content"]
        if content == "first":
            first_entered.set()
            await second_entered.wait()
            prompt_tokens = 10
        else:
            await first_entered.wait()
            second_entered.set()
            prompt_tokens = 40
        return httpx.Response(
            200,
            json=response_payload(
                {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": 2,
                    "total_tokens": prompt_tokens + 2,
                }
            ),
        )

    respx.post("https://api.deepseek.com/chat/completions").mock(side_effect=respond)
    provider = DeepSeekProvider(api_key="synthetic", model="synthetic", timeout_seconds=2, max_retries=0)

    async def generate(prompt: str) -> dict[str, int]:
        with capture_provider_usage() as usage:
            await provider.generate_structured(
                prompt=prompt, narrative_input=cast(Any, RequestInput()), schema=ResponseOutput
            )
        return usage.to_payload()

    first, second = await asyncio.gather(generate("first"), generate("second"))
    assert (first["total_tokens"], second["total_tokens"]) == (12, 42)
    assert first["http_attempts"] == second["http_attempts"] == 1


def test_nested_capture_and_exception_restore_previous_context() -> None:
    with capture_provider_usage() as outer:
        record_provider_attempt()
        with pytest.raises(ValueError, match="synthetic"), capture_provider_usage() as inner:
            record_provider_attempt()
            record_provider_response({"usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}})
            raise ValueError("synthetic")
        record_provider_attempt()
    before = outer.to_payload()
    record_provider_attempt()
    assert (
        outer.to_payload()
        == before
        == {
            "http_attempts": 2,
            "responses_with_usage": 0,
            "responses_without_usage": 0,
        }
    )
    assert inner.to_payload()["total_tokens"] == 3
    assert inner.to_payload()["http_attempts"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_transport_failure_records_attempt_but_not_token_usage() -> None:
    respx.post("https://api.deepseek.com/chat/completions").mock(side_effect=httpx.ReadTimeout("synthetic"))
    provider = DeepSeekProvider(api_key="synthetic", model="synthetic", timeout_seconds=2, max_retries=0)
    with capture_provider_usage() as usage, pytest.raises(LLMTimeoutError):
        await provider.generate_structured(
            prompt="synthetic", narrative_input=cast(Any, RequestInput()), schema=ResponseOutput
        )
    assert usage.to_payload() == {
        "http_attempts": 1,
        "responses_with_usage": 0,
        "responses_without_usage": 0,
    }
