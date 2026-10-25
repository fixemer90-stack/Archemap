from __future__ import annotations

from typing import Any, cast

import pytest
from opentelemetry.sdk.metrics.export import NumberDataPoint
from tests.unit.test_child.test_ops_observability import telemetry

from app.modules.child.narrative import ChildSectionRenderInput
from app.modules.child.observability import ObservedChildProvider
from workers.tasks import child as worker


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_actual_worker_wrapper_emits_only_bounded_attributes(
    monkeypatch: pytest.MonkeyPatch,
    failure: bool,
) -> None:
    instrument, reader, exporter = telemetry()
    monkeypatch.setattr(worker, "child_telemetry", instrument)

    async def run(**kwargs: Any) -> dict[str, Any]:
        if failure:
            raise RuntimeError("Alice DOB answers prose")
        return {"status": "ready", "generation_id": "private-id", "provider_calls": 2}

    monkeypatch.setattr(worker, "_run_child_report_async", run)
    if failure:
        with pytest.raises(RuntimeError):
            await worker._generate_child_report_async(generation_id="private-id", task_id="private-task")
    else:
        await worker._generate_child_report_async(generation_id="private-id", task_id="private-task")
    data = reader.get_metrics_data()
    assert data is not None
    for resource in data.resource_metrics:
        for scope in resource.scope_metrics:
            for metric in scope.metrics:
                for point in metric.data.data_points:
                    assert dict(point.attributes or {}) == {
                        "operation": "worker",
                        "outcome": "worker_failure" if failure else "ready",
                    }
    assert all(
        not span.events and not span.attributes and span.status.description is None
        for span in exporter.get_finished_spans()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_provider_attempt_emitted_before_success_or_exception(
    monkeypatch: pytest.MonkeyPatch,
    failure: bool,
) -> None:
    instrument, reader, _ = telemetry()
    monkeypatch.setattr("app.modules.child.observability.child_telemetry", instrument)

    class Provider:
        provider_name = "test"
        model_name = "test"

        async def generate_segment(self, *, prompt: str, section_input: ChildSectionRenderInput) -> dict[str, Any]:
            if failure:
                raise RuntimeError(prompt)
            return {"prose": prompt}

    provider = ObservedChildProvider(Provider(), operation="full_report")
    if failure:
        with pytest.raises(RuntimeError):
            await provider.generate_segment(
                prompt="private prose", section_input=cast(ChildSectionRenderInput, object())
            )
    else:
        await provider.generate_segment(prompt="private prose", section_input=cast(ChildSectionRenderInput, object()))
    data = reader.get_metrics_data()
    assert data is not None
    points = [
        point
        for resource in data.resource_metrics
        for scope in resource.scope_metrics
        for metric in scope.metrics
        for point in metric.data.data_points
    ]
    assert len(points) == 1
    assert isinstance(points[0], NumberDataPoint)
    assert points[0].value == 1
    assert dict(points[0].attributes or {}) == {"operation": "full_report", "outcome": "attempt"}


def test_provider_attempt_rejects_hostile_operation() -> None:
    instrument, reader, _ = telemetry()
    with pytest.raises(ValueError):
        instrument.provider_attempt(operation="Alice DOB answers")
    assert reader.get_metrics_data() is None
