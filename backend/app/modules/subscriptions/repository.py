"""Persistence helpers for monthly subscriptions."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.subscriptions.models import Subscription, SubscriptionEvent, SubscriptionPlan


class SubscriptionsRepository:
    """Data access for plans, subscriptions, and append-only events."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_plan(self, **values: Any) -> SubscriptionPlan:
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.plan_code == values["plan_code"])
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            plan = SubscriptionPlan(**values)
            self.db.add(plan)
            await self.db.flush()
        return plan

    async def create_subscription(self, **values: Any) -> Subscription:
        subscription = Subscription(**values)
        self.db.add(subscription)
        await self.db.flush()
        return subscription

    async def get_subscription(self, subscription_id: UUID, *, for_update: bool = False) -> Subscription | None:
        query = select(Subscription).where(Subscription.id == subscription_id)
        if for_update:
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_for_user(self, user_id: UUID) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def append_event(
        self,
        *,
        subscription_id: UUID,
        event_key: str,
        provider_event_id: str | None,
        event_type: str,
        effective_at: datetime,
        payload_json: dict[str, Any],
    ) -> tuple[SubscriptionEvent, bool]:
        result = await self.db.execute(select(SubscriptionEvent).where(SubscriptionEvent.event_key == event_key))
        existing = result.scalar_one_or_none()
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
