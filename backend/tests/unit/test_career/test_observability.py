from __future__ import annotations

from collections.abc import Mapping

from app.infrastructure.observability import configure_metrics
from app.modules.career.observability import CareerTelemetry, estimate_provider_usage, safe_error_code


class _Instrument:
    def __init__(self) -> None:
        self.calls: list[tuple[float, dict[str, str]]] = []

    def add(self, value: float, attributes: Mapping[str, str] | None = None) -> None:
        self.calls.append((value, dict(attributes or {})))

    def record(self, value: float, attributes: Mapping[str, str] | None = None) -> None:
        self.calls.append((value, dict(attributes or {})))


def test_metrics_exporter_is_disabled_without_endpoint() -> None:
    assert configure_metrics(endpoint="", service_name="archemap-test") is False


def test_telemetry_records_bounded_labels_without_user_identifiers() -> None:
    counter = _Instrument()
    duration = _Instrument()
    telemetry = CareerTelemetry(counter=counter, duration=duration)

    telemetry.record(stage="narrative", outcome="failed", duration_seconds=1.25, operation="regenerate")

    assert counter.calls == [(1, {"stage": "narrative", "outcome": "failed", "operation": "regenerate"})]
    assert duration.calls == [(1.25, {"stage": "narrative", "outcome": "failed", "operation": "regenerate"})]


def test_telemetry_rejects_unbounded_or_unknown_label_values() -> None:
    counter = _Instrument()
    duration = _Instrument()
    telemetry = CareerTelemetry(counter=counter, duration=duration)

    telemetry.record(stage="unknown", outcome="ready", duration_seconds=0.5, operation="create")

    assert counter.calls == []
    assert duration.calls == []


def test_telemetry_records_only_safe_failure_and_rollout_labels() -> None:
    counter = _Instrument()
    telemetry = CareerTelemetry(counter=counter, duration=_Instrument())

    telemetry.record(
        stage="narrative",
        outcome="failed",
        operation="create",
        error_code="career_validation_failure",
        scoring_version="career-mvp-1",
        catalog_version="career-role-catalog-1",
    )
    telemetry.record(
        stage="narrative",
        outcome="failed",
        operation="create",
        error_code="provider-secret-and-user-answer",
    )

    assert counter.calls == [
        (
            1,
            {
                "stage": "narrative",
                "outcome": "failed",
                "operation": "create",
                "error_code": "career_validation_failure",
                "scoring_version": "career-mvp-1",
                "catalog_version": "career-role-catalog-1",
            },
        )
    ]


def test_questionnaire_and_stuck_metrics_never_include_answers_or_ids() -> None:
    counter = _Instrument()
    telemetry = CareerTelemetry(counter=counter, duration=_Instrument())

    telemetry.record(stage="questionnaire", outcome="completed", operation="complete")
    telemetry.record(stage="narrative", outcome="stuck", operation="scan")

    assert counter.calls == [
        (1, {"stage": "questionnaire", "outcome": "completed", "operation": "complete"}),
        (1, {"stage": "narrative", "outcome": "stuck", "operation": "scan"}),
    ]


def test_exception_names_are_mapped_to_bounded_error_codes() -> None:
    assert safe_error_code(ValueError("secret"), stage="deterministic") == "career_input_failure"
    assert safe_error_code(RuntimeError("secret"), stage="narrative") == "career_provider_failure"


def test_provider_usage_metrics_have_no_payload_or_identity_labels() -> None:
    token_counter = _Instrument()
    cost = _Instrument()
    telemetry = CareerTelemetry(
        counter=_Instrument(),
        duration=_Instrument(),
        token_counter=token_counter,
        cost=cost,
    )

    telemetry.record_provider_usage(input_tokens=120, output_tokens=45, cost_usd=0.003)

    assert token_counter.calls == [(120, {"kind": "input"}), (45, {"kind": "output"})]
    assert cost.calls == [(0.003, {})]


def test_provider_usage_estimate_returns_only_counts_and_cost() -> None:
    usage = estimate_provider_usage(
        prompt="x" * 400,
        output="y" * 200,
        input_cost_per_million=2.0,
        output_cost_per_million=8.0,
    )

    assert usage == {"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.0006}
