"""Admin subscription support repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.schemas import SubscriptionSupportData
from app.modules.payments.models import Payment
from app.modules.subscriptions.models import Subscription, SubscriptionEvent, SubscriptionPlan
from app.modules.users.models import User


class AdminRepository:
    """Read support-safe subscription state and append explicit repair audit."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_subscription_support_by_email(self, email: str) -> SubscriptionSupportData | None:
        user_result = await self.db.execute(select(User).where(User.email == email.strip().lower()))
        user = user_result.scalar_one_or_none()
        if user is None:
            return None

        subscription_result = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        subscription = subscription_result.scalar_one_or_none()
        if subscription is None:
            return None

        plan_result = await self.db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == subscription.plan_id))
        plan = plan_result.scalar_one()

        payment = None
        if subscription.latest_payment_id is not None:
            payment_result = await self.db.execute(select(Payment).where(Payment.id == subscription.latest_payment_id))
            payment = payment_result.scalar_one_or_none()

        events_result = await self.db.execute(
            select(SubscriptionEvent)
            .where(SubscriptionEvent.subscription_id == subscription.id)
            .order_by(SubscriptionEvent.effective_at.desc(), SubscriptionEvent.created_at.desc())
            .limit(100)
        )
        events = tuple(events_result.scalars().all())
        return SubscriptionSupportData(
            user_id=user.id,
            email=user.email,
            subscription_id=subscription.id,
            plan_code=plan.plan_code,
            display_name=plan.display_name,
            status=subscription.status,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            next_billing_at=(subscription.current_period_end if not subscription.cancel_at_period_end else None),
            latest_payment_id=payment.id if payment is not None else None,
            latest_payment_status=payment.status if payment is not None else None,
            events=events,
        )

    async def append_subscription_event(
        self,
        *,
        subscription_id: UUID,
        event_key: str,
        provider_event_id: str | None,
        event_type: str,
        effective_at: datetime,
        payload_json: dict[str, Any],
    ) -> tuple[SubscriptionEvent, bool]:
        existing_result = await self.db.execute(
            select(SubscriptionEvent).where(SubscriptionEvent.event_key == event_key)
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            return existing, False
        event = SubscriptionEvent(
            subscription_id=subscription_id,
            event_key=event_key,
            provider_event_id=provider_event_id,
            event_type=event_type,
            effective_at=effective_at,
            payload_json=payload_json,
        )
        self.db.add(event)
        await self.db.flush()
        return event, True
