"""E6.S10 monthly Plus subscription model contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from app.modules.catalog.service import CatalogService
from app.modules.subscriptions.models import Subscription, SubscriptionEvent, SubscriptionPlan
from app.modules.subscriptions.service import SubscriptionsService


class _Repo:
    def __init__(self) -> None:
        self.plan = SubscriptionPlan(
            plan_code="astrotype_plus_monthly",
            display_name="Astrotype Plus",
            amount=999.0,
            currency="RUB",
            billing_interval="month",
            interval_count=1,
            features_json={"products": ["self", "career", "love", "child"]},
        )
        self.plan.id = uuid4()
        self.subscription: Subscription | None = None
        self.events: dict[str, SubscriptionEvent] = {}

    async def ensure_plan(self, **_values: Any) -> SubscriptionPlan:
        return self.plan

    async def create_subscription(self, **values: Any) -> Subscription:
        subscription = Subscription(**values)
        subscription.id = uuid4()
        self.subscription = subscription
        return subscription

    async def get_subscription(self, subscription_id: UUID, *, for_update: bool = False) -> Subscription | None:
        del for_update
        if self.subscription and self.subscription.id == subscription_id:
            return self.subscription
        return None

    async def get_latest_for_user(self, user_id: UUID) -> Subscription | None:
        if self.subscription and self.subscription.user_id == user_id:
            return self.subscription
        return None

    async def append_event(self, **values: Any) -> tuple[SubscriptionEvent, bool]:
        event_key = str(values["event_key"])
        if event_key in self.events:
            return self.events[event_key], False
        event = SubscriptionEvent(**values)
        event.id = uuid4()
        self.events[event_key] = event
        return event, True


class _Payments:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def create_payment(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(
            id=uuid4(),
            status="pending",
            metadata_json={"confirmation_url": "https://pay.example/checkout"},
        )


class _Entitlements:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def grant_paid_product(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(id=uuid4())


class _Tiers:
    async def upgrade_to_plus(self, _user_id: UUID) -> None:
        return None


def test_catalog_defines_server_owned_monthly_plus_plan() -> None:
    plan = CatalogService().get_subscription_plan("astrotype_plus_monthly")

    assert plan.display_name == "Astrotype Plus"
    assert plan.amount == 999.0
    assert plan.currency == "RUB"
    assert plan.billing_interval == "month"
    assert plan.interval_count == 1
    assert plan.products == ("self", "career", "love", "child")


async def test_checkout_creates_incomplete_subscription_shell_without_period() -> None:
    repo = _Repo()
    payments = _Payments()
    service = SubscriptionsService(None, repository=repo, payments=payments)  # type: ignore[arg-type]
    user_id = uuid4()

    result = await service.create_checkout(
        user_id=user_id,
        plan_code="astrotype_plus_monthly",
        return_url="https://app.example/billing?checkout=return",
    )

    assert repo.subscription is not None
    assert repo.subscription.status == "incomplete"
    assert repo.subscription.current_period_start is None
    assert repo.subscription.current_period_end is None
    assert result.subscription_id == repo.subscription.id
    assert result.status == "checkout_pending"
    assert result.confirmation_url == "https://pay.example/checkout"
    assert payments.calls[0]["subscription_id"] == repo.subscription.id
    assert payments.calls[0]["metadata"]["plan_code"] == "astrotype_plus_monthly"


async def test_initial_success_activates_exactly_one_calendar_month_and_period_entitlements() -> None:
    repo = _Repo()
    payments = _Payments()
    entitlements = _Entitlements()
    service = SubscriptionsService(
        None,  # type: ignore[arg-type]
        repository=repo,
        payments=payments,
        entitlements=entitlements,
        tiers=_Tiers(),
    )
    user_id = uuid4()
    checkout = await service.create_checkout(
        user_id=user_id,
        plan_code="astrotype_plus_monthly",
        return_url="https://app.example/billing",
    )
    paid_at = datetime(2026, 1, 31, 12, 0, tzinfo=UTC)
    payment = SimpleNamespace(id=uuid4(), user_id=user_id, payment_method_id="pm_saved", paid_at=paid_at)

    subscription = await service.activate_initial_payment(
        subscription_id=checkout.subscription_id,
        payment=payment,
        provider_event_id="provider-payment-1",
    )
    replay = await service.activate_initial_payment(
        subscription_id=checkout.subscription_id,
        payment=payment,
        provider_event_id="provider-payment-1",
    )

    assert subscription is replay
    assert subscription.status == "active"
    assert subscription.current_period_start == paid_at
    assert subscription.current_period_end == datetime(2026, 2, 28, 12, 0, tzinfo=UTC)
    assert subscription.provider_payment_method_id == "pm_saved"
    assert len(repo.events) == 1
    assert len(entitlements.calls) == 4
    assert {call["product"] for call in entitlements.calls} == {"self", "career", "love", "child"}
    assert all(call["starts_at"] == paid_at for call in entitlements.calls)
    assert all(call["expires_at"] == subscription.current_period_end for call in entitlements.calls)
    assert all(call["metadata"]["subscription_id"] == str(subscription.id) for call in entitlements.calls)
