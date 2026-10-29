"""Opt-in numeric provider accounting, isolated to one async call context.

This is observational evidence, not a billing receipt or a guarantee about
unobserved/ambiguous provider outcomes. Missing usage is never recorded as zero.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

_TOKEN_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens")
_CACHE_FIELDS = ("prompt_cache_hit_tokens", "prompt_cache_miss_tokens")


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


@dataclass(slots=True)
class ProviderUsageCapture:
    """A separate mutable capture per operation, never shared provider state."""

    _http_attempts: int = 0
    _responses_without_usage: int = 0
    _usage: list[dict[str, int]] = field(default_factory=list)

    def to_payload(self) -> dict[str, int]:
        payload = {
            "http_attempts": self._http_attempts,
            "responses_with_usage": len(self._usage),
            "responses_without_usage": self._responses_without_usage,
        }
        if self._usage:
            payload.update({key: sum(item[key] for item in self._usage) for key in _TOKEN_FIELDS})
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
    usage = _validated_usage(raw)
    if usage is None:
        capture._responses_without_usage += 1
    else:
        capture._usage.append(usage)
