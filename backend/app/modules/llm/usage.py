"""Opt-in numeric provider accounting, isolated to one async call context.

This is observational evidence, not a billing receipt or a guarantee about
unobserved/ambiguous provider outcomes. Missing usage is never recorded as zero.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager, contextmanager, suppress
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

from app.config import settings
from app.modules.analytics.costs import Attempt, Outcome, TokenUsage
from app.modules.analytics.usage_evidence import Provider, TransportEvidence, model_ref, record_transport_evidence
from app.modules.llm.http_dispatch import guard_llm_http_request

_TOKEN_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens")
_CACHE_FIELDS = ("prompt_cache_hit_tokens", "prompt_cache_miss_tokens")
_COUNTER_FIELDS = ("http_attempts", "responses_with_usage", "responses_without_usage")
_AGGREGATE_TOKENS_OVERFLOW = "aggregate_tokens_overflow"


def _token_count(value: object) -> bool:
    return type(value) is int and 0 <= value <= 2**63 - 1


def _validated_usage(raw: object) -> dict[str, int] | None:
    if not isinstance(raw, Mapping):
        return None
    if not all(_token_count(raw.get(key)) for key in _TOKEN_FIELDS):
        return None
    values = {key: int(raw[key]) for key in _TOKEN_FIELDS}
    if values["total_tokens"] != values["prompt_tokens"] + values["completion_tokens"]:
        return None
    if all(_token_count(raw.get(key)) for key in _CACHE_FIELDS):
        cache = {key: int(raw[key]) for key in _CACHE_FIELDS}
        if sum(cache.values()) == values["prompt_tokens"]:
            values.update(cache)
    return values


def validated_usage_aggregate(value: object) -> dict[str, int]:
    """Return validated counters and representable totals from retained diagnostics."""
    if not isinstance(value, dict):
        return {}
    keys = set(value)
    counters: set[str] = set(_COUNTER_FIELDS)
    if not counters <= keys or not all(_token_count(number) for number in value.values()):
        return {}
    known = value["responses_with_usage"]
    if known + value["responses_without_usage"] > value["http_attempts"]:
        return {}
    if keys == counters | {_AGGREGATE_TOKENS_OVERFLOW} and known >= 2 and value[_AGGREGATE_TOKENS_OVERFLOW] == 1:
        return {key: value[key] for key in counters}
    expected = set(counters)
    if known:
        expected.update(_TOKEN_FIELDS)
        if not expected <= keys or value["total_tokens"] != value["prompt_tokens"] + value["completion_tokens"]:
            return {}
        if keys.intersection(_CACHE_FIELDS):
            expected.update(_CACHE_FIELDS)
            if (
                not expected <= keys
                or value["prompt_cache_hit_tokens"] + value["prompt_cache_miss_tokens"] != value["prompt_tokens"]
            ):
                return {}
    return {key: value[key] for key in expected} if keys == expected else {}


def _response_usage(payload: object, provider: Provider) -> dict[str, int] | None:
    raw = payload.get("usage") if isinstance(payload, Mapping) else None
    values = _validated_usage(raw)
    if provider == "openrouter" and values is not None and isinstance(raw, Mapping):
        # Honor only OpenRouter's own cache fields (not DeepSeek's at this boundary).
        for key in _CACHE_FIELDS:
            values.pop(key, None)
        details = raw.get("prompt_tokens_details")
        if isinstance(details, Mapping):
            hits = details.get("cached_tokens")
            writes = details.get("cache_write_tokens", 0)
            # Two-bucket cache evidence cannot account for a separate write tariff.
            if type(hits) is int and 0 <= hits <= values["prompt_tokens"] and type(writes) is int and writes == 0:
                values["prompt_cache_hit_tokens"] = hits
                values["prompt_cache_miss_tokens"] = values["prompt_tokens"] - hits
    return values


@dataclass(slots=True)
class ProviderUsageCapture:
    """A separate mutable capture per operation, never shared provider state."""

    _http_attempts: int = 0
    _responses_without_usage: int = 0
    _usage: list[dict[str, int]] = field(default_factory=list)
    _attempts: list[TransportEvidence] = field(default_factory=list)

    @property
    def attempts(self) -> tuple[Attempt, ...]:
        return tuple(item.attempt for item in self._attempts)

    def _response(self, usage: dict[str, int] | None) -> None:
        if usage is None:
            self._responses_without_usage += 1
        else:
            self._usage.append(usage)

    def to_payload(self) -> dict[str, int]:
        payload = {
            "http_attempts": self._http_attempts,
            "responses_with_usage": len(self._usage),
            "responses_without_usage": self._responses_without_usage,
        }
        if self._usage:
            # Nonnegative component/cache sums cannot exceed the total. Keep
            # response counters and attempt facts, but never publish partial sums.
            totals = {key: sum(item[key] for item in self._usage) for key in _TOKEN_FIELDS}
            if not _token_count(totals["total_tokens"]):
                payload[_AGGREGATE_TOKENS_OVERFLOW] = 1
                return payload
            payload.update(totals)
            if all(all(key in item for key in _CACHE_FIELDS) for item in self._usage):
                payload.update({key: sum(item[key] for item in self._usage) for key in _CACHE_FIELDS})
        return payload


_current_capture: ContextVar[ProviderUsageCapture | None] = ContextVar("provider_usage_capture", default=None)


@contextmanager
def capture_provider_usage() -> Iterator[ProviderUsageCapture]:
    """Capture this operation's transport observations without changing output."""
    capture = ProviderUsageCapture()
    token = _current_capture.set(capture)
    try:
        yield capture
    finally:
        _current_capture.reset(token)


def record_provider_attempt() -> None:
    capture = _current_capture.get()
    if capture is not None:
        capture._http_attempts += 1


def record_provider_response(payload: object) -> None:
    capture = _current_capture.get()
    if capture is None:
        return
    raw = payload.get("usage") if isinstance(payload, Mapping) else None
    capture._response(_validated_usage(raw))


@dataclass(slots=True)
class _HTTPAttempt:
    enabled: bool
    capture: ProviderUsageCapture | None
    provider: Provider
    attempt_id: UUID | None = None
    occurred_at: datetime | None = None
    received: bool = False
    accepted: bool = False
    usage: dict[str, int] | None = None

    async def admit(self, request: httpx.Request) -> None:
        await guard_llm_http_request(request)
        if self.enabled or self.capture is not None:
            self.attempt_id = uuid4()
            self.occurred_at = datetime.now(UTC)
            if self.capture is not None:
                self.capture._http_attempts += 1

    def response(self, payload: object) -> None:
        if self.attempt_id is not None:
            self.usage = _response_usage(payload, self.provider)

    def error_response(self, response: httpx.Response) -> None:
        self.received = True
        if self.attempt_id is not None:
            # Non-JSON error body is not usage evidence.
            with suppress(ValueError, RecursionError):
                self.response(response.json())


async def _persist_attempt(evidence: TransportEvidence) -> None:
    """Best-effort analytics only; never commit caller work or change retries."""
    from app.infrastructure.database import engine

    try:
        async with asyncio.timeout(1), engine.begin() as connection:
            await record_transport_evidence(connection, evidence)
    except Exception:
        # Exception diagnostics can contain credentials, SQL parameters or URLs.
        logging.getLogger(__name__).warning("business_provider_usage_persistence_failed")


@asynccontextmanager
async def track_http_attempt(provider: Provider, model: str) -> AsyncIterator[_HTTPAttempt]:
    """A request-local slot admitted only after the existing dispatch guard.

    A known response rejected by HTTP/structured parsing is failed. A transport
    exception after admission but before response is ambiguous, not zero use.
    Cancellation is not swallowed or turned into a retry; capture is still
    updated, but no database I/O is started while a BaseException unwinds.
    """
    tracked = _HTTPAttempt(settings.BUSINESS_MONITORING_ENABLED, _current_capture.get(), provider)
    persist = True
    try:
        yield tracked
    except BaseException as exc:
        persist = isinstance(exc, Exception)
        raise
    finally:
        if tracked.attempt_id is not None and tracked.occurred_at is not None:
            outcome: Outcome = "succeeded" if tracked.accepted else "failed" if tracked.received else "unknown"
            counts = tracked.usage
            usage = (
                TokenUsage(
                    counts["prompt_tokens"],
                    counts["completion_tokens"],
                    counts["total_tokens"],
                    "provider",
                    counts.get("prompt_cache_hit_tokens"),
                )
                if counts is not None
                else None
            )
            evidence = TransportEvidence(
                tracked.occurred_at, provider, model_ref(model), Attempt(tracked.attempt_id, outcome, usage)
            )
            if tracked.capture is not None:
                tracked.capture._attempts.append(evidence)
                # Aggregate each received response, even if HTTP status or the
                # output contract rejected it. No response remains ambiguous.
                if tracked.received:
                    tracked.capture._response(counts)
            if tracked.enabled and persist:
                await _persist_attempt(evidence)
