"""E6.S12 idempotent renewal lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from app.modules.subscriptions.models import Subscription, SubscriptionEvent, SubscriptionPlan
from app.modules.subscriptions.service import SubscriptionsService


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


class _Entitlements:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def grant_paid_product(self, **values: Any) -> SimpleNamespace:
        self.calls.append(values)
        return SimpleNamespace(id=uuid4())


class _Tiers:
    async def upgrade_to_plus(self, _user_id: UUID) -> None:
        return None


def _active_subscription() -> Subscription:
    subscription = Subscription(
        user_id=uuid4(),
        plan_id=uuid4(),
        provider="yookassa",
        status="active",
        current_period_start=datetime(2026, 9, 30, 10, 0, tzinfo=UTC),
        current_period_end=datetime(2026, 10, 31, 10, 0, tzinfo=UTC),
        cancel_at_period_end=False,
        metadata_json={"plan_code": "astrotype_plus_monthly"},
    )
    subscription.id = uuid4()
    return subscription


async def test_renewal_success_extends_one_interval_once() -> None:
    subscription = _active_subscription()
    repo = _Repo(subscription)
    entitlements = _Entitlements()
    service = SubscriptionsService(
        None,  # type: ignore[arg-type]
        repository=repo,
        entitlements=entitlements,
        tiers=_Tiers(),
    )
    payment = SimpleNamespace(id=uuid4(), paid_at=datetime(2026, 10, 31, 10, 0, tzinfo=UTC))

    await service.apply_renewal_success(
        subscription_id=subscription.id,
        payment=payment,
        provider_event_id="renewal-payment-1",
    )
    await service.apply_renewal_success(
        subscription_id=subscription.id,
        payment=payment,
        provider_event_id="renewal-payment-1",
    )

    assert subscription.current_period_end == datetime(2026, 11, 30, 10, 0, tzinfo=UTC)
    assert subscription.status == "active"
    assert len(repo.events) == 1
    assert len(entitlements.calls) == 4
    assert all(call["expires_at"] == subscription.current_period_end for call in entitlements.calls)


async def test_renewal_failure_is_audited_and_never_extends_period() -> None:
    subscription = _active_subscription()
    original_end = subscription.current_period_end
    repo = _Repo(subscription)
    service = SubscriptionsService(None, repository=repo, tiers=_Tiers())  # type: ignore[arg-type]

    await service.apply_renewal_failure(
        subscription_id=subscription.id,
        provider_event_id="renewal-payment-failed",
        reason="payment.canceled",
        effective_at=datetime(2026, 10, 31, 10, 0, tzinfo=UTC),
    )

    assert subscription.current_period_end == original_end
    assert subscription.status == "past_due"
    assert next(iter(repo.events.values())).event_type == "renewal_failed"
