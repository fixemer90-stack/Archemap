from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.routing import APIRoute

from app.config import Settings
from app.core.exceptions import ValidationError
from app.modules.catalog.service import PRODUCT_CATALOG, CatalogService


@pytest.mark.asyncio
async def test_career_access_requires_backend_plus_or_grandfathered_entitlement() -> None:
    from app.modules.career.access import CareerAccessPolicy

    user_id = uuid4()
    entitlements = AsyncMock()
    entitlements.has_active_plus_access.side_effect = [False]
    entitlements.has_active_product_access.side_effect = [False]

    denied = await CareerAccessPolicy(entitlements).check(user_id)

    assert denied.allowed is False
    assert denied.reason == "missing_career_access"
    entitlements.has_active_plus_access.assert_awaited_once_with(user_id=user_id)
    assert entitlements.has_active_product_access.await_args_list[0].kwargs == {
        "user_id": user_id,
        "product": "career",
    }

    entitlements.reset_mock()
    entitlements.has_active_plus_access.side_effect = [True]
    plus = await CareerAccessPolicy(entitlements).check(user_id)
    assert plus.allowed is True
    assert plus.source == "plus"

    entitlements.reset_mock()
    entitlements.has_active_plus_access.side_effect = [False]
    entitlements.has_active_product_access.side_effect = [True]
    grandfathered = await CareerAccessPolicy(entitlements).check(user_id)
    assert grandfathered.allowed is True
    assert grandfathered.source == "legacy_career"


def test_career_product_contract_is_canonical_and_legacy_sku_is_not_purchasable() -> None:
    from app.modules.career.contracts import CAREER_ACCESS_CLASS, CAREER_REPORT_TYPE, LEGACY_CAREER_SKU

    report = CatalogService().get_report(CAREER_REPORT_TYPE)
    assert CAREER_REPORT_TYPE == report.report_type == "career"
    assert CAREER_ACCESS_CLASS == report.access_class == "plus_only"
    assert LEGACY_CAREER_SKU in report.commercial_skus
    assert PRODUCT_CATALOG[LEGACY_CAREER_SKU].purchasable is False

    with pytest.raises(ValidationError, match="retired"):
        CatalogService().get_product(LEGACY_CAREER_SKU)


def test_career_access_matrix_and_migration_boundary_are_explicit() -> None:
    from app.modules.career.contracts import CAREER_ACCESS_MATRIX, LEGACY_PAYLOAD_FALLBACK_ALLOWED

    assert set(CAREER_ACCESS_MATRIX) == {
        "create",
        "questionnaire",
        "generate",
        "read",
        "regenerate",
        "versions",
        "pdf",
    }
    assert all(rule.requires_ownership for rule in CAREER_ACCESS_MATRIX.values())
    assert all(rule.requires_target_access for rule in CAREER_ACCESS_MATRIX.values())
    assert LEGACY_PAYLOAD_FALLBACK_ALLOWED is False


def test_every_runtime_career_route_has_an_explicit_access_operation_contract() -> None:
    from app.modules.career.contracts import CAREER_ROUTE_ACCESS_CONTRACT
    from app.modules.career.router import router

    runtime_routes = {
        (method, f"/v1{route.path}"): getattr(route.endpoint, "__career_access_operation__", None)
        for route in router.routes
        if isinstance(route, APIRoute)
        for method in route.methods or set()
        if method != "HEAD"
    }

    assert runtime_routes == {
        ("GET", "/v1/career/questionnaires/current"): "questionnaire",
        ("PUT", "/v1/career/questionnaires/{session_id}/answers"): "questionnaire",
        ("POST", "/v1/career/questionnaires/{session_id}/complete"): "questionnaire",
        ("POST", "/v1/career/reports"): "create",
        ("GET", "/v1/career/generations/{generation_id}"): "generate",
        ("GET", "/v1/career/reports/{report_id}"): "read",
        ("GET", "/v1/career/reports/{report_id}/sections"): "read",
        ("POST", "/v1/career/reports/{report_id}/regenerate"): "regenerate",
        ("GET", "/v1/career/reports/{report_id}/versions"): "versions",
        ("GET", "/v1/career/reports/{report_id}/pdf"): "pdf",
    }
    assert runtime_routes == {(route.method, route.path): route.operation for route in CAREER_ROUTE_ACCESS_CONTRACT}


@pytest.mark.asyncio
async def test_career_report_payload_is_loaded_only_after_ownership_and_access() -> None:
    from app.modules.career.router import _load_authorized_career_report

    report_id = uuid4()
    user_id = uuid4()
    report = SimpleNamespace(id=report_id)
    repository = AsyncMock()
    events: list[str] = []

    async def get_owned_report_id(*, report_id: UUID, user_id: UUID) -> UUID:
        events.append("ownership")
        return report_id

    async def require_access() -> None:
        events.append("access")

    async def get_report(report_id: UUID) -> object:
        events.append("payload")
        return report

    repository.get_owned_report_id.side_effect = get_owned_report_id
    repository.get_report.side_effect = get_report

    loaded = await _load_authorized_career_report(
        repository,
        report_id=report_id,
        user_id=user_id,
        require_access=require_access,
    )

    assert loaded.id == report_id
    repository.get_owned_report_id.assert_awaited_once_with(report_id=report_id, user_id=user_id)
    repository.get_report.assert_awaited_once_with(report_id)
    assert events == ["ownership", "access", "payload"]


@pytest.mark.asyncio
async def test_foreign_career_report_is_404_without_access_or_payload_read() -> None:
    from fastapi import HTTPException

    from app.modules.career.router import _load_authorized_career_report

    repository = AsyncMock()
    repository.get_owned_report_id.return_value = None
    require_access = AsyncMock()

    with pytest.raises(HTTPException) as missing:
        await _load_authorized_career_report(
            repository,
            report_id=uuid4(),
            user_id=uuid4(),
            require_access=require_access,
        )

    assert missing.value.status_code == 404
    require_access.assert_not_awaited()
    repository.get_report.assert_not_awaited()


def test_career_rollout_flag_is_off_by_default() -> None:
    assert Settings.model_fields["CAREER_REPORT_ENABLED"].default is False


def test_disabled_career_surface_reports_a_stable_404_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi import HTTPException

    from app.config import settings
    from app.modules.career.router import _require_feature_enabled

    monkeypatch.setattr(settings, "CAREER_REPORT_ENABLED", False)
    with pytest.raises(HTTPException) as disabled:
        _require_feature_enabled()

    assert disabled.value.status_code == 404
    # The product page branches on this exact detail so a disabled Career surface is
    # never reported to the user as "no natal chart yet, build the main report first".
    assert disabled.value.detail == "Career report is not enabled"

    monkeypatch.setattr(settings, "CAREER_REPORT_ENABLED", True)
    _require_feature_enabled()  # an enabled surface must not raise
