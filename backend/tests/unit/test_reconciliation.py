"""E6.S15 support read and manual reconciliation contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import ValidationError
from app.modules.admin.service import AdminService, SubscriptionSupportData
from app.modules.subscriptions.models import SubscriptionEvent

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


class _Repo:
    def __init__(self, data: SubscriptionSupportData) -> None:
        self.data = data
        self.events: dict[str, SubscriptionEvent] = {}

    async def get_subscription_support_by_email(self, email: str) -> SubscriptionSupportData | None:
        return self.data if email == self.data.email else None

    async def append_subscription_event(self, **values: Any) -> tuple[SubscriptionEvent, bool]:
        key = str(values["event_key"])
        event = SubscriptionEvent(**values)
        event.id = uuid4()
        self.events[key] = event
        return event, True


class _Payments:
    def __init__(self) -> None:
        self.user_ids: list[UUID] = []

    async def reconcile_latest_pending_provider_payment(self, user_id: UUID) -> None:
        self.user_ids.append(user_id)


def _data() -> SubscriptionSupportData:
    return SubscriptionSupportData(
        user_id=uuid4(),
        email="support-target@example.com",
        subscription_id=uuid4(),
        plan_code="astrotype_plus_monthly",
        display_name="Astrotype Plus",
        status="active",
        current_period_start=NOW - timedelta(days=5),
        current_period_end=NOW + timedelta(days=25),
        cancel_at_period_end=False,
        next_billing_at=NOW + timedelta(days=25),
        latest_payment_id=uuid4(),
        latest_payment_status="succeeded",
        events=(
            SimpleNamespace(
                event_type="initial_payment_succeeded",
                effective_at=NOW - timedelta(days=5),
                provider_event_id="provider-payment-1",
                payload_json={"payment_id": "safe-id"},
            ),
        ),
    )


async def test_support_summary_exposes_period_payment_and_audit_events() -> None:
    data = _data()
    service = AdminService(None, repository=_Repo(data), payments=_Payments())  # type: ignore[arg-type]

    summary = await service.get_subscription_support(email=data.email)

    assert summary.email == data.email
    assert summary.plan_code == "astrotype_plus_monthly"
    assert summary.current_period_end == data.current_period_end
    assert summary.next_billing_at == data.next_billing_at
    assert summary.latest_payment_status == "succeeded"
    assert summary.events[0].event_type == "initial_payment_succeeded"


async def test_manual_reconciliation_requires_reason_and_records_operator_audit() -> None:
    data = _data()
    repo = _Repo(data)
    payments = _Payments()
    operator_id = uuid4()
    service = AdminService(None, repository=repo, payments=payments)  # type: ignore[arg-type]

    with pytest.raises(ValidationError, match="reason"):
        await service.reconcile_subscription(email=data.email, reason="  ", operator_user_id=operator_id)

    summary = await service.reconcile_subscription(
        email=data.email,
        reason="support ticket BILL-42",
        operator_user_id=operator_id,
    )

    assert summary.subscription_id == str(data.subscription_id)
    assert payments.user_ids == [data.user_id]
    event = next(iter(repo.events.values()))
    assert event.event_type == "manual_reconciliation_requested"
    assert event.payload_json == {
        "reason": "support ticket BILL-42",
        "operator_user_id": str(operator_id),
    }
