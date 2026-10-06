"""E10 S05 observability, rollback, and alerting contracts."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

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
    telemetry = BirthDataRefinementTelemetry(
        requests=requests,
        cooldowns=cooldowns,
        duration=duration,
        failures=failures,
        stuck=stuck,
    )

    telemetry.record_request("accepted")
    telemetry.record_request("profile-123")
    telemetry.record_cooldown_rejection()
    telemetry.record_generation_duration(2.5)
    telemetry.record_generation_failure("report_generation_failed")
    telemetry.record_generation_failure("private place: Moscow")
    telemetry.set_stuck_generations(3)

    assert requests.calls == [(1, {"outcome": "accepted"})]
    assert cooldowns.calls == [(1, None)]
    assert duration.calls == [(2.5, None)]
    assert failures.calls == [(1, {"code": "report_generation_failed"})]
    assert stuck.calls == [(3, None)]
    assert "Moscow" not in repr((requests.calls, cooldowns.calls, duration.calls, failures.calls, stuck.calls))


def test_instrument_names_and_attributes_are_pii_free() -> None:
    source = (REPOSITORY_ROOT / "backend/app/modules/profiles/observability.py").read_text(encoding="utf-8")

    for name in (
        "birth_data_refinement_requests_total",
        "birth_data_refinement_cooldown_rejections_total",
        "birth_data_refinement_generation_duration_seconds",
        "birth_data_refinement_generation_failures_total",
        "birth_data_refinement_stuck_generations",
    ):
        assert name in source
    for forbidden in ("user_id", "profile_id", "revision_id", "birth_time", "birth_place", "snapshot"):
        assert forbidden not in source


def test_refinement_worker_failure_logs_use_bounded_codes_not_exception_strings() -> None:
    source = (REPOSITORY_ROOT / "backend/workers/tasks/astrotype_v2.py").read_text(encoding="utf-8")

    assert "birth_data_refinement_generation_failed" in source
    assert 'error_code="report_generation_failed"' in source
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
    warning.assert_called_once_with(
        "birth_data_refinement_alert",
        stuck=2,
        recent_failed=1,
        stuck_after_minutes=20,
        monitor_window_minutes=15,
    )
    assert not {"user_id", "profile_id", "revision_id", "snapshot"} & set(warning.call_args.kwargs)


def test_prometheus_rules_cover_stuck_and_failure_increase() -> None:
    rules_path = REPOSITORY_ROOT / "deploy/prometheus-birth-data-refinement.rules.yaml"
    rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    alerts = {rule["alert"]: rule for group in rules["groups"] for rule in group["rules"]}

    assert "BirthDataRefinementStuckGenerations" in alerts
    assert "BirthDataRefinementGenerationFailures" in alerts
    assert "birth_data_refinement_stuck_generations > 0" in alerts["BirthDataRefinementStuckGenerations"]["expr"]
    assert (
        "increase(birth_data_refinement_generation_failures_total"
        in alerts["BirthDataRefinementGenerationFailures"]["expr"]
    )
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


def test_staging_and_production_compose_enable_backend_worker_scheduler_and_frontend() -> None:
    for filename in ("docker-compose.staging.yml", "docker-compose.prod.yml"):
        compose = yaml.safe_load((REPOSITORY_ROOT / filename).read_text(encoding="utf-8"))
        services: dict[str, Any] = compose["services"]
        for service_name in ("backend", "worker", "scheduler"):
            assert services[service_name]["environment"]["BIRTH_DATA_REFINEMENT_ENABLED"] == "true"
        assert services["frontend"]["environment"]["NEXT_PUBLIC_BIRTH_DATA_REFINEMENT_ENABLED"] == "true"
