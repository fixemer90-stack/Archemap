"""Unit tests for payment safety boundaries and entitlement lifecycle."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import configure_mappers
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


def _payment(metadata_json: dict[str, object] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        provider="yookassa",
        provider_payment_id="provider-payment-id",
        amount=999.0,
        currency="RUB",
        status="pending",
        metadata_json=metadata_json or {"product_id": "self_full", "product": "self"},
        paid_at=None,
        failed_at=None,
        cancelled_at=None,
        error_code=None,
        payment_method_type=None,
    )


def _canonical_yookassa_payment(
    payment: SimpleNamespace,
    *,
    paid: bool = True,
    user_id: str | None = None,
) -> dict[str, object]:
    return {
        "id": "provider-payment-id",
        "status": "succeeded",
        "paid": paid,
        "amount": {"value": "999.00", "currency": "RUB"},
        "metadata": {
            "payment_id": str(payment.id),
            "user_id": user_id or str(payment.user_id),
            "product_id": "self_full",
            "product": "self",
        },
        "payment_method": {"type": "bank_card"},
    }


def test_payment_mapper_matches_existing_schema_without_subscription_table() -> None:
    """Payment mapper must not reference a non-existent subscriptions table."""
    configure_mappers()


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


def test_create_payment_request_public_contract_is_product_only() -> None:
    fields = set(CreatePaymentRequest.model_fields)

    assert fields == {"product_id", "return_url"}
    assert CreatePaymentRequest.model_config.get("extra") == "forbid"


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

    assert payment.amount == 999.0
    assert payment.currency == "RUB"
    assert payment.description == "Astrotype Plus — полный доступ"
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
            "object": {"id": "provider-payment-id", "status": "succeeded", "amount": {"value": "999.00"}},
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
    payment = _payment()
    service = PaymentsService(_FakeDb(payment))  # type: ignore[arg-type]

    with (
        patch(
            "app.modules.payments.service.YooKassaProvider.get_payment",
            new=AsyncMock(return_value=_canonical_yookassa_payment(payment)),
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
                    "amount": {"value": "999.00", "currency": "RUB"},
                    "metadata": {
                        "payment_id": str(payment.id),
                        "user_id": str(payment.user_id),
                        "product_id": "self_full",
                        "product": "self",
                    },
                    "payment_method": {"type": "bank_card"},
                    "paid": True,
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


async def test_yookassa_webhook_rejects_metadata_mismatch() -> None:
    payment = _payment()
    db = _FakeDb(payment)
    service = PaymentsService(db)  # type: ignore[arg-type]

    with (
        patch(
            "app.modules.payments.service.YooKassaProvider.get_payment",
            new=AsyncMock(return_value=_canonical_yookassa_payment(payment, user_id=str(uuid4()))),
        ),
        patch(
            "app.modules.payments.service.EntitlementsService.grant_paid_product",
            new=AsyncMock(return_value=MagicMock(id=uuid4())),
        ) as grant,
    ):
        result = await service.handle_webhook(
            provider="yookassa",
            payload={"event": "payment.succeeded", "object": {"id": "provider-payment-id"}},
        )

    webhook = cast(Any, db.added[0])
    assert result["processed"] is False
    assert result["message"] == "Payment payload mismatch"
    assert webhook.error_message == "Payment payload mismatch"
    assert payment.status == "pending"
    grant.assert_not_awaited()


async def test_yookassa_webhook_rejects_succeeded_without_paid_true() -> None:
    payment = _payment()
    service = PaymentsService(_FakeDb(payment))  # type: ignore[arg-type]

    with (
        patch(
            "app.modules.payments.service.YooKassaProvider.get_payment",
            new=AsyncMock(return_value=_canonical_yookassa_payment(payment, paid=False)),
        ),
        patch(
            "app.modules.payments.service.EntitlementsService.grant_paid_product",
            new=AsyncMock(return_value=MagicMock(id=uuid4())),
        ) as grant,
    ):
        result = await service.handle_webhook(
            provider="yookassa",
            payload={"event": "payment.succeeded", "object": {"id": "provider-payment-id"}},
        )

    assert result["processed"] is False
    assert result["message"] == "Payment payload mismatch"
    assert payment.status == "pending"
    assert payment.paid_at is None
    grant.assert_not_awaited()


async def test_yookassa_webhook_records_provider_reconciliation_failure() -> None:
    db = _FakeDb()
    service = PaymentsService(db)  # type: ignore[arg-type]

    with (
        patch(
            "app.modules.payments.service.YooKassaProvider.get_payment",
            new=AsyncMock(side_effect=httpx.HTTPError("provider unavailable")),
        ),
        pytest.raises(httpx.HTTPError),
    ):
        await service.handle_webhook(
            provider="yookassa",
            payload={"event": "payment.succeeded", "object": {"id": "provider-payment-id"}},
        )

    webhook = cast(Any, db.added[0])
    assert webhook.processed is False
    assert webhook.processed_at is None
    assert webhook.error_message == "Provider reconciliation failed"
