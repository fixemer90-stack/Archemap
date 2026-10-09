"""E6.S11 subscription expiry and access-control contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from app.modules.authorization.service import EntitlementsService
from app.modules.subscriptions.service import SubscriptionAccessPolicy

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


def _subscription(**overrides: Any) -> SimpleNamespace:
    values: dict[str, Any] = {
        "id": uuid4(),
        "status": "active",
        "current_period_start": NOW - timedelta(days=1),
        "current_period_end": NOW + timedelta(days=1),
        "grace_until": None,
        "cancel_at_period_end": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_access_policy_enforces_inclusive_start_and_exclusive_end() -> None:
    assert SubscriptionAccessPolicy.is_active(_subscription(), now=NOW) is True
    assert SubscriptionAccessPolicy.is_active(_subscription(current_period_start=NOW), now=NOW) is True
    assert (
        SubscriptionAccessPolicy.is_active(_subscription(current_period_start=NOW + timedelta(seconds=1)), now=NOW)
        is False
    )
    assert SubscriptionAccessPolicy.is_active(_subscription(current_period_end=NOW), now=NOW) is False
    assert (
        SubscriptionAccessPolicy.is_active(_subscription(current_period_end=NOW - timedelta(seconds=1)), now=NOW)
        is False
    )
    assert SubscriptionAccessPolicy.is_active(_subscription(status="suspended"), now=NOW) is False
    assert SubscriptionAccessPolicy.is_active(_subscription(status="cancel_scheduled"), now=NOW) is True


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object:
        return self.value


class _EntitlementDb:
    def __init__(self, entitlement: object, subscription: object) -> None:
        self.values = [entitlement, subscription]

    async def execute(self, _query: object) -> _ScalarResult:
        return _ScalarResult(self.values.pop(0))


async def test_subscription_entitlement_requires_live_subscription_not_account_tier() -> None:
    subscription_id = uuid4()
    entitlement = SimpleNamespace(
        product="career",
        status="active",
        expires_at=NOW + timedelta(days=10),
        metadata_json={"subscription_id": str(subscription_id)},
    )
    db = _EntitlementDb(entitlement, _subscription(id=subscription_id, current_period_end=NOW))
    service = EntitlementsService(db, now=lambda: NOW)  # type: ignore[arg-type]

    assert await service.has_active_product_access(uuid4(), "career") is False


async def test_historical_direct_purchase_remains_valid_without_subscription_metadata() -> None:
    entitlement = SimpleNamespace(
        product="self",
        status="active",
        expires_at=None,
        metadata_json={"product_id": "self_full"},
    )

    class _DirectDb:
        async def execute(self, _query: object) -> _ScalarResult:
            return _ScalarResult(entitlement)

    service = EntitlementsService(_DirectDb(), now=lambda: NOW)  # type: ignore[arg-type]

    assert await service.has_active_product_access(uuid4(), "self") is True
