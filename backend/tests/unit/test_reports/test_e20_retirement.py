"""Retirement boundaries for generic Career reports (not the target product)."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.reports import router
from app.modules.reports.schemas import GenerateReportRequest
from app.modules.reports.service import ReportService


@pytest.mark.asyncio
async def test_e20_direct_career_generation_rejects_before_database_effects() -> None:
    db = MagicMock()
    db.execute = AsyncMock(side_effect=AssertionError("retirement must precede SQL"))
    with pytest.raises(HTTPException) as exc:
        await ReportService(db).generate_report(uuid4(), uuid4(), product="career")
    assert exc.value.status_code == 410
    assert cast(Any, exc.value.detail) == {
        "code": "legacy_career_generation_retired",
        "message": "Career reports are created through the Career product flow.",
        "target_path": "/products/career",
    }
    db.execute.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_e20_router_rejects_before_generation_after_ownership_and_access(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    service = MagicMock()

    async def owned(*args: object) -> None:
        events.append("ownership")

    async def access(**kwargs: object) -> None:
        events.append("access")

    service.assert_profile_owned = owned
    service.generate_report = AsyncMock(side_effect=AssertionError("writer must not be invoked"))
    monkeypatch.setattr(router, "ReportService", lambda db: service)
    monkeypatch.setattr(router, "_require_legacy_report_access", access)
    with pytest.raises(HTTPException) as exc:
        await router.generate_report(
            GenerateReportRequest(profile_id=str(uuid4()), product="career"), MagicMock(), uuid4()
        )
    assert exc.value.status_code == 410
    assert events == ["ownership", "access"]
    service.generate_report.assert_not_called()


def test_e20_telemetry_rejects_unknown_operations() -> None:
    from app.modules.reports.retirement import RetirementTelemetry

    counter = MagicMock()
    telemetry = RetirementTelemetry(counter=counter)
    invalid_operations: list[object] = ["bad", "archive_read:private@example.com", "", None, []]
    for operation in invalid_operations:
        telemetry.record(cast(str, operation))
    counter.add.assert_not_called()
    telemetry.record("blocked_generation")
    counter.add.assert_called_once_with(1, {"operation": "blocked_generation"})


def test_e20_celery_retirement_never_finalizes_as_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.modules.report_narratives import tasks
    from app.modules.reports.retirement import LegacyCareerRetiredError
    from workers.tasks.reports import generate_report_narrative

    monkeypatch.setattr(tasks, "generate_report_narrative_task", MagicMock(side_effect=LegacyCareerRetiredError()))
    finalizer = MagicMock()
    monkeypatch.setattr(tasks, "finalize_narrative_task_failure", finalizer)
    with pytest.raises(LegacyCareerRetiredError):
        cast(Any, generate_report_narrative).run(str(uuid4()))
    finalizer.assert_not_called()


def test_e20_runtime_openapi_declares_structured_retirement_response() -> None:
    from app.main import app

    schema = app.openapi()
    for path in ("/api/v1/reports/generate", "/api/v1/reports/{report_id}/narrative/regenerate"):
        response = schema["paths"][path]["post"]["responses"]["410"]
        assert response["content"]["application/json"]["schema"]["$ref"].endswith("/LegacyCareerRetiredResponse")


@pytest.mark.asyncio
async def test_e20_grandfathered_target_access_is_observed(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.modules.career import router as career_router
    from app.modules.career.access import CareerAccessDecision
    from app.modules.reports.retirement import retirement_telemetry

    monkeypatch.setattr(
        "app.modules.payments.service.PaymentsService.reconcile_latest_pending_provider_payment", AsyncMock()
    )
    monkeypatch.setattr(
        "app.modules.career.access.CareerAccessPolicy.check",
        AsyncMock(return_value=CareerAccessDecision(allowed=True, source="legacy_career")),
    )
    counter = MagicMock()
    monkeypatch.setattr(retirement_telemetry, "counter", counter)
    await career_router._require_career_access(db=MagicMock(), user_id=uuid4())
    counter.add.assert_called_once_with(1, {"operation": "target_grandfathered_access"})


@pytest.mark.asyncio
async def test_e20_rules_service_cannot_bypass_retired_career_generation() -> None:
    from app.modules.rules.service import RulesService

    db = MagicMock()
    db.execute = AsyncMock(side_effect=AssertionError("no snapshot lookup before retirement"))
    with pytest.raises(HTTPException) as exc:
        await RulesService(db).interpret_chart(uuid4(), uuid4(), product="career")
    assert exc.value.status_code == 410
    db.execute.assert_not_called()


def test_e20_rules_runtime_declares_retirement() -> None:
    from app.main import app

    assert "410" in app.openapi()["paths"]["/api/v1/rules/interpret"]["post"]["responses"]


@pytest.mark.asyncio
@pytest.mark.parametrize("product", ["self"])
async def test_e20_noncareer_rules_service_still_interprets_real_rules(
    product: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.modules.charts.models import ChartSnapshot
    from app.modules.rules.service import RulesService
    from tests.unit.test_reports.test_reports import make_chart_data

    service = RulesService(MagicMock())
    monkeypatch.setattr(service, "_get_snapshot", AsyncMock(return_value=ChartSnapshot(chart_data=make_chart_data())))
    rendered = await service.interpret_chart(uuid4(), uuid4(), product=product)
    assert isinstance(rendered["claims"], list)


def test_e20_pure_career_rules_loader_remains_usable() -> None:
    from app.modules.rules.loader import load_ruleset

    assert load_ruleset("career", "v1") is not None
