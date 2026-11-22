"""Business facts from committed Plus checkout and cancellation transitions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import settings
from app.modules.analytics.models import BusinessEvent, BusinessEventOutbox
from app.modules.payments.models import Payment
from app.modules.subscriptions.models import Subscription, SubscriptionEvent, SubscriptionPlan
from app.modules.subscriptions.service import SubscriptionsService
from app.modules.users.models import User

pytestmark = pytest.mark.usefixtures("_setup_database")
_UNUSED_HASH = "not-used-for-authentication"


@pytest.mark.parametrize("case", ["enabled", "disabled", "outbox-rejected"])
async def test_plus_checkout_records_intent_with_payment_before_dispatch(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", case != "disabled")
    monkeypatch.setattr(settings, "YOOKASSA_PROVENANCE_ENABLED", False)
    user = User(email="checkout-fact@example.invalid", hashed_password=_UNUSED_HASH)
    db_session.add(user)
    await db_session.flush()
    owner = user.id
    await db_session.commit()
    calls = 0

    async def create(_provider: object, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"id": "synthetic-payment", "status": "pending"}

    monkeypatch.setattr("app.modules.payments.service.YooKassaProvider.create_payment", create)
    service = SubscriptionsService(db_session)
    if case == "outbox-rejected":
        await db_session.execute(text("ALTER TABLE business_event_outbox ADD CHECK (false)"))
        await db_session.commit()
        with pytest.raises(IntegrityError):
            await service.create_checkout(user_id=owner, plan_code="astrotype_plus_monthly", return_url="")
        checkout = None
    else:
        checkout = await service.create_checkout(user_id=owner, plan_code="astrotype_plus_monthly", return_url="")
    await db_session.commit()

    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    async with async_sessionmaker(engine)() as fresh:
        facts = (await fresh.scalars(select(BusinessEvent))).all()
        deliveries = (await fresh.scalars(select(BusinessEventOutbox))).all()
        if checkout is None:
            assert calls == 0 and not facts and not deliveries
            assert await fresh.scalar(select(Payment.id)) is None
            assert await fresh.scalar(select(Subscription.id)) is None
        else:
            assert calls == 1
            payment = await fresh.get(Payment, checkout.payment_id)
            assert payment is not None and payment.paid_at is None
            if case == "disabled":
                assert not facts and not deliveries
            else:
                (fact,) = facts
                (delivery,) = deliveries
                assert fact.event_type == "checkout_created" and fact.entity_id == payment.id
                assert fact.subject_id == owner and fact.occurred_at == payment.created_at
                assert (
                    fact.product == "plus" and fact.mode == "unknown" and fact.details == {} and fact.source_id is None
                )
                assert delivery.event_id == fact.id and delivery.destination == "internal_projection"


@pytest.mark.parametrize("case", ["enabled", "disabled", "outbox-rejected"])
async def test_plus_renewal_cancellation_records_one_fact_per_transition(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", case != "disabled")
    now = datetime(2026, 1, 15, tzinfo=UTC)
    user = User(email="cancel-fact@example.invalid", hashed_password=_UNUSED_HASH)
    plan = SubscriptionPlan(
        plan_code="astrotype_plus_monthly", display_name="Plus", amount=999, billing_interval="month", interval_count=1
    )
    db_session.add_all([user, plan])
    await db_session.flush()
    owner = user.id
    subscription = Subscription(
        user_id=owner,
        plan_id=plan.id,
        provider="yookassa",
        status="active",
        current_period_start=now - timedelta(days=5),
        current_period_end=now + timedelta(days=20),
        metadata_json={"plan_code": plan.plan_code},
    )
    db_session.add(subscription)
    await db_session.flush()
    sub_id = subscription.id
    await db_session.commit()
    service = SubscriptionsService(db_session)
    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def cancel(moment: datetime) -> None:
        await service.cancel_at_period_end(subscription_id=sub_id, user_id=owner, reason="private reason", now=moment)

    if case == "outbox-rejected":
        await db_session.execute(text("ALTER TABLE business_event_outbox ADD CHECK (false)"))
        await db_session.commit()
        with pytest.raises(IntegrityError):
            await cancel(now)
    else:
        async with sessions.begin() as stale:
            preloaded = await stale.get(Subscription, sub_id)
            assert preloaded is not None and preloaded.cancel_at_period_end is False
            await cancel(now)
            await db_session.commit()
            await SubscriptionsService(stale).cancel_at_period_end(
                subscription_id=sub_id, user_id=owner, reason="replayed", now=now + timedelta(seconds=1)
            )
        if case == "enabled":
            await service.resume(subscription_id=sub_id, user_id=owner, now=now + timedelta(seconds=2))
            await db_session.commit()
            await cancel(now + timedelta(seconds=3))
    await db_session.commit()

    async with sessions() as fresh:
        saved = await fresh.get(Subscription, sub_id)
        assert saved is not None and saved.current_period_end == now + timedelta(days=20)
        events = (
            await fresh.scalars(
                select(SubscriptionEvent)
                .where(SubscriptionEvent.event_type == "cancel_requested")
                .order_by(SubscriptionEvent.effective_at)
            )
        ).all()
        facts = (await fresh.scalars(select(BusinessEvent).order_by(BusinessEvent.occurred_at))).all()
        deliveries = (await fresh.scalars(select(BusinessEventOutbox))).all()
        if case == "outbox-rejected":
            assert saved.status == "active" and saved.cancelled_at is None and not saved.cancel_at_period_end
            assert not events and not facts and not deliveries
        elif case == "disabled":
            assert saved.status == "cancel_scheduled" and saved.cancelled_at == now
            assert len(events) == 1 and not facts and not deliveries
        else:
            assert saved.status == "cancel_scheduled" and saved.cancelled_at == now + timedelta(seconds=3)
            assert len(events) == len(facts) == len(deliveries) == 2
            for event, fact in zip(events, facts, strict=True):
                assert fact.event_type == "renewal_canceled" and fact.entity_id == event.id
                assert fact.occurred_at == event.effective_at and fact.subject_id == owner
                assert (
                    fact.product == "plus" and fact.mode == "unknown" and fact.details == {} and fact.source_id is None
                )
            assert {delivery.event_id for delivery in deliveries} == {fact.id for fact in facts}
