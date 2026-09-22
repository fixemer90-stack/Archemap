"""Low-cardinality Career metrics and correlation context."""

from __future__ import annotations

import re
from collections.abc import Mapping
from math import ceil
from typing import Protocol, cast

import structlog
from opentelemetry import metrics, trace

_ALLOWED_STAGES = {"access", "questionnaire", "deterministic", "narrative", "pdf"}
_ALLOWED_OUTCOMES = {
    "allowed",
    "denied",
    "draft_saved",
    "completed",
    "ready",
    "failed",
    "partial_failure",
    "validation_rejected",
    "retried",
    "stuck",
    "version_observed",
}
_ALLOWED_OPERATIONS = {"create", "regenerate", "read", "complete", "save", "render", "scan"}
_ALLOWED_ERROR_CODES = {
    "career_input_failure",
    "career_provider_failure",
    "career_validation_failure",
    "career_queue_unavailable",
    "career_stuck_generation",
}
_VERSION_RE = re.compile(r"^career-[a-z0-9][a-z0-9.-]{0,79}$")
_ALLOWED_SECTIONS = {
    "professional_summary",
    "work_style",
    "strengths",
    "decision_making",
    "leadership_and_influence",
    "optimal_environment",
    "risk_conditions",
    "career_archetypes",
    "role_families",
    "career_paths",
}


class _Counter(Protocol):
    def add(self, amount: float, attributes: Mapping[str, str] | None = None) -> None: ...


class _Histogram(Protocol):
    def record(self, amount: float, attributes: Mapping[str, str] | None = None) -> None: ...


class CareerTelemetry:
    def __init__(
        self,
        *,
        counter: _Counter,
        duration: _Histogram,
        token_counter: _Counter | None = None,
        cost: _Histogram | None = None,
    ) -> None:
        self.counter = counter
        self.duration = duration
        self.token_counter = token_counter
        self.cost = cost

    def record(
        self,
        *,
        stage: str,
        outcome: str,
        duration_seconds: float | None = None,
        operation: str,
        section_key: str | None = None,
        error_code: str | None = None,
        scoring_version: str | None = None,
        catalog_version: str | None = None,
        amount: int = 1,
    ) -> None:
        if (
            stage not in _ALLOWED_STAGES
            or outcome not in _ALLOWED_OUTCOMES
            or operation not in _ALLOWED_OPERATIONS
            or (section_key is not None and section_key not in _ALLOWED_SECTIONS)
            or (error_code is not None and error_code not in _ALLOWED_ERROR_CODES)
            or (scoring_version is not None and _VERSION_RE.fullmatch(scoring_version) is None)
            or (catalog_version is not None and _VERSION_RE.fullmatch(catalog_version) is None)
            or amount < 1
        ):
            return
        attributes = {"stage": stage, "outcome": outcome, "operation": operation}
        if section_key is not None:
            attributes["section_key"] = section_key
        if error_code is not None:
            attributes["error_code"] = error_code
        if scoring_version is not None:
            attributes["scoring_version"] = scoring_version
        if catalog_version is not None:
            attributes["catalog_version"] = catalog_version
        self.counter.add(amount, attributes)
        if duration_seconds is not None:
            self.duration.record(max(duration_seconds, 0.0), attributes)

    def record_provider_usage(self, *, input_tokens: int, output_tokens: int, cost_usd: float) -> None:
        """Record aggregate provider usage without provider payload or identity labels."""

        if min(input_tokens, output_tokens, cost_usd) < 0:
            return
        if self.token_counter is not None:
            self.token_counter.add(input_tokens, {"kind": "input"})
            self.token_counter.add(output_tokens, {"kind": "output"})
        if self.cost is not None:
            self.cost.record(cost_usd, {})


def safe_error_code(exc: Exception, *, stage: str) -> str:
    """Map exceptions to bounded public telemetry codes without exception text."""

    if stage == "deterministic" and isinstance(exc, ValueError):
        return "career_input_failure"
    if exc.__class__.__name__ == "CareerNarrativeValidationError":
        return "career_validation_failure"
    return "career_provider_failure"


def estimate_provider_usage(
    *,
    prompt: str,
    output: str,
    input_cost_per_million: float,
    output_cost_per_million: float,
) -> dict[str, int | float]:
    """Estimate aggregate usage when a provider adapter exposes no usage object."""

    input_tokens = ceil(len(prompt) / 4) if prompt else 0
    output_tokens = ceil(len(output) / 4) if output else 0
    cost_usd = (
        input_tokens * max(input_cost_per_million, 0.0) + output_tokens * max(output_cost_per_million, 0.0)
    ) / 1_000_000
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost_usd, 8),
    }


_meter = metrics.get_meter("archemap.career")
career_telemetry = CareerTelemetry(
    counter=_meter.create_counter(
        "career_operations_total",
        description="Career pipeline operations by bounded stage and outcome",
    ),
    duration=_meter.create_histogram(
        "career_operation_duration_seconds",
        unit="s",
        description="Career stage duration by bounded stage and outcome",
    ),
    token_counter=_meter.create_counter(
        "career_provider_tokens_total",
        unit="token",
        description="Career provider input and output token usage",
    ),
    cost=_meter.create_histogram(
        "career_provider_cost_usd",
        unit="USD",
        description="Career provider cost per section generation",
    ),
)


def bind_career_context(
    *,
    generation_id: str,
    report_id: str | None,
    user_id: str,
    section_key: str | None = None,
    scoring_version: str | None = None,
    prompt_version: str | None = None,
    model_version: str | None = None,
) -> structlog.stdlib.BoundLogger:
    """Bind searchable IDs to logs/traces without recording report content."""

    context = {
        "generation_id": generation_id,
        "report_id": report_id,
        "user_id": user_id,
        "section_key": section_key,
        "scoring_version": scoring_version,
        "prompt_version": prompt_version,
        "model_version": model_version,
    }
    safe_context = {key: value for key, value in context.items() if value is not None}
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in safe_context.items():
            span.set_attribute(f"career.{key}", value)
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger().bind(**safe_context))
