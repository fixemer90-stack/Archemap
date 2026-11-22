"""Initial Plus payment provenance tests; the PSP is always a synthetic transport."""

from __future__ import annotations

import asyncio
import json
from base64 import b64encode
from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import settings
from app.modules.analytics.models import BusinessEvent, BusinessEventOutbox
from app.modules.authorization.models import Entitlement
from app.modules.payments.models import Payment, PaymentWebhook
from app.modules.payments.service import PaymentsService
from app.modules.subscriptions.models import Subscription, SubscriptionEvent
from app.modules.subscriptions.service import SubscriptionsService
from app.modules.users.models import User

_BINDING = UUID("e90560fc-9140-4fbe-b5cc-806148125201")
_SHOP = "synthetic-shop"
_UNUSED_HASH = "not-used-for-authentication"


@pytest.mark.usefixtures("_setup_database")
@pytest.mark.parametrize("enabled", [False, True])
async def test_initial_plus_checkout_pins_provenance_before_provider_dispatch(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, enabled: bool
) -> None:
    monkeypatch.setitem(settings.__dict__, "YOOKASSA_PROVENANCE_ENABLED", enabled)
    monkeypatch.setitem(settings.__dict__, "YOOKASSA_MERCHANT_BINDING_ID", _BINDING)
    monkeypatch.setitem(settings.__dict__, "YOOKASSA_PAYMENT_MODE", "test")
    monkeypatch.setattr(settings, "YOOKASSA_SHOP_ID", _SHOP)
    monkeypatch.setattr(settings, "YOOKASSA_SECRET_KEY", "synthetic-key")
    user = User(email="merchant-proof@example.invalid", hashed_password=_UNUSED_HASH)
    db_session.add(user)
    await db_session.flush()
    observed: list[tuple[object, object, object, object]] = []
    original_client = httpx.AsyncClient

    async def transport(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["Authorization"] == "Basic " + b64encode(f"{_SHOP}:synthetic-key".encode()).decode()
        metadata = json.loads(request.content)["metadata"]
        payment = await db_session.get(Payment, UUID(metadata["payment_id"]))
        assert payment is not None
        observed.append(
            (
                getattr(payment, "merchant_binding_id", None),
                getattr(payment, "payment_mode", None),
                getattr(payment, "merchant_account_id", None),
                payment.status,
            )
        )
        return httpx.Response(200, json={"id": "synthetic-payment", "status": "succeeded", "paid": True})

    def client(**kwargs: Any) -> httpx.AsyncClient:
        return original_client(transport=httpx.MockTransport(transport), **kwargs)

    monkeypatch.setattr("app.modules.payments.providers.yookassa.httpx.AsyncClient", client)
    checkout = await SubscriptionsService(db_session).create_checkout(
        user_id=user.id, plan_code="astrotype_plus_monthly", return_url="https://example.invalid"
    )
    await db_session.commit()
    db_session.expire_all()
    payment = await db_session.get(Payment, checkout.payment_id)
    assert payment is not None
    persisted = (payment.provider_payment_id, payment.status, payment.paid_at)
    await db_session.rollback()
    assert observed == [(_BINDING, "test", _SHOP, "pending") if enabled else (None, None, None, "pending")]
    assert persisted == ("synthetic-payment", "pending" if enabled else "succeeded", None)


@pytest.mark.usefixtures("_setup_database")
@pytest.mark.parametrize(
    ("mode", "shop", "override", "accept"),
    [
        ("test", _SHOP, {}, True),
        ("live", _SHOP, {"test": False}, True),
        ("test", "wrong-auth-shop", {}, False),
        ("test", _SHOP, {"recipient": {"account_id": "wrong-recipient"}}, False),
        ("test", _SHOP, {"recipient": {}}, False),
        ("test", _SHOP, {"test": None}, False),
        ("test", _SHOP, {"test": 1}, False),
        ("test", _SHOP, {"test": False}, False),
        ("test", _SHOP, {"amount": {"value": "999.001", "currency": "RUB"}}, False),
        ("test", _SHOP, {"amount": {"value": "NaN", "currency": "RUB"}}, False),
        ("test", _SHOP, {"amount": {"value": 999.0, "currency": "RUB"}}, False),
        ("test", _SHOP, {"amount": {"value": "999.00"}}, False),
        ("test", _SHOP, {"metadata": {"subscription_id": "wrong-subscription"}}, False),
        ("test", _SHOP, {"metadata": {"plan_code": "wrong-plan"}}, False),
        ("test", _SHOP, {"metadata": {"billing_reason": "renewal"}}, False),
        ("test", _SHOP, {"metadata": {"product": "career"}}, False),
        ("test", _SHOP, {"paid": 1}, False),
        ("test", _SHOP, {"id": "different-canonical-id"}, False),
        ("test", _SHOP, {"status": []}, False),
    ],
)
@pytest.mark.parametrize("path", ["webhook", "reconcile"])
async def test_bound_payment_requires_exact_canonical_evidence(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    shop: str,
    override: dict[str, Any],
    accept: bool,
    path: str,
) -> None:
    monkeypatch.setattr(settings, "YOOKASSA_PROVENANCE_ENABLED", True)
    monkeypatch.setattr(settings, "YOOKASSA_MERCHANT_BINDING_ID", _BINDING)
    monkeypatch.setattr(settings, "YOOKASSA_PAYMENT_MODE", mode)
    monkeypatch.setattr(settings, "YOOKASSA_SHOP_ID", _SHOP)
    monkeypatch.setattr(settings, "YOOKASSA_SECRET_KEY", "synthetic-key")
    user = User(email="canonical-proof@example.invalid", hashed_password=_UNUSED_HASH)
    db_session.add(user)
    await db_session.flush()
    canonical: dict[str, Any] = {}
    original_client = httpx.AsyncClient

    def transport(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            canonical.update(
                {
                    "id": "synthetic-payment",
                    "status": "succeeded",
                    "paid": True,
                    "test": True,
                    "recipient": {"account_id": _SHOP},
                    "amount": {"value": "999.00", "currency": "RUB"},
                    "metadata": json.loads(request.content)["metadata"],
                }
            )
            return httpx.Response(200, json=canonical)
        assert request.method == "GET"
        assert request.url.path.endswith("/synthetic-payment")
        assert request.headers["Authorization"] == "Basic " + b64encode(f"{shop}:synthetic-key".encode()).decode()
        changes = dict(override)
        if "metadata" in changes:
            changes["metadata"] = {**canonical["metadata"], **changes["metadata"]}
        return httpx.Response(200, json={**canonical, **changes})

    def client(**kwargs: Any) -> httpx.AsyncClient:
        return original_client(transport=httpx.MockTransport(transport), **kwargs)

    monkeypatch.setattr("app.modules.payments.providers.yookassa.httpx.AsyncClient", client)
    checkout = await SubscriptionsService(db_session).create_checkout(
        user_id=user.id, plan_code="astrotype_plus_monthly", return_url="https://example.invalid"
    )
    await db_session.commit()
    # The creation gate and current configured mode cannot reclassify an existing payment.
    monkeypatch.setattr(settings, "YOOKASSA_PROVENANCE_ENABLED", False)
    monkeypatch.setattr(settings, "YOOKASSA_PAYMENT_MODE", "live" if mode == "test" else "test")
    monkeypatch.setattr(settings, "YOOKASSA_SHOP_ID", shop)
    service = PaymentsService(db_session)
    payment = await db_session.get(Payment, checkout.payment_id)
    assert payment is not None
    if path == "webhook":
        await service.handle_webhook("yookassa", {"event": "payment.succeeded", "object": canonical})
    else:
        await service.reconcile_pending_provider_payment(payment)
    await db_session.commit()
    db_session.expire_all()
    try:
        payment = await db_session.get(Payment, checkout.payment_id)
        subscription = await db_session.get(Subscription, checkout.subscription_id)
        assert payment is not None and subscription is not None
        assert payment.payment_mode == mode
        assert payment.status == ("succeeded" if accept else "pending")
        assert (payment.paid_at is not None) is accept
        assert subscription.status == ("active" if accept else "incomplete")
    finally:
        await db_session.rollback()


@pytest.mark.usefixtures("_setup_database")
@pytest.mark.parametrize("analytics", ["off", "on", "rollback", "reconcile-first"])
async def test_stale_reconciliation_cannot_replace_first_webhook_success(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    analytics: str,
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", analytics != "off")
    monkeypatch.setattr(settings, "YOOKASSA_PROVENANCE_ENABLED", True)
    monkeypatch.setattr(settings, "YOOKASSA_MERCHANT_BINDING_ID", _BINDING)
    monkeypatch.setattr(settings, "YOOKASSA_PAYMENT_MODE", "test")
    monkeypatch.setattr(settings, "YOOKASSA_SHOP_ID", _SHOP)
    monkeypatch.setattr(settings, "YOOKASSA_SECRET_KEY", "synthetic-key")
    user = User(email="concurrent-proof@example.invalid", hashed_password=_UNUSED_HASH)
    db_session.add(user)
    await db_session.flush()

    lookup_started = asyncio.Event()
    release_lookup = asyncio.Event()
    canonical: dict[str, Any] = {}
    original_client = httpx.AsyncClient

    async def transport(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            canonical.update(
                {
                    "id": "synthetic-payment",
                    "status": "succeeded",
                    "paid": True,
                    "test": True,
                    "recipient": {"account_id": _SHOP},
                    "amount": {"value": "999.00", "currency": "RUB"},
                    "metadata": json.loads(request.content)["metadata"],
                }
            )
        elif not lookup_started.is_set():
            lookup_started.set()
            await release_lookup.wait()
        return httpx.Response(200, json=canonical)

    def client(**kwargs: Any) -> httpx.AsyncClient:
        return original_client(transport=httpx.MockTransport(transport), **kwargs)

    monkeypatch.setattr("app.modules.payments.providers.yookassa.httpx.AsyncClient", client)
    checkout = await SubscriptionsService(db_session).create_checkout(
        user_id=user.id, plan_code="astrotype_plus_monthly", return_url="https://example.invalid"
    )
    await db_session.commit()
    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def reconcile() -> None:
        async with sessions() as session:
            stale = await session.get(Payment, checkout.payment_id)
            assert stale is not None and stale.status == "pending"
            await PaymentsService(session).reconcile_pending_provider_payment(stale)
            await session.commit()

    webhook = {"event": "payment.succeeded", "object": canonical}
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(BusinessEvent)) == 0
    if analytics == "rollback":
        lookup_started.set()  # The deliberate outbox failure runs before the two-session race.
        async with sessions.begin() as session:
            await session.execute(
                text("""
                CREATE FUNCTION reject_second_financial_fact() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF (SELECT event_type FROM business_events WHERE id = NEW.event_id)
                        = 'subscription_period_started' THEN
                        RAISE EXCEPTION 'fixture rejects period outbox' USING ERRCODE = '23514';
                    END IF;
                    RETURN NEW;
                END;
                $$
            """)
            )
            await session.execute(
                text("""
                CREATE TRIGGER reject_second_financial_fact BEFORE INSERT ON business_event_outbox
                FOR EACH ROW EXECUTE FUNCTION reject_second_financial_fact()
            """)
            )
        async with sessions() as session:
            with pytest.raises(IntegrityError, match="fixture rejects period outbox"):
                await PaymentsService(session).handle_webhook("yookassa", webhook)
            await session.commit()
        async with sessions.begin() as session:
            payment = await session.get(Payment, checkout.payment_id)
            subscription = await session.get(Subscription, checkout.subscription_id)
            assert payment is not None and payment.status == "pending" and payment.paid_at is None
            assert subscription is not None and subscription.current_period_start is None
            assert await session.scalar(select(func.count()).select_from(Entitlement)) == 0
            assert await session.scalar(select(func.count()).select_from(PaymentWebhook)) == 0
            assert await session.scalar(select(func.count()).select_from(BusinessEvent)) == 0
            assert await session.scalar(select(func.count()).select_from(BusinessEventOutbox)) == 0
            await session.execute(text("DROP TRIGGER reject_second_financial_fact ON business_event_outbox"))
            await session.execute(text("DROP FUNCTION reject_second_financial_fact()"))
        lookup_started.clear()

    if analytics == "reconcile-first":
        lookup_started.set()
        await reconcile()
        async with sessions() as session:
            payment = await session.get(Payment, checkout.payment_id)
            assert payment is not None and payment.paid_at is not None
            first_paid_at = payment.paid_at
    else:
        async with asyncio.timeout(10), asyncio.TaskGroup() as tasks:
            tasks.create_task(reconcile())
            await lookup_started.wait()
            async with sessions() as session:
                result = await PaymentsService(session).handle_webhook("yookassa", webhook)
                assert result["processed"] is True
                await session.commit()
                payment = await session.get(Payment, checkout.payment_id)
                assert payment is not None and payment.paid_at is not None
                first_paid_at = payment.paid_at
            release_lookup.set()

    async with sessions() as session:
        await PaymentsService(session).handle_webhook("yookassa", webhook)
        await session.commit()
    async with sessions() as session:
        payment = await session.get(Payment, checkout.payment_id)
        subscription = await session.get(Subscription, checkout.subscription_id)
        effective_times = (
            await session.scalars(
                select(SubscriptionEvent.effective_at).where(
                    SubscriptionEvent.subscription_id == checkout.subscription_id,
                    SubscriptionEvent.event_type == "initial_payment_succeeded",
                )
            )
        ).all()
        assert payment is not None and subscription is not None
        assert payment.paid_at == first_paid_at == subscription.current_period_start
        assert effective_times == [first_paid_at]
        rows = {fact.event_type: fact for fact in (await session.scalars(select(BusinessEvent))).all()}
        if analytics == "off":
            assert not rows
        else:
            assert set(rows) == {"payment_confirmed", "subscription_period_started"}
            assert rows["payment_confirmed"].source_id == _BINDING
            assert rows["subscription_period_started"].source_id is None
            for fact in rows.values():
                assert (fact.entity_id, fact.subject_id, fact.mode, fact.product, fact.occurred_at, fact.details) == (
                    payment.id,
                    user.id,
                    "test",
                    "plus",
                    first_paid_at,
                    {},
                )
        assert await session.scalar(select(func.count()).select_from(BusinessEventOutbox)) == len(rows)
