"""First-party-only collector request boundary; no provider or persistent services."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.infrastructure.redis import get_redis_client
from app.modules.analytics import collector

ORIGIN = "http://localhost:3000"
HEADERS = {"origin": ORIGIN, "x-analytics-request": "1", "content-type": "application/json"}


@pytest.fixture
def collector_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    app = FastAPI()
    app.include_router(collector.router)
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", [ORIGIN])
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    return app


@pytest.fixture
async def client(collector_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=collector_app), base_url=ORIGIN) as session:
        yield session


@pytest.mark.parametrize("header", ["origin", "x-analytics-request"])
async def test_missing_csrf_rejected_before_auth(client: AsyncClient, header: str) -> None:
    response = await client.post(
        "/analytics/events", headers={k: v for k, v in HEADERS.items() if k != header}, json={}
    )
    assert response.status_code == 403


async def test_cross_origin_and_flag_off(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    assert (
        await client.post("/analytics/events", headers={**HEADERS, "origin": "https://wrong.test"}, json={})
    ).status_code == 403
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", False)
    assert (await client.post("/analytics/events", headers=HEADERS, json={})).status_code == 404


@pytest.mark.parametrize(
    ("body", "status"),
    [
        (b"{" + b" " * 1024 + b"}", 413),
        (b'{"duplicate":0,"duplicate":1}', 422),
        (b'{"event":"payment_confirmed"}', 422),
        (b'{"event":"report_ready"}', 422),
        (
            b'{"event":"report_opened","product":"child",'
            b'"report_id":"00000000-0000-0000-0000-000000000001","email":"PRIVATE_SENTINEL"}',
            422,
        ),
        (b'{"event":"report_opened","product":"child","report_id":"00000000-0000-0000-0000-000000000001"}', 401),
    ],
)
async def test_invalid_requests_are_bounded_and_not_echoed(client: AsyncClient, body: bytes, status: int) -> None:
    response = await client.post("/analytics/events", headers=HEADERS, content=body)
    assert response.status_code == status
    assert "PRIVATE_SENTINEL" not in response.text
    assert response.headers["cache-control"] == "private, no-store"


async def test_owner_not_taken_from_payload(
    client: AsyncClient, collector_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = UUID(int=7)
    report = UUID(int=9)
    collector_app.dependency_overrides[get_current_user] = lambda: owner
    collector_app.dependency_overrides[get_db] = lambda: None
    collector_app.dependency_overrides[get_redis_client] = lambda: None
    observe = AsyncMock(return_value=True)
    monkeypatch.setattr(collector, "observe_owned_report", observe)
    monkeypatch.setattr(collector, "_limit", AsyncMock())
    body = {"event": "report_opened", "report_id": str(report), "product": "self"}
    assert (
        await client.post("/analytics/events", headers=HEADERS, json={**body, "owner_id": str(UUID(int=8))})
    ).status_code == 422
    assert (await client.post("/analytics/events", headers=HEADERS, json=body)).status_code == 204
    observe.assert_awaited_once_with(None, owner_id=owner, product="self", report_id=report)


@pytest.mark.parametrize(
    "body",
    [
        {"granted": 1},
        {"granted": False},
        {"policy_version": "fixture-v1\n"},
        {"client_id": 123},
        {"client_id": "123\n"},
        {"client_id": "PRIVATE@example.test"},
        {"occurred_at": "2020-01-01"},
    ],
)
async def test_capture_rejects_nonconforming_app_claims(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, body: dict[str, object]
) -> None:
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_APPROVED", "true")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_VERSION", "fixture-v1")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_RETENTION_DAYS", "3")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_COUNTER_ID", "123")
    rate = AsyncMock()
    monkeypatch.setattr(collector, "_limit", rate)
    response = await client.post(
        "/analytics/attribution/capture",
        headers=HEADERS,
        json={"granted": True, "policy_version": "fixture-v1", "client_id": None, **body},
    )
    assert response.status_code == 422
    assert "PRIVATE" not in response.text
    rate.assert_not_awaited()


def test_runtime_openapi_exposes_only_registered_event() -> None:
    from app.main import app

    route = app.openapi()["paths"]["/api/v1/analytics/events"]["post"]
    schema = route["requestBody"]["content"]["application/json"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["event"]["const"] == "report_opened"
    assert set(schema["properties"]) == {"event", "report_id", "product"}


async def test_expired_receipt_timestamp_returns_404_even_if_redis_has_it(
    client: AsyncClient, collector_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_APPROVED", "true")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_VERSION", "fixture-v1")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_RETENTION_DAYS", "3")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_COUNTER_ID", "123")
    collector_app.dependency_overrides[get_current_user] = lambda: UUID(int=7)
    collector_app.dependency_overrides[get_db] = lambda: None
    cache = AsyncMock()
    cache.getdel.return_value = collector.Pending(
        counter_id=123,
        policy_version="fixture-v1",
        client_id=None,
        captured_at=datetime.now(UTC) - timedelta(minutes=31),
    ).model_dump_json()
    collector_app.dependency_overrides[get_redis_client] = lambda: cache
    monkeypatch.setattr(collector, "_limit", AsyncMock())
    bind = AsyncMock(return_value=False)
    monkeypatch.setattr(collector, "bind_attribution", bind)
    response = await client.post("/analytics/attribution/attach", headers=HEADERS, json={"receipt": "r" * 43})
    assert response.status_code == 404
    assert response.headers["cache-control"] == "private, no-store"
    bind.assert_not_awaited()


@pytest.mark.parametrize("source", [{}, {"source_counter_id": "456"}])
async def test_known_observation_requires_approved_source_counter(
    client: AsyncClient, collector_app: FastAPI, monkeypatch: pytest.MonkeyPatch, source: dict[str, str]
) -> None:
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_APPROVED", "true")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_VERSION", "fixture-v1")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_RETENTION_DAYS", "3")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_COUNTER_ID", "123")
    cache = AsyncMock()
    collector_app.dependency_overrides[get_redis_client] = lambda: cache
    monkeypatch.setattr(collector, "_limit", AsyncMock())
    response = await client.post(
        "/analytics/attribution/capture",
        headers=HEADERS,
        json={"granted": True, "policy_version": "fixture-v1", "client_id": "9876", **source},
    )
    assert response.status_code == 404
    cache.set.assert_not_awaited()
