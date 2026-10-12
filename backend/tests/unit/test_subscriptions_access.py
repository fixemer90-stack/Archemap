"""E6.S11 subscription expiry and access-control contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from app.modules.authorization.service import EntitlementsService
from app.modules.catalog.service import CatalogService
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

    def scalars(self) -> _ScalarResult:
        return self

    def all(self) -> list[object]:
        return [] if self.value is None else [self.value]

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


async def test_future_direct_entitlement_is_not_active_before_starts_at() -> None:
    entitlement = SimpleNamespace(
        product="career",
        status="active",
        starts_at=NOW + timedelta(seconds=1),
        expires_at=None,
        metadata_json={},
    )

    class _DirectDb:
        async def execute(self, _query: object) -> _ScalarResult:
            return _ScalarResult(entitlement)

    service = EntitlementsService(_DirectDb(), now=lambda: NOW)  # type: ignore[arg-type]

    assert await service.has_active_product_access(uuid4(), "career") is False
    assert await service.has_active_direct_product_access(uuid4(), "career") is False


async def test_past_due_subscription_entitlement_is_not_grandfathered_product_access() -> None:
    subscription_id = uuid4()
    entitlement = SimpleNamespace(
        product="career",
        status="active",
        starts_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=10),
        metadata_json={"subscription_id": str(subscription_id)},
    )
    subscription = _subscription(
        id=subscription_id,
        status="past_due",
        grace_until=NOW + timedelta(days=3),
    )
    service = EntitlementsService(
        _EntitlementDb(entitlement, subscription),  # type: ignore[arg-type]
        now=lambda: NOW,
    )

    assert await service.has_active_product_access(uuid4(), "career") is False


class _RowsResult:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def scalars(self) -> _RowsResult:
        return self

    def all(self) -> list[object]:
        return self.values

    def scalar_one_or_none(self) -> object | None:
        return self.values[0] if self.values else None


class _SequenceDb:
    def __init__(self, *values: list[object]) -> None:
        self.values = list(values)

    async def execute(self, _query: object) -> _RowsResult:
        return _RowsResult(self.values.pop(0))


def _plus_entitlement(subscription_id: object, **overrides: Any) -> SimpleNamespace:
    values: dict[str, Any] = {
        "product": "self",
        "status": "active",
        "expires_at": NOW + timedelta(days=1),
        "metadata_json": {"subscription_id": str(subscription_id)},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


async def test_plus_access_requires_monthly_plan_and_exact_active_period() -> None:
    subscription_id = uuid4()
    plan_id = uuid4()
    entitlement = _plus_entitlement(subscription_id)
    subscription = _subscription(id=subscription_id, plan_id=plan_id)
    plan = SimpleNamespace(id=plan_id, plan_code="astrotype_plus_monthly")
    service = EntitlementsService(
        _SequenceDb([entitlement], [subscription], [plan]),  # type: ignore[arg-type]
        now=lambda: NOW,
    )

    assert await service.has_active_plus_access(uuid4()) is True


async def test_plus_access_rejects_direct_purchase_wrong_plan_and_period_end() -> None:
    plan_id = uuid4()
    direct = _plus_entitlement(uuid4(), metadata_json={"product_id": "self_full"}, expires_at=None)
    direct_service = EntitlementsService(_SequenceDb([direct]), now=lambda: NOW)  # type: ignore[arg-type]
    assert await direct_service.has_active_plus_access(uuid4()) is False

    for plan_code, period_end in (
        ("legacy_plan", NOW + timedelta(days=1)),
        ("astrotype_plus_monthly", NOW),
    ):
        subscription_id = uuid4()
        service = EntitlementsService(
            _SequenceDb(
                [_plus_entitlement(subscription_id)],
                [_subscription(id=subscription_id, plan_id=plan_id, current_period_end=period_end)],
                [SimpleNamespace(id=plan_id, plan_code=plan_code)],
            ),  # type: ignore[arg-type]
            now=lambda: NOW,
        )
        assert await service.has_active_plus_access(uuid4()) is False


async def test_multiple_entitlement_rows_are_evaluated_without_scalar_cardinality_failure() -> None:
    subscription_id = uuid4()
    plan_id = uuid4()
    expired = _plus_entitlement(uuid4(), expires_at=NOW)
    active = _plus_entitlement(subscription_id)
    service = EntitlementsService(
        _SequenceDb(
            [expired, active],
            [_subscription(id=subscription_id, plan_id=plan_id)],
            [SimpleNamespace(id=plan_id, plan_code="astrotype_plus_monthly")],
        ),  # type: ignore[arg-type]
        now=lambda: NOW,
    )

    assert await service.has_active_plus_access(uuid4()) is True
    assert CatalogService().get_subscription_plan("astrotype_plus_monthly").plan_code == "astrotype_plus_monthly"
