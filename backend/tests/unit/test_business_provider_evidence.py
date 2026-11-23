"""S09 transport evidence is per HTTP request, never per artifact or raw payload."""

import asyncio
from typing import Any

import httpx
import pytest
import respx
from pydantic import BaseModel

from app.config import settings
from app.modules.analytics.usage_evidence import TransportEvidence
from app.modules.llm.exceptions import LLMInvalidResponseError, LLMProviderUnavailableError
from app.modules.llm.providers.deepseek import DeepSeekProvider
from app.modules.llm.providers.openrouter import OpenRouterProvider
from app.modules.llm.usage import (
    capture_provider_usage,
    record_provider_attempt,
    record_provider_response,
    track_http_attempt,
    validated_usage_aggregate,
)


class _Input(BaseModel):
    secret: str = "private input secret"


class _Output(BaseModel):
    ok: bool


@pytest.mark.parametrize("extra", [0, 1], ids=["int64_max", "int64_overflow"])
def test_aggregate_token_limit_preserves_counters_and_never_returns_partial_totals(extra: int) -> None:
    limit = 2**63 - 1
    counters = {"http_attempts": 2, "responses_with_usage": 2, "responses_without_usage": 0}
    with capture_provider_usage() as captured:
        for prompt, completion in ((limit - 5, 2), (2, 1 + extra)):
            record_provider_attempt()
            record_provider_response(
                {
                    "usage": {
                        "prompt_tokens": prompt,
                        "completion_tokens": completion,
                        "total_tokens": prompt + completion,
                        "prompt_cache_hit_tokens": prompt,
                        "prompt_cache_miss_tokens": 0,
                    }
                }
            )
    payload = captured.to_payload()
    if extra:
        assert payload == counters | {"aggregate_tokens_overflow": 1}
        assert validated_usage_aggregate(payload) == counters
    else:
        assert payload == counters | {
            "prompt_tokens": limit - 3,
            "completion_tokens": 3,
            "total_tokens": limit,
            "prompt_cache_hit_tokens": limit - 3,
            "prompt_cache_miss_tokens": 0,
        }
        assert validated_usage_aggregate(payload) == payload


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"aggregate_tokens_overflow": True},
        {"aggregate_tokens_overflow": 2},
        {"aggregate_tokens_overflow": 1, "responses_with_usage": 1},
        {"aggregate_tokens_overflow": 1, "prompt_cache_hit_tokens": 0},
        {"aggregate_tokens_overflow": 1, "prompt_tokens": 1, "completion_tokens": 0, "total_tokens": 1},
    ],
)
def test_aggregate_rejects_malformed_overflow_diagnostics(fields: dict[str, int]) -> None:
    counters = {"http_attempts": 2, "responses_with_usage": 2, "responses_without_usage": 0}
    assert validated_usage_aggregate(counters | fields) == {}


@pytest.mark.asyncio
@respx.mock
async def test_capture_keeps_retry_identity_and_failed_response_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", False)
    monkeypatch.setattr("app.modules.llm.providers.deepseek.asyncio.sleep", no_sleep)
    route = respx.post("https://api.deepseek.com/chat/completions").mock(
        side_effect=[
            httpx.Response(503, json={"usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}}),
            httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}], "secret": "private output"}),
        ]
    )
    provider = DeepSeekProvider(api_key="private key", model="private model", timeout_seconds=2, max_retries=1)
    request: Any = _Input()
    with capture_provider_usage() as captured, pytest.raises(LLMInvalidResponseError):
        await provider.generate_structured(prompt="private prompt", narrative_input=request, schema=_Output)
    assert route.call_count == 2
    first, second = captured.attempts
    assert first.attempt_id != second.attempt_id
    assert (first.outcome, second.outcome) == ("failed", "failed")
    assert first.usage is not None and first.usage.total_tokens == 3
    assert second.usage is None
    assert "private" not in repr(captured.attempts)
    assert captured.to_payload() == {
        "http_attempts": 2,
        "responses_with_usage": 1,
        "responses_without_usage": 1,
        "prompt_tokens": 1,
        "completion_tokens": 2,
        "total_tokens": 3,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("body", ["known", "invalid", "non-json"])
@respx.mock
async def test_openrouter_rejected_response_capture(body: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", False)
    counts = {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}
    response = (
        httpx.Response(503, text="not json")
        if body == "non-json"
        else httpx.Response(503, json={"usage": counts if body == "known" else counts | {"total_tokens": True}})
    )
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(return_value=response)
    provider = OpenRouterProvider(api_key="synthetic", model="synthetic", timeout_seconds=2, max_retries=0)
    request: Any = _Input()
    with capture_provider_usage() as captured, pytest.raises(LLMProviderUnavailableError):
        await provider.generate_structured(prompt="private", narrative_input=request, schema=_Output)
    (attempt,) = captured.attempts
    assert attempt.outcome == "failed"
    assert (attempt.usage is not None) is (body == "known")
    assert captured.to_payload() == (
        {"http_attempts": 1, "responses_with_usage": 1, "responses_without_usage": 0} | counts
        if body == "known"
        else {"http_attempts": 1, "responses_with_usage": 0, "responses_without_usage": 1}
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("writes", [0, 2, True])
@respx.mock
async def test_openrouter_reports_valid_cached_usage(writes: int | bool) -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"ok":true}'}}],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 2,
                    "total_tokens": 5,
                    "prompt_tokens_details": {"cached_tokens": 2, "cache_write_tokens": writes},
                },
            },
        )
    )
    provider = OpenRouterProvider(api_key="private key", model="private model", timeout_seconds=2, max_retries=0)
    request: Any = _Input()
    with capture_provider_usage() as captured:
        assert (await provider.generate_structured(prompt="private", narrative_input=request, schema=_Output)).ok
    (attempt,) = captured.attempts
    assert attempt.outcome == "succeeded"
    assert attempt.usage is not None
    if type(writes) is int and writes == 0:
        assert attempt.usage.cache_hit_tokens == 2
        assert captured.to_payload()["prompt_cache_miss_tokens"] == 1
    else:
        assert attempt.usage.cache_hit_tokens is None
        assert "prompt_cache_miss_tokens" not in captured.to_payload()


@pytest.mark.asyncio
async def test_request_guard_and_cancellation_do_not_publish_false_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    persisted: list[TransportEvidence] = []

    async def persist(evidence: TransportEvidence) -> None:
        persisted.append(evidence)

    async def reject(_: httpx.Request) -> None:
        raise RuntimeError("dispatch guard")

    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    monkeypatch.setattr("app.modules.llm.usage._persist_attempt", persist)
    request = httpx.Request("POST", "https://never-sent.invalid/")
    with monkeypatch.context() as guard:
        guard.setattr("app.modules.llm.usage.guard_llm_http_request", reject)
        with capture_provider_usage() as denied, pytest.raises(RuntimeError, match="dispatch guard"):
            async with track_http_attempt("deepseek", "synthetic") as tracked:
                await tracked.admit(request)
    assert denied.attempts == ()
    with capture_provider_usage() as cancelled, pytest.raises(asyncio.CancelledError):
        async with track_http_attempt("deepseek", "synthetic") as tracked:
            await tracked.admit(request)
            raise asyncio.CancelledError
    (attempt,) = cancelled.attempts
    assert attempt.outcome == "unknown" and attempt.usage is None
    assert cancelled.to_payload() == {"http_attempts": 1, "responses_with_usage": 0, "responses_without_usage": 0}
    assert not persisted


@pytest.mark.asyncio
@respx.mock
async def test_analytics_db_failure_does_not_change_provider_result(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class UnavailableDatabase:
        def begin(self) -> None:
            raise RuntimeError("private database failure")

    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    monkeypatch.setattr("app.infrastructure.database.engine", UnavailableDatabase())
    respx.post("https://api.deepseek.com/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": '{"ok":true}'}}]})
    )
    provider = DeepSeekProvider(api_key="synthetic", model="synthetic", timeout_seconds=2, max_retries=0)
    request: Any = _Input()
    assert (await provider.generate_structured(prompt="private", narrative_input=request, schema=_Output)).ok
    assert "business_provider_usage_persistence_failed" in caplog.text
    assert "private database failure" not in caplog.text
