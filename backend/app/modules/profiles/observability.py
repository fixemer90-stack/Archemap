"""Low-cardinality metrics for E10 birth-data refinement."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from opentelemetry import metrics
from opentelemetry.metrics import Observation

_ALLOWED_REQUEST_OUTCOMES = {
    "accepted",
    "disabled",
    "validation_rejected",
    "forbidden",
    "not_found",
    "conflict",
    "cooldown",
    "enqueue_failed",
}
_ALLOWED_FAILURE_CODES = {
    "narrative_generation_failed",
    "report_generation_failed",
}


class _Counter(Protocol):
    def add(self, amount: float, attributes: Mapping[str, str] | None = None) -> None: ...


class _Histogram(Protocol):
    def record(self, amount: float, attributes: Mapping[str, str] | None = None) -> None: ...


class _Gauge(Protocol):
    def set(self, amount: float, attributes: Mapping[str, str] | None = None) -> None: ...


class _CurrentGauge:
    def __init__(self) -> None:
        self.value = 0

    def set(self, amount: float, attributes: Mapping[str, str] | None = None) -> None:
        del attributes
        self.value = max(int(amount), 0)

    def observe(self, _options: object) -> list[Observation]:
        return [Observation(self.value)]


class BirthDataRefinementTelemetry:
    """Record only allowlisted outcomes/codes and aggregate numeric values."""

    def __init__(
        self,
        *,
        requests: _Counter,
        cooldowns: _Counter,
        duration: _Histogram,
        failures: _Counter,
        stuck: _Gauge,
    ) -> None:
        self.requests = requests
        self.cooldowns = cooldowns
        self.duration = duration
        self.failures = failures
        self.stuck = stuck

    def record_request(self, outcome: str) -> None:
        if outcome in _ALLOWED_REQUEST_OUTCOMES:
            self.requests.add(1, {"outcome": outcome})

    def record_cooldown_rejection(self) -> None:
        self.cooldowns.add(1)

    def record_generation_duration(self, duration_seconds: float) -> None:
        self.duration.record(max(duration_seconds, 0.0))

    def record_generation_failure(self, code: str) -> None:
        if code in _ALLOWED_FAILURE_CODES:
            self.failures.add(1, {"code": code})

    def set_stuck_generations(self, count: int) -> None:
        self.stuck.set(max(count, 0))


_meter = metrics.get_meter("archemap.birth_data_refinement")
_current_stuck = _CurrentGauge()
_meter.create_observable_gauge(
    "birth_data_refinement_stuck_generations",
    callbacks=[_current_stuck.observe],
    description="Current queued or processing birth-data refinements older than the configured threshold",
)
birth_data_refinement_telemetry = BirthDataRefinementTelemetry(
    requests=_meter.create_counter(
        "birth_data_refinement_requests_total",
        description="Birth-data refinement POST requests by bounded outcome",
    ),
    cooldowns=_meter.create_counter(
        "birth_data_refinement_cooldown_rejections_total",
        description="Birth-data refinement requests rejected by the cooldown",
    ),
    duration=_meter.create_histogram(
        "birth_data_refinement_generation_duration_seconds",
        unit="s",
        description="Birth-data refinement generation duration",
    ),
    failures=_meter.create_counter(
        "birth_data_refinement_generation_failures_total",
        description="Birth-data refinement generation failures by bounded code",
    ),
    stuck=_current_stuck,
)
