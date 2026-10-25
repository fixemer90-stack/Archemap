from __future__ import annotations

import math

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.modules.child.observability import ChildTelemetry


def telemetry() -> tuple[ChildTelemetry, InMemoryMetricReader, InMemorySpanExporter]:
    reader = InMemoryMetricReader()
    meter = MeterProvider(metric_readers=[reader]).get_meter("test.child")
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return ChildTelemetry(meter=meter, tracer=provider.get_tracer("test.child")), reader, exporter


@pytest.mark.parametrize("outcome", ["ready", "failed", "narrative_failed", "not_claimed"])
def test_actual_emissions_contain_only_bounded_attributes(outcome: str) -> None:
    instrument, reader, exporter = telemetry()
    with instrument.lifecycle():
        instrument.record(operation="full_report", outcome=outcome, duration_seconds=0.2)
    data = reader.get_metrics_data()
    assert data is not None
    emitted = [
        point.attributes
        for resource in data.resource_metrics
        for scope in resource.scope_metrics
        for metric in scope.metrics
        for point in metric.data.data_points
    ]
    assert emitted
    assert all(set(attrs or {}) <= {"operation", "outcome"} for attrs in emitted)
    assert {dict(attrs or {})["outcome"] for attrs in emitted} == {outcome}
    assert all(not span.events and not span.attributes for span in exporter.get_finished_spans())


@pytest.mark.parametrize(
    "labels",
    [
        {"operation": "Child Alice", "outcome": "ready"},
        {"operation": "full_report", "outcome": "DOB 2020-01-01"},
        {"operation": [], "outcome": "ready"},
        {"operation": "full_report", "outcome": "ready", "child_name": "Alice"},
    ],
)
def test_hostile_labels_rejected_before_any_emission(labels: dict[str, object]) -> None:
    instrument, reader, _ = telemetry()
    with pytest.raises((ValueError, TypeError)):
        instrument.record(**labels, duration_seconds=1.0)  # type: ignore[arg-type]
    assert reader.get_metrics_data() is None


@pytest.mark.parametrize("duration", [-1, math.nan, math.inf])
def test_invalid_measurements_rejected(duration: float) -> None:
    instrument, _, _ = telemetry()
    with pytest.raises(ValueError):
        instrument.record(operation="full_report", outcome="ready", duration_seconds=duration)


def test_failure_span_does_not_automatically_record_exception_pii() -> None:
    instrument, _, exporter = telemetry()
    with pytest.raises(RuntimeError), instrument.lifecycle():
        raise RuntimeError("Alice DOB answers private prose")
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert not spans[0].events
    assert not spans[0].attributes
    assert spans[0].status.description is None
