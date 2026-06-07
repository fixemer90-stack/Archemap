"""Unit tests for payment safety boundaries and entitlement lifecycle."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError
from starlette.requests import Request

from app.modules.payments.router import yookassa_webhook
from app.modules.payments.schemas import CreatePaymentRequest
from app.modules.payments.service import PaymentsService


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object:
        return self.value


class _FakeDb:
    def __init__(self, payment: object | None = None) -> None:
        self.payment = payment
        self.added: list[object] = []
        self.flushed = 0

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        self.flushed += 1

    async def execute(self, _query: object) -> _ScalarResult:
        return _ScalarResult(self.payment)


def _request_with_json(payload: dict[str, object]) -> Request:
    body = json.dumps(payload).encode()
    sent = False

    async def receive() -> dict[str, object]:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/payments/webhooks/yookassa",
            "headers": [],
        },
        receive,
    )


def test_create_payment_request_rejects_client_controlled_amount() -> None:
    """Client must send product_id, never commercial price fields."""
    with pytest.raises(PydanticValidationError):
        CreatePaymentRequest.model_validate(
            {
                "product_id": "self_full",
                "amount": 1.0,
                "currency": "RUB",
                "description": "cheap hacked payment",
                "metadata": {"product": "career"},
            }
        )


async def test_create_payment_for_product_uses_server_catalog_price() -> None:
    db = _FakeDb()
    service = PaymentsService(db)  # type: ignore[arg-type]

    with patch.object(
        service,
        "_create_yookassa_payment",
        new=AsyncMock(
            return_value={
                "id": "provider-payment-id",
                "status": "pending",
                "confirmation": {"type": "redirect", "confirmation_url": "https://pay.example"},
            }
        ),
    ) as create_provider_payment:
        payment = await service.create_payment_for_product(
            user_id=uuid4(),
            product_id="self_full",
            return_url="https://app.example/thanks",
        )

    assert payment.amount == 990.0
    assert payment.currency == "RUB"
    assert payment.description == "Astrotype Self — полный отчёт"
    assert payment.metadata_json is not None
    assert payment.metadata_json["product_id"] == "self_full"
    assert payment.metadata_json["product"] == "self"
    create_provider_payment.assert_awaited_once()


async def test_yookassa_webhook_acknowledges_invalid_signature_and_processes_payload() -> None:
    """YooKassa docs require HTTP 200 acknowledgement; authenticity is status/IP based, not HMAC."""
    request = _request_with_json(
        {
            "type": "notification",
            "event": "payment.succeeded",
            "object": {"id": "provider-payment-id", "status": "succeeded", "amount": {"value": "990.00"}},
        }
    )

    with patch(
        "app.modules.payments.router.PaymentsService.handle_webhook",
        new=AsyncMock(
            return_value={
                "processed": True,
                "payment_id": "local-id",
                "status": "succeeded",
                "message": "ok",
            }
        ),
    ) as handle:
        response = await yookassa_webhook(request=request, db=AsyncMock())

    assert getattr(response, "status_code", 200) == 200
    handle.assert_awaited_once()


async def test_successful_yookassa_webhook_grants_product_entitlement() -> None:
    payment = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        provider="yookassa",
        provider_payment_id="provider-payment-id",
        amount=990.0,
        currency="RUB",
        status="pending",
        metadata_json={"product_id": "self_full", "product": "self"},
        paid_at=None,
        failed_at=None,
        cancelled_at=None,
        error_code=None,
        payment_method_type=None,
    )
    service = PaymentsService(_FakeDb(payment))  # type: ignore[arg-type]

    with (
        patch(
            "app.modules.payments.service.YooKassaProvider.get_payment",
            new=AsyncMock(
                return_value={
                    "id": "provider-payment-id",
                    "status": "succeeded",
                    "amount": {"value": "990.00", "currency": "RUB"},
                    "payment_method": {"type": "bank_card"},
                }
            ),
        ),
        patch(
            "app.modules.payments.service.EntitlementsService.grant_paid_product",
            new=AsyncMock(return_value=MagicMock(id=uuid4())),
        ) as grant,
    ):
        result = await service.handle_webhook(
            provider="yookassa",
            payload={
                "event": "payment.succeeded",
                "object": {
                    "id": "provider-payment-id",
                    "status": "succeeded",
                    "amount": {"value": "990.00", "currency": "RUB"},
                    "payment_method": {"type": "bank_card"},
                },
            },
        )

    assert result["processed"] is True
    assert payment.status == "succeeded"
    grant.assert_awaited_once_with(
        user_id=payment.user_id,
        product="self",
        source_payment_id=payment.id,
        metadata={"product_id": "self_full"},
    )
