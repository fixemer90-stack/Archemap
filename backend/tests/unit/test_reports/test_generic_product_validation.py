"""Generic product identifiers are exact catalog values, never filesystem paths."""

from collections.abc import Awaitable, Callable
from typing import Any, cast, get_args
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.exceptions import ValidationError
from app.core.products import GenericProduct, validate_generic_product
from app.dependencies import get_current_user
from app.main import app
from app.modules.charts.models import ChartSnapshot
from app.modules.reports import router as reports_router
from app.modules.reports.schemas import GenerateReportRequest
from app.modules.reports.service import ReportService
from app.modules.rules.schemas import InterpretRequest
from app.modules.rules.service import RulesService
from tests.unit.test_reports.test_reports import make_chart_data

INVALID_PRODUCTS: list[object] = [
    "career/.",
    "career/",
    "self/../career",
    "/career",
    "/absolute/career",
    "../career",
    r"career\.",
    r"self\..\career",
    "career/%2e",
    "self/%2e%2e/career",
    "career%2f.",
    "career%252f.",
    "CAREER",
    "Self",
    " career",
    "career ",
    "unknown",
    "",
    None,
    1,
    True,
    [],
    {},
]
ENDPOINTS = ["/api/v1/rules/interpret", "/api/v1/reports/generate"]


@pytest.mark.asyncio
async def test_rules_rejects_career_path_alias_before_sql() -> None:
    db = MagicMock()
    db.execute = AsyncMock(side_effect=AssertionError("invalid product reached SQL"))
    with pytest.raises(ValidationError, match="Unsupported product identifier"):
        await RulesService(db).interpret_chart(uuid4(), uuid4(), product="career/.")
    db.execute.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("product", INVALID_PRODUCTS)
@pytest.mark.parametrize("service_type", [RulesService, ReportService])
async def test_direct_services_reject_invalid_products_before_work(
    product: object, service_type: type[RulesService] | type[ReportService], monkeypatch: pytest.MonkeyPatch
) -> None:
    db = MagicMock()
    db.execute = AsyncMock(side_effect=AssertionError("no SQL"))
    db.flush = AsyncMock(side_effect=AssertionError("no mutations"))
    forbidden = MagicMock(side_effect=AssertionError("no chart/features/rules/render work"))
    module = "rules" if service_type is RulesService else "reports"
    for name in ("extract_features", "load_ruleset", "render_full_report", "_dict_to_chart"):
        monkeypatch.setattr(f"app.modules.{module}.service.{name}", forbidden)
    service = service_type(db)
    entry: Callable[..., Awaitable[object]]
    if isinstance(service, RulesService):
        entry = service.interpret_chart
        lookup = AsyncMock(side_effect=AssertionError("no snapshot lookup"))
        monkeypatch.setattr(service, "_get_snapshot", lookup)
    else:
        entry = service.generate_report
        lookup = AsyncMock(side_effect=AssertionError("no existing report lookup"))
        monkeypatch.setattr(service, "_find_existing", lookup)
    with pytest.raises(ValidationError) as exc:
        await entry(uuid4(), uuid4(), product=cast(Any, product))
    assert exc.value.code == "unsupported_product"
    assert exc.value.message == "Unsupported product identifier"
    lookup.assert_not_called()
    forbidden.assert_not_called()
    db.execute.assert_not_called()
    db.add.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("product", INVALID_PRODUCTS)
@pytest.mark.parametrize("endpoint", ENDPOINTS)
async def test_http_rejects_invalid_products_before_service_or_sql(
    client: AsyncClient, product: object, endpoint: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    app.dependency_overrides[get_current_user] = lambda: uuid4()
    forbidden = AsyncMock(side_effect=AssertionError("invalid request reached service"))
    monkeypatch.setattr(RulesService, "interpret_chart", forbidden)
    monkeypatch.setattr(ReportService, "assert_profile_owned", forbidden)
    monkeypatch.setattr(ReportService, "generate_report", forbidden)
    response = await client.post(endpoint, json={"profile_id": str(uuid4()), "product": product})
    assert response.status_code == 422, response.text
    assert response.json()["detail"][0]["loc"] == ["body", "product"]
    forbidden.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ENDPOINTS)
async def test_http_literal_career_still_returns_structured_retirement(
    client: AsyncClient, endpoint: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    app.dependency_overrides[get_current_user] = lambda: uuid4()
    monkeypatch.setattr(ReportService, "assert_profile_owned", AsyncMock())
    monkeypatch.setattr(reports_router, "_require_legacy_report_access", AsyncMock())
    response = await client.post(endpoint, json={"profile_id": str(uuid4()), "product": "career"})
    assert response.status_code == 410, response.text
    assert response.json()["detail"] == {
        "code": "legacy_career_generation_retired",
        "message": "Career reports are created through the Career product flow.",
        "target_path": "/products/career",
    }


@pytest.mark.asyncio
async def test_http_self_interprets_real_rules(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: uuid4()
    # Earth + fixed deliberately activates real Self rules (not an empty interpretation).
    chart_data = make_chart_data()
    chart_data["planets"][0].update(sign="Taurus", longitude=40.0)
    monkeypatch.setattr(RulesService, "_get_snapshot", AsyncMock(return_value=ChartSnapshot(chart_data=chart_data)))
    response = await client.post(ENDPOINTS[0], json={"profile_id": str(uuid4()), "product": "self"})
    assert response.status_code == 200, response.text
    assert response.json()["product"] == "self"
    assert response.json()["claims"]
    assert response.json()["all_archetype_scores"]


@pytest.mark.parametrize("product", get_args(GenericProduct))
def test_canonical_products_remain_parseable(product: str) -> None:
    validate_generic_product(product)
    for schema in (InterpretRequest, GenerateReportRequest):
        assert schema.model_validate({"profile_id": str(uuid4()), "product": product}).product == product


def test_runtime_request_schemas_publish_canonical_product_enum() -> None:
    for name in ("InterpretRequest", "GenerateReportRequest"):
        product = app.openapi()["components"]["schemas"][name]["properties"]["product"]
        assert product["enum"] == ["self", "love", "child", "career"]
        assert product["default"] == "self"
