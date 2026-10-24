from __future__ import annotations

import inspect

import pytest

from app.api.v1 import api_router
from app.modules.child.narrative import DisabledChildSegmentProvider
from app.modules.child.router import router as child_router
from app.modules.child.service import configured_child_provider
from workers.celery_app import app
from workers.tasks.child import generate_child_report


def test_child_report_create_routes_are_registered_in_production_api() -> None:
    assert any(getattr(included, "original_router", None) is child_router for included in api_router.routes)
    routes = {
        (getattr(route, "path", ""), method)
        for route in child_router.routes
        for method in getattr(route, "methods", set())
    }

    assert ("/child/reports", "POST") in routes
    endpoint = next(
        getattr(route, "endpoint", None)
        for route in child_router.routes
        if getattr(route, "path", "") == "/child/reports"
    )
    assert endpoint is not None
    assert endpoint.child_access_operation == "report_create"


def test_child_worker_has_bounded_soft_and_hard_timeouts_without_fake_celery_retry() -> None:
    registered = app.tasks["child.generate_report"]

    assert registered.name == generate_child_report.name == "child.generate_report"
    assert isinstance(registered.soft_time_limit, int)
    assert isinstance(registered.time_limit, int)
    assert 0 < registered.soft_time_limit < registered.time_limit
    source = inspect.getsource(registered.run)
    assert "self.retry" not in source


def test_child_reconciliation_is_scheduled() -> None:
    schedule = app.conf.beat_schedule["reconcile-child-generations"]

    assert schedule["task"] == "child.reconcile_generations"
    assert float(schedule["schedule"]) > 0


def test_default_disabled_llm_uses_controlled_non_mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.child.service.settings.LLM_ENABLED", False)
    monkeypatch.setattr("app.modules.child.service.settings.LLM_PROVIDER", "mock")

    provider = configured_child_provider()

    assert isinstance(provider, DisabledChildSegmentProvider)
    assert provider.provider_name == "disabled"
