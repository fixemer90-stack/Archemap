"""E10 S05 observability, rollback, and alerting contracts."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call

import pytest
import yaml

from app.config import Settings

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class RecordingCounter:
    def __init__(self) -> None:
        self.calls: list[tuple[float, Mapping[str, str] | None]] = []

    def add(self, amount: float, attributes: Mapping[str, str] | None = None) -> None:
        self.calls.append((amount, attributes))


class RecordingHistogram:
    def __init__(self) -> None:
        self.calls: list[tuple[float, Mapping[str, str] | None]] = []

    def record(self, amount: float, attributes: Mapping[str, str] | None = None) -> None:
        self.calls.append((amount, attributes))


class RecordingGauge:
    def __init__(self) -> None:
        self.calls: list[tuple[float, Mapping[str, str] | None]] = []

    def set(self, amount: float, attributes: Mapping[str, str] | None = None) -> None:
        self.calls.append((amount, attributes))


def test_refinement_settings_default_to_safe_rollback_values() -> None:
    config = Settings(_env_file=None)

    assert config.BIRTH_DATA_REFINEMENT_ENABLED is False
    assert config.BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES == 20
    assert config.BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES == 15
    assert config.BIRTH_DATA_REFINEMENT_MONITOR_INTERVAL_SECONDS == 300


def test_telemetry_accepts_only_bounded_attributes() -> None:
    from app.modules.profiles.observability import BirthDataRefinementTelemetry

    requests = RecordingCounter()
    cooldowns = RecordingCounter()
    duration = RecordingHistogram()
    failures = RecordingCounter()
    stuck = RecordingGauge()
    recent_failures = RecordingGauge()
    telemetry = BirthDataRefinementTelemetry(
        requests=requests,
        cooldowns=cooldowns,
        duration=duration,
        failures=failures,
        stuck=stuck,
        recent_failures=recent_failures,
    )

    telemetry.record_request("accepted")
    telemetry.record_request("profile-123")
    telemetry.record_cooldown_rejection()
    telemetry.record_generation_duration(2.5)
    telemetry.record_generation_failure("report_generation_failed")
    telemetry.record_generation_failure("private place: Moscow")
    telemetry.set_stuck_generations(3)
    telemetry.set_recent_failures(2)

    assert requests.calls == [(1, {"outcome": "accepted"})]
    assert cooldowns.calls == [(1, None)]
    assert duration.calls == [(2.5, None)]
    assert failures.calls == [(1, {"code": "report_generation_failed"})]
    assert stuck.calls == [(3, None)]
    assert recent_failures.calls == [(2, None)]
    assert "Moscow" not in repr(
        (requests.calls, cooldowns.calls, duration.calls, failures.calls, stuck.calls, recent_failures.calls)
    )


def test_otel_instrument_names_are_native_and_prometheus_series_are_documented_separately() -> None:
    source = (REPOSITORY_ROOT / "backend/app/modules/profiles/observability.py").read_text(encoding="utf-8")

    for name in (
        '"birth_data_refinement_requests"',
        '"birth_data_refinement_cooldown_rejections"',
        '"birth_data_refinement_generation_duration"',
        '"birth_data_refinement_generation_failures"',
        "birth_data_refinement_stuck_generations",
        "birth_data_refinement_recent_failures",
    ):
        assert name in source
    for forbidden_name in (
        '"birth_data_refinement_requests_total"',
        '"birth_data_refinement_cooldown_rejections_total"',
        '"birth_data_refinement_generation_duration_seconds"',
        '"birth_data_refinement_generation_failures_total"',
    ):
        assert forbidden_name not in source
    assert 'unit="s"' in source
    for forbidden in ("user_id", "profile_id", "revision_id", "birth_time", "birth_place", "snapshot"):
        assert forbidden not in source


def test_refinement_worker_logs_use_strict_allowlist_and_preserve_non_refinement_context() -> None:
    from workers.tasks import astrotype_v2

    refinement_logger = MagicMock()
    astrotype_v2._log_generation_started(
        refinement_logger,
        generation_id="generation-1",
        revision_id="revision-1",
        profile_id="profile-private",
        user_id="user-private",
        force=True,
    )
    astrotype_v2._log_generation_finished(
        refinement_logger,
        generation_id="generation-1",
        revision_id="revision-1",
        report_id="report-private",
        profile_id="profile-private",
        status="ready",
    )
    astrotype_v2._log_generation_finished(
        refinement_logger,
        generation_id="generation-1",
        revision_id="revision-1",
        report_id="report-private",
        profile_id="profile-private",
        status="private-status-Moscow",
    )
    astrotype_v2._log_generation_narrative_failed(
        refinement_logger,
        generation_id="generation-1",
        revision_id="revision-1",
        report_id="report-private",
        profile_id="profile-private",
    )
    astrotype_v2._log_generation_failed(
        refinement_logger,
        generation_id="generation-1",
        revision_id="revision-1",
        profile_id="profile-private",
        user_id="user-private",
    )

    assert refinement_logger.info.call_args_list == [
        call("birth_data_refinement_generation_started", generation_id="generation-1", revision_id="revision-1"),
        call(
            "birth_data_refinement_generation_finished",
            generation_id="generation-1",
            revision_id="revision-1",
            status="ready",
        ),
        call(
            "birth_data_refinement_generation_finished",
            generation_id="generation-1",
            revision_id="revision-1",
            status="unknown",
        ),
    ]
    assert refinement_logger.error.call_args_list == [
        call(
            "birth_data_refinement_generation_narrative_failed",
            generation_id="generation-1",
            revision_id="revision-1",
            error_code="narrative_generation_failed",
        ),
        call(
            "birth_data_refinement_generation_failed",
            generation_id="generation-1",
            revision_id="revision-1",
            error_code="report_generation_failed",
        ),
    ]
    assert not refinement_logger.exception.called
    assert "private" not in repr(refinement_logger.mock_calls)

    legacy_logger = MagicMock()
    astrotype_v2._log_generation_started(
        legacy_logger,
        generation_id="generation-2",
        revision_id=None,
        profile_id="profile-2",
        user_id="user-2",
        force=False,
    )
    astrotype_v2._log_generation_failed(
        legacy_logger,
        generation_id="generation-2",
        revision_id=None,
        profile_id="profile-2",
        user_id="user-2",
    )

    legacy_logger.info.assert_called_once_with(
        "astrotype_v2_generation_started",
        generation_id="generation-2",
        profile_id="profile-2",
        user_id="user-2",
        force=False,
    )
    legacy_logger.exception.assert_called_once_with(
        "astrotype_v2_generation_failed",
        generation_id="generation-2",
        profile_id="profile-2",
        user_id="user-2",
        error_code="report_generation_failed",
    )


def test_refinement_execution_log_calls_do_not_inline_private_fields_or_exception_strings() -> None:
    source = (REPOSITORY_ROOT / "backend/workers/tasks/astrotype_v2.py").read_text(encoding="utf-8")

    for helper in (
        "_log_generation_started",
        "_log_generation_finished",
        "_log_generation_narrative_failed",
        "_log_generation_failed",
    ):
        assert helper in source
    assert "error=str(exc)" not in source


@pytest.mark.asyncio
async def test_monitor_reports_stuck_and_recent_failed_without_pii(monkeypatch: pytest.MonkeyPatch) -> None:
    from workers.tasks import profile_refinement

    stuck_result = MagicMock()
    stuck_result.scalar_one.return_value = 2
    failed_result = MagicMock()
    failed_result.scalar_one.return_value = 1
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[stuck_result, failed_result])
    context = AsyncMock()
    context.__aenter__.return_value = session
    context.__aexit__.return_value = None
    telemetry = MagicMock()
    warning = MagicMock()
    monkeypatch.setattr(profile_refinement, "async_session_factory", lambda: context)
    monkeypatch.setattr(profile_refinement, "birth_data_refinement_telemetry", telemetry)
    monkeypatch.setattr(profile_refinement.logger, "warning", warning)
    monkeypatch.setattr("workers.tasks.profile_refinement.settings.BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES", 20)
    monkeypatch.setattr("workers.tasks.profile_refinement.settings.BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES", 15)

    result = await profile_refinement._monitor_birth_data_refinements_async(now=datetime(2026, 10, 6, 8, 0, tzinfo=UTC))

    assert result == {"stuck": 2, "recent_failed": 1, "alerted": True}
    telemetry.set_stuck_generations.assert_called_once_with(2)
    telemetry.set_recent_failures.assert_called_once_with(1)
    warning.assert_called_once_with(
        "birth_data_refinement_alert",
        stuck=2,
        recent_failed=1,
        stuck_after_minutes=20,
        monitor_window_minutes=15,
    )
    assert not {"user_id", "profile_id", "revision_id", "snapshot"} & set(warning.call_args.kwargs)


def test_prometheus_rules_cover_stuck_and_recent_failures_without_counter_first_sample_loss() -> None:
    rules_path = REPOSITORY_ROOT / "deploy/prometheus-birth-data-refinement.rules.yaml"
    rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    alerts = {rule["alert"]: rule for group in rules["groups"] for rule in group["rules"]}

    assert "BirthDataRefinementStuckGenerations" in alerts
    assert "BirthDataRefinementGenerationFailures" in alerts
    assert "birth_data_refinement_stuck_generations > 0" in alerts["BirthDataRefinementStuckGenerations"]["expr"]
    failure_expr = alerts["BirthDataRefinementGenerationFailures"]["expr"]
    assert "birth_data_refinement_recent_failures > 0" in failure_expr
    assert "increase(" not in failure_expr
    for rule in alerts.values():
        assert set(rule["labels"]) == {"severity", "service"}
        assert rule["annotations"]["runbook"]
        assert "user" not in repr(rule).lower()


def test_staging_prometheus_loads_refinement_rules() -> None:
    compose = yaml.safe_load((REPOSITORY_ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8"))
    prometheus = compose["services"]["prometheus"]
    config = yaml.safe_load((REPOSITORY_ROOT / "deploy/prometheus.staging.yaml").read_text(encoding="utf-8"))

    assert (
        "./deploy/prometheus-birth-data-refinement.rules.yaml:/etc/prometheus/rules/birth-data-refinement.yaml:ro"
        in prometheus["volumes"]
    )
    assert config["rule_files"] == ["/etc/prometheus/rules/*.yaml"]


def _resolve_compose_flag(expression: str, environment: Mapping[str, str]) -> str:
    match = re.fullmatch(r"\$\{([A-Z0-9_]+):-([^}]*)}", expression)
    assert match is not None
    variable, default = match.groups()
    return environment.get(variable) or default


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ({}, "false"),
        ({"BIRTH_DATA_REFINEMENT_ENABLED": "true", "NEXT_PUBLIC_BIRTH_DATA_REFINEMENT_ENABLED": "true"}, "true"),
        ({"BIRTH_DATA_REFINEMENT_ENABLED": "false", "NEXT_PUBLIC_BIRTH_DATA_REFINEMENT_ENABLED": "false"}, "false"),
    ],
)
def test_staging_and_production_compose_flags_fail_closed_and_propagate_operator_values(
    environment: Mapping[str, str], expected: str
) -> None:
    for filename in ("docker-compose.staging.yml", "docker-compose.prod.yml"):
        compose = yaml.safe_load((REPOSITORY_ROOT / filename).read_text(encoding="utf-8"))
        services: dict[str, Any] = compose["services"]
        for service_name in ("backend", "worker", "refinement-monitor", "scheduler"):
            backend_flag = services[service_name]["environment"]["BIRTH_DATA_REFINEMENT_ENABLED"]
            assert _resolve_compose_flag(backend_flag, environment) == expected
        frontend = services["frontend"]
        build_flag = frontend["build"]["args"]["NEXT_PUBLIC_BIRTH_DATA_REFINEMENT_ENABLED"]
        runtime_flag = frontend["environment"]["NEXT_PUBLIC_BIRTH_DATA_REFINEMENT_ENABLED"]
        assert _resolve_compose_flag(build_flag, environment) == expected
        assert _resolve_compose_flag(runtime_flag, environment) == expected


def test_deployment_examples_keep_refinement_disabled_until_rollout_gates_pass() -> None:
    for filename in (".env.staging.example", ".env.production.example"):
        example = (REPOSITORY_ROOT / filename).read_text(encoding="utf-8")
        assert "BIRTH_DATA_REFINEMENT_ENABLED=false" in example
        assert "NEXT_PUBLIC_BIRTH_DATA_REFINEMENT_ENABLED=false" in example


def test_staging_and_production_monitor_thresholds_propagate_operator_values() -> None:
    environment = {
        "BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES": "31",
        "BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES": "17",
        "BIRTH_DATA_REFINEMENT_MONITOR_INTERVAL_SECONDS": "123",
    }
    expected = {
        "BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES": ("20", "31"),
        "BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES": ("15", "17"),
        "BIRTH_DATA_REFINEMENT_MONITOR_INTERVAL_SECONDS": ("300", "123"),
    }
    for filename in ("docker-compose.staging.yml", "docker-compose.prod.yml"):
        compose = yaml.safe_load((REPOSITORY_ROOT / filename).read_text(encoding="utf-8"))
        services: dict[str, Any] = compose["services"]
        for service_name in ("backend", "worker", "refinement-monitor", "scheduler"):
            service_environment = services[service_name]["environment"]
            for variable, (default, configured) in expected.items():
                expression = service_environment[variable]
                assert _resolve_compose_flag(expression, {}) == default
                assert _resolve_compose_flag(expression, environment) == configured
