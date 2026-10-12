"""E8 access contract for the mounted legacy reports API."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from inspect import getsource
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

import app.modules.reports.router as reports_router
from app.modules.authorization.service import EntitlementsService
from app.modules.reports.access import LEGACY_REPORT_ROUTE_ACCESS_CONTRACT
from app.modules.reports.models import Report
from app.modules.reports.schemas import GenerateReportRequest
from app.modules.reports.service import ReportService


def test_legacy_report_runtime_routes_match_access_inventory() -> None:
    runtime_routes = {
        (method, f"/v1{cast(Any, route).path}"): cast(Any, route).endpoint.__report_access_operation__
        for route in reports_router.router.routes
        for method in cast(Any, route).methods or set()
    }

    assert runtime_routes == {
        (route.method, route.path): route.operation for route in LEGACY_REPORT_ROUTE_ACCESS_CONTRACT
    }


def test_every_legacy_report_operation_reaches_an_access_gate_before_payload_work() -> None:
    expected_gate: dict[Callable[..., Any], str] = {
        reports_router.generate_report: "await _require_legacy_report_access",
        reports_router.list_reports: "_accessible_legacy_report_products",
        reports_router.get_report: "await _require_owned_legacy_report_access",
        reports_router.regenerate_report_narrative: "await _require_owned_legacy_report_access",
        reports_router.head_report_pdf: "await _get_report_pdf_headers",
        reports_router.get_report_pdf: "await _render_report_pdf",
        reports_router.post_report_pdf: "await _render_report_pdf",
        reports_router.get_report_versions: "await _require_owned_legacy_report_access",
        reports_router.get_report_version: "await _require_owned_legacy_report_access",
    }

    for endpoint, marker in expected_gate.items():
        assert marker in getsource(endpoint)

    assert "await _require_owned_legacy_report_access" in getsource(reports_router._get_report_pdf_headers)


async def test_plus_only_legacy_read_is_denied_before_payload_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    report_id = uuid4()

    async def metadata(
        self: ReportService,
        requested_report_id: UUID,
        requested_user_id: UUID,
    ) -> SimpleNamespace:
        assert requested_report_id == report_id
        assert requested_user_id == user_id
        return SimpleNamespace(id=report_id, product="love")

    async def payload(*_args: Any, **_kwargs: Any) -> Report:
        raise AssertionError("protected payload loaded before access denial")

    async def no_plus(self: EntitlementsService, requested_user_id: UUID) -> bool:
        assert requested_user_id == user_id
        return False

    async def no_direct(self: EntitlementsService, requested_user_id: UUID, product: str) -> bool:
        assert requested_user_id == user_id
        assert product == "love"
        return False

    monkeypatch.setattr(ReportService, "get_report_access_metadata", metadata)
    monkeypatch.setattr(ReportService, "get_report", payload)
    monkeypatch.setattr(EntitlementsService, "has_active_plus_access", no_plus)
    monkeypatch.setattr(EntitlementsService, "has_active_direct_product_access", no_direct)

    with pytest.raises(HTTPException) as exc_info:
        await reports_router.get_report(report_id, db=cast(Any, AnyDb()), current_user=user_id)

    assert exc_info.value.status_code == 402
    detail = cast(dict[str, str], exc_info.value.detail)
    assert detail["report_type"] == "love"
    assert "report_data" not in detail


async def test_basic_legacy_read_does_not_query_paid_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    report = Report(
        id=uuid4(),
        user_id=user_id,
        profile_id=uuid4(),
        product="self",
        status="ready",
        version=1,
        mode="full",
        report_data={"product": "self", "archetype": {"primary": "Стратег"}},
        pdf_generated=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    async def metadata(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(id=report.id, product="self")

    async def payload(*_args: Any, **_kwargs: Any) -> Report:
        return report

    async def paid_lookup(*_args: Any, **_kwargs: Any) -> bool:
        raise AssertionError("basic report queried paid access")

    async def no_narrative(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(ReportService, "get_report_access_metadata", metadata)
    monkeypatch.setattr(ReportService, "get_report", payload)
    monkeypatch.setattr(EntitlementsService, "has_active_plus_access", paid_lookup)
    monkeypatch.setattr(reports_router, "get_latest_narrative_for_report", no_narrative)

    response = await reports_router.get_report(report.id, db=cast(Any, AnyDb()), current_user=user_id)

    assert response.id == report.id


async def test_plus_only_legacy_generation_checks_profile_ownership_then_denies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    profile_id = uuid4()
    events: list[str] = []

    async def owned(self: ReportService, requested_profile_id: UUID, requested_user_id: UUID) -> None:
        assert requested_profile_id == profile_id
        assert requested_user_id == user_id
        events.append("ownership")

    async def no_plus(self: EntitlementsService, requested_user_id: UUID) -> bool:
        assert requested_user_id == user_id
        events.append("access")
        return False

    async def no_direct(self: EntitlementsService, requested_user_id: UUID, product: str) -> bool:
        assert requested_user_id == user_id
        assert product == "child"
        events.append("direct_access")
        return False

    async def generate(*_args: Any, **_kwargs: Any) -> Report:
        raise AssertionError("generation started despite access denial")

    monkeypatch.setattr(ReportService, "assert_profile_owned", owned)
    monkeypatch.setattr(EntitlementsService, "has_active_plus_access", no_plus)
    monkeypatch.setattr(EntitlementsService, "has_active_direct_product_access", no_direct)
    monkeypatch.setattr(ReportService, "generate_report", generate)

    with pytest.raises(HTTPException) as exc_info:
        await reports_router.generate_report(
            GenerateReportRequest(profile_id=str(profile_id), product="child", mode="full"),
            db=cast(Any, AnyDb()),
            current_user=user_id,
        )

    assert exc_info.value.status_code == 402
    assert events == ["ownership", "access", "direct_access"]


async def test_legacy_list_includes_each_direct_grandfathered_product(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()

    async def no_plus(self: EntitlementsService, requested_user_id: UUID) -> bool:
        assert requested_user_id == user_id
        return False

    async def direct_product(
        self: EntitlementsService,
        requested_user_id: UUID,
        product: str,
    ) -> bool:
        assert requested_user_id == user_id
        return product == "love"

    monkeypatch.setattr(EntitlementsService, "has_active_plus_access", no_plus)
    monkeypatch.setattr(EntitlementsService, "has_active_direct_product_access", direct_product)

    allowed = await reports_router._accessible_legacy_report_products(
        db=cast(Any, AnyDb()),
        user_id=user_id,
    )

    assert "love" in allowed
    assert "child" not in allowed


class AnyDb:
    """Opaque DB stand-in; access-contract tests monkeypatch every DB boundary."""
