"""Bounded, content-free Child worker telemetry; no process-local current gauge."""

from __future__ import annotations

import math
from contextlib import AbstractContextManager
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.metrics import Meter
from opentelemetry.trace import Span, Tracer

from app.modules.child.narrative import ChildSectionRenderInput, ChildSegmentProvider, DisabledChildSegmentProvider
from app.modules.child.status import ChildGenerationOperation, ChildGenerationStatus

OPERATIONS = frozenset(item.value for item in ChildGenerationOperation) | {"worker"}
OUTCOMES = frozenset(item.value for item in ChildGenerationStatus) | {"not_claimed", "worker_failure"}


class ChildTelemetry:
    """Never accept arbitrary labels, identifiers, prose or exception objects."""

    def __init__(self, *, meter: Meter, tracer: Tracer) -> None:
        self.tracer = tracer
        self.operations = meter.create_counter("child.worker.operations", description="Child worker outcomes")
        self.duration = meter.create_histogram("child.worker.duration", unit="s")
        self.provider_attempts = meter.create_counter(
            "child.provider.attempts", description="Observed provider attempts"
        )

    def lifecycle(self) -> AbstractContextManager[Span]:
        # SDK defaults record exception messages/stacktraces: explicitly disable both.
        return self.tracer.start_as_current_span("child.worker", record_exception=False, set_status_on_exception=False)

    def record(self, *, operation: str, outcome: str, duration_seconds: float) -> None:
        if (
            not isinstance(operation, str)
            or operation not in OPERATIONS
            or not isinstance(outcome, str)
            or outcome not in OUTCOMES
            or not isinstance(duration_seconds, (int, float))
            or isinstance(duration_seconds, bool)
            or not math.isfinite(duration_seconds)
            or duration_seconds < 0
        ):
            raise ValueError("invalid child telemetry measurement")
        attributes = {"operation": operation, "outcome": outcome}
        self.operations.add(1, attributes)
        self.duration.record(duration_seconds, attributes)

    def provider_attempt(self, *, operation: str) -> None:
        """Count immediately BEFORE a provider call, including thrown/ambiguous attempts."""
        if not isinstance(operation, str) or operation not in OPERATIONS:
            raise ValueError("invalid child telemetry operation")
        self.provider_attempts.add(1, {"operation": operation, "outcome": "attempt"})


class ObservedChildProvider:
    def __init__(self, provider: ChildSegmentProvider, *, operation: str) -> None:
        self.provider = provider
        self.operation = operation
        self.provider_name = provider.provider_name
        self.model_name = provider.model_name

    async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
        child_telemetry.provider_attempt(operation=self.operation)
        return await self.provider.generate_segment(prompt=prompt, section_input=section_input)


def observe_child_provider(provider: ChildSegmentProvider, *, operation: str) -> ChildSegmentProvider:
    """Keep the controlled disabled sentinel unwrapped: it performs no external attempt."""
    if isinstance(provider, DisabledChildSegmentProvider):
        return provider
    return ObservedChildProvider(provider, operation=operation)


child_telemetry = ChildTelemetry(meter=metrics.get_meter("archemap.child"), tracer=trace.get_tracer("archemap.child"))
