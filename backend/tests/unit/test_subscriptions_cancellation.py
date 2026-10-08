"""E6.S13 cancellation, resume, suspension, and grace policy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import ValidationError
from app.modules.subscriptions.models import Subscription, SubscriptionEvent, SubscriptionPlan
from app.modules.subscriptions.service import SubscriptionAccessPolicy, SubscriptionsService

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


class _Repo:
    def __init__(self, subscription: Subscription) -> None:
        self.subscription = subscription
        self.events: dict[str, SubscriptionEvent] = {}

    async def ensure_plan(self, **_values: Any) -> SubscriptionPlan:
        raise AssertionError("not used")

    async def create_subscription(self, **_values: Any) -> Subscription:
        raise AssertionError("not used")

    async def get_subscription(self, subscription_id: UUID, *, for_update: bool = False) -> Subscription | None:
        del for_update
        return self.subscription if self.subscription.id == subscription_id else None

    async def get_latest_for_user(self, user_id: UUID) -> Subscription | None:
        return self.subscription if self.subscription.user_id == user_id else None

    async def append_event(self, **values: Any) -> tuple[SubscriptionEvent, bool]:
        key = str(values["event_key"])
        if key in self.events:
            return self.events[key], False
        event = SubscriptionEvent(**values)
        event.id = uuid4()
        self.events[key] = event
        return event, True


def _subscription() -> Subscription:
    subscription = Subscription(
        user_id=uuid4(),
        plan_id=uuid4(),
        provider="yookassa",
        status="active",
        current_period_start=NOW - timedelta(days=5),
        current_period_end=NOW + timedelta(days=25),
        cancel_at_period_end=False,
        metadata_json={"plan_code": "astrotype_plus_monthly"},
    )
    subscription.id = uuid4()
    return subscription


async def test_cancel_schedules_end_but_preserves_paid_access() -> None:
    subscription = _subscription()
    service = SubscriptionsService(None, repository=_Repo(subscription))  # type: ignore[arg-type]

    result = await service.cancel_at_period_end(
        subscription_id=subscription.id,
        user_id=subscription.user_id,
        reason="user_request",
        now=NOW,
    )

    assert result.status == "cancel_scheduled"
    assert result.cancel_at_period_end is True
    assert result.cancelled_at == NOW
    assert SubscriptionAccessPolicy.is_active(result, now=NOW) is True


async def test_resume_before_expiry_restores_renewal() -> None:
    subscription = _subscription()
    subscription.status = "cancel_scheduled"
    subscription.cancel_at_period_end = True
    service = SubscriptionsService(None, repository=_Repo(subscription))  # type: ignore[arg-type]

    result = await service.resume(
        subscription_id=subscription.id,
        user_id=subscription.user_id,
        now=NOW,
    )

    assert result.status == "active"
    assert result.cancel_at_period_end is False
    assert result.cancelled_at is None


async def test_resume_after_expiry_is_rejected() -> None:
    subscription = _subscription()
    subscription.status = "cancel_scheduled"
    subscription.cancel_at_period_end = True
    subscription.current_period_end = NOW
    service = SubscriptionsService(None, repository=_Repo(subscription))  # type: ignore[arg-type]

    with pytest.raises(ValidationError, match="expired"):
        await service.resume(subscription_id=subscription.id, user_id=subscription.user_id, now=NOW)


async def test_refund_suspends_access_before_natural_expiry() -> None:
    subscription = _subscription()
    service = SubscriptionsService(None, repository=_Repo(subscription))  # type: ignore[arg-type]

    result = await service.suspend(
        subscription_id=subscription.id,
        event_key="refund:refund-1",
        reason="refund_succeeded",
        now=NOW,
    )

    assert result.status == "suspended"
    assert SubscriptionAccessPolicy.is_active(result, now=NOW) is False


def test_past_due_has_no_access_without_explicit_grace() -> None:
    subscription = _subscription()
    subscription.status = "past_due"
    assert SubscriptionAccessPolicy.is_active(subscription, now=NOW) is False

    subscription.grace_until = NOW + timedelta(days=3)
    assert SubscriptionAccessPolicy.is_active(subscription, now=NOW) is True
