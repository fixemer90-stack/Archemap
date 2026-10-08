"""Monthly Plus subscription lifecycle service."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.authorization.service import AccountTierService, EntitlementsService
from app.modules.catalog.service import CatalogService, SubscriptionPlanDefinition
from app.modules.payments.service import PaymentsService
from app.modules.subscriptions.models import Subscription, SubscriptionEvent, SubscriptionPlan
from app.modules.subscriptions.repository import SubscriptionsRepository

logger = structlog.get_logger()


class SubscriptionAccessPolicy:
    """Pure paid-period policy used by authorization and billing state."""

    ACTIVE_STATUSES = frozenset({"active", "cancel_scheduled"})

    @classmethod
    def is_active(cls, subscription: Any, *, now: datetime | None = None) -> bool:
        moment = now or datetime.now(UTC)
        start = subscription.current_period_start
        end = subscription.current_period_end
        return (
            subscription.status in cls.ACTIVE_STATUSES
            and start is not None
            and end is not None
            and start <= moment < end
        )


class _Repository(Protocol):
    async def ensure_plan(self, **values: Any) -> SubscriptionPlan: ...
    async def create_subscription(self, **values: Any) -> Subscription: ...
    async def get_subscription(self, subscription_id: UUID, *, for_update: bool = False) -> Subscription | None: ...
    async def get_latest_for_user(self, user_id: UUID) -> Subscription | None: ...
    async def append_event(self, **values: Any) -> tuple[SubscriptionEvent, bool]: ...


class _Payments(Protocol):
    async def create_payment(self, **kwargs: Any) -> Any: ...


class _Entitlements(Protocol):
    async def grant_paid_product(self, **kwargs: Any) -> Any: ...


class _Tiers(Protocol):
    async def upgrade_to_plus(self, user_id: UUID) -> Any: ...


@dataclass(frozen=True)
class CheckoutResult:
    subscription_id: UUID
    payment_id: UUID
    status: str
    confirmation_url: str


def add_calendar_months(value: datetime, months: int) -> datetime:
    """Add calendar months, clamping end-of-month dates deterministically."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


class SubscriptionsService:
    """Create and activate server-owned monthly Plus subscriptions."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: _Repository | None = None,
        payments: _Payments | None = None,
        entitlements: _Entitlements | None = None,
        tiers: _Tiers | None = None,
    ) -> None:
        self.db = db
        self.repository = repository or SubscriptionsRepository(db)
        self.payments = payments or PaymentsService(db)
        self.entitlements = entitlements or EntitlementsService(db)
        self.tiers = tiers or AccountTierService(db)

    async def _ensure_plan(self, definition: SubscriptionPlanDefinition) -> SubscriptionPlan:
        return await self.repository.ensure_plan(
            plan_code=definition.plan_code,
            display_name=definition.display_name,
            amount=definition.amount,
            currency=definition.currency,
            billing_interval=definition.billing_interval,
            interval_count=definition.interval_count,
            is_active=True,
            features_json={"products": list(definition.products)},
        )

    async def create_checkout(self, *, user_id: UUID, plan_code: str, return_url: str) -> CheckoutResult:
        definition = CatalogService().get_subscription_plan(plan_code)
        plan = await self._ensure_plan(definition)
        subscription = await self.repository.create_subscription(
            user_id=user_id,
            plan_id=plan.id,
            provider="yookassa",
            status="incomplete",
            current_period_start=None,
            current_period_end=None,
            cancel_at_period_end=False,
            metadata_json={"plan_code": definition.plan_code},
        )
        payment = await self.payments.create_payment(
            user_id=user_id,
            amount=definition.amount,
            provider="yookassa",
            currency=definition.currency,
            description=f"{definition.display_name} — 1 месяц",
            metadata={
                "product_id": definition.plan_code,
                "plan_code": definition.plan_code,
                "subscription_id": str(subscription.id),
            },
            return_url=return_url,
            subscription_id=subscription.id,
            save_payment_method=True,
        )
        confirmation_url = str((payment.metadata_json or {}).get("confirmation_url") or "")
        return CheckoutResult(
            subscription_id=subscription.id,
            payment_id=payment.id,
            status="checkout_pending",
            confirmation_url=confirmation_url,
        )

    async def activate_initial_payment(
        self,
        *,
        subscription_id: UUID,
        payment: Any,
        provider_event_id: str,
    ) -> Subscription:
        subscription = await self.repository.get_subscription(subscription_id, for_update=True)
        if subscription is None:
            raise NotFoundError("Subscription not found")
        event_key = f"initial_payment_succeeded:{provider_event_id}"
        paid_at = payment.paid_at or datetime.now(UTC)
        event, created = await self.repository.append_event(
            subscription_id=subscription.id,
            event_key=event_key,
            provider_event_id=provider_event_id,
            event_type="initial_payment_succeeded",
            effective_at=paid_at,
            payload_json={"payment_id": str(payment.id)},
        )
        del event
        if not created:
            return subscription
        if subscription.current_period_start is not None:
            raise ValidationError("Initial subscription period is already active")

        definition = CatalogService().get_subscription_plan(str(subscription.metadata_json["plan_code"]))
        period_end = add_calendar_months(paid_at, definition.interval_count)
        subscription.status = "active"
        subscription.current_period_start = paid_at
        subscription.current_period_end = period_end
        subscription.latest_payment_id = payment.id
        subscription.provider_payment_method_id = payment.payment_method_id

        for product in definition.products:
            await self.entitlements.grant_paid_product(
                user_id=subscription.user_id,
                product=product,
                source_payment_id=payment.id,
                starts_at=paid_at,
                expires_at=period_end,
                metadata={"plan_code": definition.plan_code, "subscription_id": str(subscription.id)},
            )
        await self.tiers.upgrade_to_plus(subscription.user_id)
        logger.info(
            "subscription_transition",
            subscription_id=str(subscription.id),
            event_type="initial_payment_succeeded",
            old_status="incomplete",
            new_status="active",
            current_period_end=period_end.isoformat(),
        )
        return subscription
