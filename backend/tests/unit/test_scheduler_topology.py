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
