"""E23.S07 calendar, policy and task topology contracts."""

from datetime import UTC, date, datetime, timedelta

from app.config import settings
from app.modules.analytics.operations import (
    ProviderSample,
    digest_target,
    moscow_day_bounds,
    provider_state,
)
from workers.celery_app import app


def test_digest_catches_up_only_latest_due_day_and_uses_moscow_midnight() -> None:
    due = datetime(2026, 6, 1, 7, tzinfo=UTC)
    assert digest_target(due - timedelta(microseconds=1)) == date(2026, 5, 30)
    assert digest_target(due) == date(2026, 5, 31)
    assert digest_target(due + timedelta(hours=12)) == date(2026, 5, 31)
    assert moscow_day_bounds(date(2026, 5, 31)) == (
        datetime(2026, 5, 30, 21, tzinfo=UTC),
        datetime(2026, 5, 31, 21, tzinfo=UTC),
    )


def test_provider_breach_and_recovery_need_positive_evidence() -> None:
    assert provider_state(ProviderSample(failed=1, ready=0, ready_after_failure=0)) is None
    assert provider_state(ProviderSample(failed=3, ready=2, ready_after_failure=0)) is True
    assert provider_state(ProviderSample(failed=0, ready=0, ready_after_failure=0)) is None
    assert provider_state(ProviderSample(failed=2, ready=5, ready_after_failure=0)) is None
    assert provider_state(ProviderSample(failed=1, ready=5, ready_after_failure=3)) is False


def test_analytics_tasks_use_existing_worker_queue_and_watchdog_is_not_a_task() -> None:
    app.loader.import_default_modules()
    expected = {"analytics.project_business_events", "analytics.evaluate_business_operations"}
    assert expected.issubset(app.tasks)
    assert not any("dead_man" in name for name in app.tasks)
    entries = {entry["task"]: entry for entry in app.conf.beat_schedule.values() if entry["task"] in expected}
    assert entries.keys() == (expected if settings.BUSINESS_MONITORING_ENABLED else set())
    assert all(entry["schedule"] == 60.0 and entry["options"]["expires"] == 110 for entry in entries.values())
    for name in expected:
        assert app.conf.task_routes[name] == {"queue": "celery"}
