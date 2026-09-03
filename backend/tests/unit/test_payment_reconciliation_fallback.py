"""Regression tests for YooKassa success reconciliation when webhook delivery is missing."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.modules.payments.service import PaymentsService


class _ListScalarResult:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def scalars(self) -> _ListScalarResult:
        return self

    def all(self) -> list[object]:
        return self.values


class _BillingStateDb:
    def __init__(self, payments: list[object], entitlements: list[object]) -> None:
        self.results = [_ListScalarResult(payments), _ListScalarResult(entitlements)]
        self.flushed = 0

    async def execute(self, _query: object) -> _ListScalarResult:
        return self.results.pop(0)

    async def flush(self) -> None:
        self.flushed += 1


def _payment_attempt(status: str = "pending") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        provider="yookassa",
        provider_payment_id="provider-payment-id",
        amount=999.0,
        currency="RUB",
        status=status,
        metadata_json={"product_id": "self_full", "product": "self"},
        paid_at=None,
        failed_at=None,
        cancelled_at=None,
        refunded_at=None,
        error_code=None,
        error_message=None,
        payment_method_type=None,
        created_at=datetime.now(UTC),
    )


def _entitlement(payment: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        product="self",
        status="active",
        starts_at=datetime.now(UTC),
        expires_at=None,
        source_payment_id=payment.id,
    )


def _canonical_yookassa_payment(payment: SimpleNamespace) -> dict[str, object]:
    return {
        "id": payment.provider_payment_id,
        "status": "succeeded",
        "paid": True,
        "amount": {"value": "999.00", "currency": "RUB"},
        "metadata": {
            "payment_id": str(payment.id),
            "user_id": str(payment.user_id),
            "product_id": "self_full",
            "product": "self",
        },
        "payment_method": {"type": "yoo_money"},
    }


@pytest.mark.asyncio
async def test_billing_access_reconciles_pending_yookassa_success_when_webhook_is_missing() -> None:
    payment = _payment_attempt("pending")
    db = _BillingStateDb([payment], [_entitlement(payment)])
    service = PaymentsService(db)  # type: ignore[arg-type]

    with (
        patch(
            "app.modules.payments.service.YooKassaProvider.get_payment",
            new=AsyncMock(return_value=_canonical_yookassa_payment(payment)),
        ) as get_payment,
        patch(
            "app.modules.payments.service.EntitlementsService.grant_paid_product",
            new=AsyncMock(return_value=MagicMock(id=uuid4())),
        ) as grant,
        patch(
            "app.modules.payments.service.AccountTierService.upgrade_to_plus",
            new=AsyncMock(return_value=MagicMock(id=payment.user_id)),
        ) as upgrade,
    ):
        state = await service.get_billing_access_state(user_id=payment.user_id)

    get_payment.assert_awaited_once_with("provider-payment-id")
    grant.assert_awaited_once_with(
        user_id=payment.user_id,
        product="self",
        source_payment_id=payment.id,
        metadata={"product_id": "self_full"},
    )
    upgrade.assert_awaited_once_with(payment.user_id)
    assert payment.status == "succeeded"
    assert payment.paid_at is not None
    assert payment.payment_method_type == "yoo_money"
    assert state.access_state == "plus_active"
    assert state.account_tier == "plus"


def test_v2_report_access_gate_reconciles_pending_payment_before_locking() -> None:
    router_source = "app/modules/astrotype_v2/router.py"
    from pathlib import Path

    source = Path(router_source).read_text()

    assert "PaymentsService(db).reconcile_latest_pending_provider_payment" in source
    assert source.index("reconcile_latest_pending_provider_payment") < source.index(
        "EntitlementsService(db).has_active_product_access"
    )
