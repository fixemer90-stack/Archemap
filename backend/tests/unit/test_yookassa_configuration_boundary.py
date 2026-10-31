"""Provider configuration is a fail-closed boundary, not a failed HTTP attempt."""

from __future__ import annotations

from base64 import b64encode
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

from app.config import settings
from app.core.exceptions import PaymentError
from app.modules.payments.providers.yookassa import YooKassaProvider
from app.modules.payments.service import PaymentsService


async def test_unconfigured_webhook_fails_closed_with_static_public_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.exceptions import ArchemapError
    from app.main import app

    monkeypatch.setattr(settings, "YOOKASSA_SHOP_ID", "")
    monkeypatch.setattr(settings, "YOOKASSA_SECRET_KEY", "")
    client = MagicMock(side_effect=AssertionError("HTTP client must not be constructed"))
    monkeypatch.setattr("app.modules.payments.providers.yookassa.httpx.AsyncClient", client)
    db = MagicMock()
    db.flush = AsyncMock()
    with pytest.raises(PaymentError) as error:
        await PaymentsService(db).handle_webhook(
            provider="yookassa", payload={"event": "payment.succeeded", "object": {"id": "synthetic-payment"}}
        )
    client.assert_not_called()
    db.execute.assert_not_called()
    handler = cast(Any, app.exception_handlers[ArchemapError])
    response = await handler(None, error.value)
    assert response.status_code == 400
    assert response.body == (b'{"detail":"Payment provider is not configured","code":"payment_provider_unconfigured"}')


@pytest.mark.parametrize("operation", ["create", "get", "capture", "cancel"])
@pytest.mark.parametrize(
    "shop_id,secret_key", [("", ""), ("", "sentinel"), ("sentinel", ""), ("  ", "sentinel"), ("sentinel", "\t")]
)
async def test_unconfigured_provider_never_constructs_http_client(
    monkeypatch: pytest.MonkeyPatch, operation: str, shop_id: str, secret_key: str
) -> None:
    monkeypatch.setattr(settings, "YOOKASSA_SHOP_ID", shop_id)
    monkeypatch.setattr(settings, "YOOKASSA_SECRET_KEY", secret_key)
    client = MagicMock(side_effect=AssertionError("HTTP client must not be constructed"))
    monkeypatch.setattr("app.modules.payments.providers.yookassa.httpx.AsyncClient", client)
    provider = YooKassaProvider()
    with pytest.raises(PaymentError, match="Payment provider is not configured") as error:
        if operation == "create":
            await provider.create_payment(100, idempotency_key="synthetic-key")
        elif operation == "get":
            await provider.get_payment("synthetic-payment")
        elif operation == "capture":
            await provider.capture_payment("synthetic-payment", 50, "synthetic-key")
        else:
            await provider.cancel_payment("synthetic-payment", "synthetic-key")
    assert error.value.code == "payment_provider_unconfigured"
    assert str(error.value) == "Payment provider is not configured"
    client.assert_not_called()


@pytest.mark.parametrize("operation", ["create", "get", "capture", "cancel"])
async def test_configured_provider_preserves_http_contract(
    monkeypatch: pytest.MonkeyPatch, operation: str, respx_mock: respx.MockRouter
) -> None:
    monkeypatch.setattr(settings, "YOOKASSA_SHOP_ID", "synthetic-shop")
    monkeypatch.setattr(settings, "YOOKASSA_SECRET_KEY", "synthetic-secret")
    provider = YooKassaProvider()
    path = "/payments" if operation == "create" else "/payments/synthetic-payment"
    if operation in {"capture", "cancel"}:
        path += f"/{operation}"
    method = "GET" if operation == "get" else "POST"
    route = respx_mock.route(method=method, url=f"https://api.yookassa.ru/v3{path}").mock(
        return_value=httpx.Response(200, json={"id": "synthetic-payment", "status": "pending"})
    )
    if operation == "create":
        result = await provider.create_payment(
            100, return_url="https://example.invalid/return", idempotency_key="fixed-key"
        )
    elif operation == "get":
        result = await provider.get_payment("synthetic-payment")
    elif operation == "capture":
        result = await provider.capture_payment("synthetic-payment", 50, "fixed-key")
    else:
        result = await provider.cancel_payment("synthetic-payment", "fixed-key")
    assert result == {"id": "synthetic-payment", "status": "pending"}
    assert route.call_count == 1
    request = route.calls[0].request
    assert request.headers["Authorization"] == "Basic " + b64encode(b"synthetic-shop:synthetic-secret").decode()
    if operation != "get":
        assert request.headers["Idempotence-Key"] == "fixed-key"
    if operation == "create":
        assert request.content == (
            b'{"amount":{"value":"100.00","currency":"RUB"},"capture":true,"description":"",'
            b'"save_payment_method":false,"confirmation":{"type":"redirect","return_url":"https://example.invalid/return"}}'
        )
    elif operation == "capture":
        assert request.content == b'{"amount":{"value":"50.00","currency":"RUB"}}'
    elif operation == "cancel":
        assert request.content == b"{}"
