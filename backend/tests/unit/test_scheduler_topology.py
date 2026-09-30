from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from workers.celery_app import app

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILES = (
    "docker-compose.yml",
    "docker-compose.staging.yml",
    "docker-compose.prod.yml",
)
BEAT_COMMAND = "celery -A workers.celery_app.app beat --loglevel=INFO"


def _load_compose(filename: str) -> dict[str, Any]:
    payload = yaml.safe_load((REPOSITORY_ROOT / filename).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _command(service: dict[str, Any]) -> str:
    command = service.get("command", "")
    if isinstance(command, list):
        return " ".join(str(part) for part in command)
    return str(command).strip()


@pytest.mark.parametrize("filename", COMPOSE_FILES)
def test_compose_runs_one_singleton_celery_beat_scheduler(filename: str) -> None:
    services = _load_compose(filename)["services"]
    beat_services = [name for name, service in services.items() if " beat " in f" {_command(service)} "]

    assert beat_services == ["scheduler"]
    scheduler = services["scheduler"]
    worker = services["worker"]

    assert _command(scheduler) == BEAT_COMMAND
    assert " -B " not in f" {_command(worker)} "
    assert scheduler.get("deploy", {}).get("replicas", 1) == 1
    assert scheduler["build"] == worker["build"]
    assert scheduler["environment"] == worker["environment"]
    assert scheduler.get("env_file") == worker.get("env_file")
    assert scheduler["depends_on"] == worker["depends_on"]
    assert scheduler.get("restart") == worker.get("restart")
    assert scheduler.get("volumes") == worker.get("volumes")

    if "container_name" in worker:
        assert scheduler["container_name"] == "astrotype-scheduler"


def test_career_monitor_is_registered_in_the_local_beat_schedule() -> None:
    import workers.tasks.career  # noqa: F401

    schedule = app.conf.beat_schedule["monitor-career-pipeline"]

    assert schedule["task"] == "career.monitor_pipeline"
    assert schedule["schedule"] == 300.0
    assert schedule["task"] in app.tasks


def test_birth_data_refinement_dispatch_is_registered_in_the_beat_schedule() -> None:
    import workers.tasks  # noqa: F401

    schedule = app.conf.beat_schedule["dispatch-birth-data-refinements"]

    assert schedule["task"] == "profiles.dispatch_birth_data_refinements"
    assert schedule["schedule"] == 60.0
    assert schedule["task"] in app.tasks


def test_every_beat_schedule_entry_is_a_task_the_worker_can_execute() -> None:
    """Every scheduled task must be registered, or the worker rejects it with KeyError."""

    import workers.tasks  # noqa: F401

    unregistered = sorted(entry["task"] for entry in app.conf.beat_schedule.values() if entry["task"] not in app.tasks)

    assert unregistered == []


def test_staging_has_an_internal_otlp_metrics_collector() -> None:
    compose = _load_compose("docker-compose.staging.yml")
    services = compose["services"]

    collector = services["otel-collector"]
    assert collector["image"] == "otel/opentelemetry-collector-contrib:0.103.0"
    assert collector["command"] == ["--config=/etc/otelcol-contrib/config.yaml"]
    assert collector["volumes"] == ["./deploy/otel-collector.staging.yaml:/etc/otelcol-contrib/config.yaml:ro"]
    assert collector["healthcheck"]["test"] == [
        "CMD",
        "/otelcol-contrib",
        "validate",
        "--config=/etc/otelcol-contrib/config.yaml",
    ]
    assert "ports" not in collector

    for service_name in ("backend", "worker"):
        assert services[service_name]["depends_on"]["otel-collector"] == {"condition": "service_healthy"}

    collector_config = yaml.safe_load(
        (REPOSITORY_ROOT / "deploy" / "otel-collector.staging.yaml").read_text(encoding="utf-8")
    )
    assert collector_config["receivers"]["otlp"]["protocols"]["http"]["endpoint"] == "0.0.0.0:4318"
    assert collector_config["service"]["pipelines"]["metrics"] == {
        "receivers": ["otlp"],
        "exporters": ["debug", "prometheus"],
    }


def test_worker_configures_otlp_metrics_from_runtime_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings
    from workers import celery_app

    calls: list[tuple[str, str]] = []

    def fake_configure_metrics(*, endpoint: str, service_name: str) -> bool:
        calls.append((endpoint, service_name))
        return True

    monkeypatch.setattr(celery_app, "configure_metrics", fake_configure_metrics)
    monkeypatch.setattr(settings, "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "http://collector:4318/v1/metrics")
    monkeypatch.setattr(settings, "OTEL_SERVICE_NAME", "astrotype-staging")

    assert celery_app.configure_worker_observability() is True
    assert calls == [("http://collector:4318/v1/metrics", "astrotype-staging-worker")]


def test_staging_exposes_a_basic_auth_protected_career_metrics_dashboard() -> None:
    compose = _load_compose("docker-compose.staging.yml")
    services = compose["services"]

    prometheus = services["prometheus"]
    assert prometheus["image"] == "prom/prometheus:v2.53.1"
    assert prometheus["command"] == [
        "--config.file=/etc/prometheus/prometheus.yml",
        "--storage.tsdb.path=/prometheus",
        "--web.external-url=https://staging.astrotype.ru/career-metrics/",
        "--web.route-prefix=/",
    ]
    assert prometheus["volumes"] == [
        "./deploy/prometheus.staging.yaml:/etc/prometheus/prometheus.yml:ro",
        "prometheus_staging_data:/prometheus",
    ]
    assert "ports" not in prometheus
    assert prometheus["healthcheck"] == {
        "test": ["CMD", "wget", "--spider", "http://localhost:9090/-/ready"],
        "interval": "15s",
        "timeout": "5s",
        "retries": 10,
    }

    collector_config = yaml.safe_load(
        (REPOSITORY_ROOT / "deploy" / "otel-collector.staging.yaml").read_text(encoding="utf-8")
    )
    assert collector_config["exporters"]["prometheus"]["endpoint"] == "0.0.0.0:9464"
    assert collector_config["service"]["pipelines"]["metrics"]["exporters"] == [
        "debug",
        "prometheus",
    ]

    prometheus_config = yaml.safe_load(
        (REPOSITORY_ROOT / "deploy" / "prometheus.staging.yaml").read_text(encoding="utf-8")
    )
    assert prometheus_config["scrape_configs"] == [
        {
            "job_name": "otel-collector",
            "static_configs": [{"targets": ["otel-collector:9464"]}],
        }
    ]

    gateway = services["gateway"]
    assert gateway["depends_on"]["prometheus"] == {"condition": "service_healthy"}
    assert set(gateway["networks"]) == {"default", "edge"}
    caddyfile = (REPOSITORY_ROOT / "deploy" / "Caddyfile.staging").read_text(encoding="utf-8")
    ordered_route = caddyfile.split("\troute {", maxsplit=1)[1].split("\n\t}\n\n\theader", maxsplit=1)[0]
    basic_auth_position = ordered_route.index("basic_auth")
    root_redirect_position = ordered_route.index("@career_metrics_root path /career-metrics")
    dashboard_proxy_position = ordered_route.index("handle_path /career-metrics/*")
    frontend_fallback_position = ordered_route.index("reverse_proxy staging-frontend:3000")
    assert basic_auth_position < root_redirect_position < dashboard_proxy_position < frontend_fallback_position
    assert "redir @career_metrics_root /career-metrics/ 308" in ordered_route
    assert "reverse_proxy prometheus:9090" in ordered_route
