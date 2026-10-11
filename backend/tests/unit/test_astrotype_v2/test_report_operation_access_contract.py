from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from app.modules.astrotype_v2.router import _load_basic_report_for_user, _require_basic_report_access, router


def test_every_v2_report_route_has_an_explicit_basic_access_operation() -> None:
    runtime_routes = {
        (method, f"/v1{route.path}"): getattr(route.endpoint, "__report_access_operation__", None)
        for route in router.routes
        if isinstance(route, APIRoute)
        for method in route.methods or set()
        if method != "HEAD"
    }

    assert runtime_routes == {
        ("POST", "/v1/astrotype-v2/reports"): "create",
        ("GET", "/v1/astrotype-v2/reports/generations/{generation_id}"): "status",
        ("GET", "/v1/astrotype-v2/reports/{report_id}"): "read",
        ("GET", "/v1/astrotype-v2/reports/{report_id}/pdf"): "export",
        ("GET", "/v1/astrotype-v2/reports/{report_id}/progress"): "status",
        ("GET", "/v1/astrotype-v2/reports/{report_id}/facts"): "calculation",
        ("GET", "/v1/astrotype-v2/reports/{report_id}/infographic"): "calculation",
        ("GET", "/v1/astrotype-v2/reports/{report_id}/segments"): "segments",
        ("POST", "/v1/astrotype-v2/reports/{report_id}/regenerate"): "regenerate",
    }


async def test_basic_report_policy_never_requires_a_paid_entitlement() -> None:
    db = AsyncMock()

    await _require_basic_report_access(db=db, user_id=uuid4())

    db.execute.assert_not_awaited()


async def test_basic_report_checks_ownership_before_loading_payload() -> None:
    report_id = uuid4()
    user_id = uuid4()
    repository = AsyncMock()
    repository.get_owned_report_chart_id.return_value = uuid4()
    report = SimpleNamespace(id=report_id)
    repository.get_report.return_value = report
    db = AsyncMock()

    loaded = await _load_basic_report_for_user(
        repository=repository,
        db=db,
        report_id=report_id,
        user_id=user_id,
    )

    assert loaded.id == report_id
    repository.get_owned_report_chart_id.assert_awaited_once_with(report_id=report_id, user_id=user_id)
    repository.get_report.assert_awaited_once_with(report_id)
    db.execute.assert_not_awaited()


async def test_foreign_basic_report_is_404_without_payload_read() -> None:
    repository = AsyncMock()
    repository.get_owned_report_chart_id.return_value = None

    with pytest.raises(HTTPException) as missing:
        await _load_basic_report_for_user(
            repository=repository,
            db=AsyncMock(),
            report_id=uuid4(),
            user_id=uuid4(),
        )

    assert missing.value.status_code == 404
    repository.get_report.assert_not_awaited()


def test_router_checks_ownership_metadata_before_loading_report_payload() -> None:
    import inspect

    from app.modules.astrotype_v2 import router as router_module

    source = inspect.getsource(router_module)
    assert "get_owned_report_chart_id" in source
    assert "await _require_basic_report_access" in source
    assert "SELF_REPORT_PRODUCT" not in source
    assert "_require_self_report_access" not in source
    assert "build_locked_product_response" not in source
