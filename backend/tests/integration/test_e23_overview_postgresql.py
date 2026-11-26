"""Run only in the dedicated disposable E23 PostgreSQL cluster."""

import os
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app import dependencies
from app.api import middleware
from app.config import settings
from app.main import app
from app.modules.admin import router as admin
from app.modules.analytics import landing_documents as landing
from app.modules.analytics.models import BusinessEvent, SelfReadinessEvidence
from app.modules.analytics.overview import build_overview
from app.modules.analytics.schemas import BusinessEventInput, EventDetails, EventType, Mode, Product
from app.modules.authorization.models import Entitlement
from app.modules.payments.models import Payment, YooKassaMerchantBinding
from app.modules.subscriptions.models import Subscription, SubscriptionPlan
from app.modules.users.models import User
from tests.conftest import test_engine
from tests.conftest import test_session_factory as sessions
from tests.landing_redis import disposable_landing_redis

pytestmark = pytest.mark.skipif(
    os.getenv("E23_DISPOSABLE_TEST_DATABASES") != "1", reason="requires dedicated disposable E23 databases"
)
NO_LOGIN_HASH = "!"


@pytest.fixture
async def overview_tables(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    metadata = BusinessEvent.metadata
    tables = [
        metadata.tables[model.__tablename__]
        for model in (
            User,
            SubscriptionPlan,
            Subscription,
            YooKassaMerchantBinding,
            Payment,
            Entitlement,
            BusinessEvent,
            SelfReadinessEvidence,
        )
    ]
    async with test_engine.begin() as conn:
        assert await conn.scalar(text("SELECT current_database()")) == "e23_tests"
        assert await conn.scalar(text("SELECT current_schemas(false) = ARRAY['public']::name[]")) is True
        await conn.run_sync(metadata.create_all, tables=tables, checkfirst=False)
    monkeypatch.setattr(admin, "async_session_factory", sessions)
    try:
        yield
    finally:
        async with test_engine.begin() as conn:
            await conn.run_sync(metadata.drop_all, tables=tables)


def fact(value: BusinessEventInput, recorded: datetime | None = None) -> BusinessEvent:
    return BusinessEvent(
        schema_version=1,
        event_type=value.event_type.value,
        semantic_key=value.semantic_key,
        entity_id=value.entity_id,
        source_id=value.source_id,
        subject_id=value.subject_id,
        occurred_at=value.occurred_at,
        created_at=recorded or value.occurred_at,
        mode=value.mode.value,
        product=value.product.value if value.product else None,
        details=value.details.model_dump(mode="json", exclude_none=True),
    )


@pytest.mark.usefixtures("overview_tables")
@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("no-fact", 0),  # A covered mature signup without a readiness transition is a non-activation.
        ("legacy", None),
        ("legacy-and-proven", None),
        ("wrong-owner", None),
        ("wrong-report", None),
        ("signup-straddle", None),
        ("as-of-straddle", None),
        ("as-of-equality", None),
        ("after-as-of-observed", 0),
        ("after-as-of-pending", 0),
        ("late", 0),
        ("signup-inclusive", 1),
    ],
)
async def test_mature_d7_does_not_infer_first_visibility_from_the_fact(scenario: str, expected: int | None) -> None:
    signup = datetime(2026, 1, 2, tzinfo=UTC)
    deadline = signup + timedelta(days=7)
    as_of = deadline + timedelta(seconds=1)
    owner, report = uuid4(), uuid4()
    async with sessions.begin() as db:
        db.add(
            fact(BusinessEventInput(event_type=EventType.REGISTRATION_COMPLETED, entity_id=owner, occurred_at=signup))
        )
        if scenario == "legacy-and-proven":
            db.add(
                fact(
                    BusinessEventInput(
                        event_type=EventType.BASIC_REPORT_READY,
                        entity_id=uuid4(),
                        subject_id=owner,
                        product=Product.SELF,
                        occurred_at=signup - timedelta(seconds=1),
                    )
                )
            )
        if scenario != "no-fact":
            readiness = fact(
                BusinessEventInput(
                    event_type=EventType.BASIC_REPORT_READY,
                    entity_id=report,
                    subject_id=owner,
                    product=Product.SELF,
                    occurred_at=signup + timedelta(days=1),
                )
            )
            db.add(readiness)
            await db.flush()
            if scenario != "legacy":
                lower = {
                    "signup-straddle": signup - timedelta(microseconds=1),
                    "late": deadline,
                    "as-of-straddle": as_of - timedelta(microseconds=1),
                    "as-of-equality": as_of,
                    "after-as-of-observed": as_of + timedelta(microseconds=1),
                    "after-as-of-pending": as_of + timedelta(microseconds=1),
                }.get(scenario, signup)
                upper = as_of + timedelta(seconds=1) if "as-of" in scenario else max(lower, signup)
                db.add(
                    SelfReadinessEvidence(
                        event_id=readiness.id,
                        owner_id=uuid4() if scenario == "wrong-owner" else owner,
                        report_id=uuid4() if scenario == "wrong-report" else report,
                        generation_id=uuid4(),
                        publish_not_before=lower,
                        observed_at=None if scenario == "after-as-of-pending" else upper,
                    )
                )
    async with sessions.begin() as db:
        await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        overview = await build_overview(
            db,
            as_of=as_of,
            from_date=signup.date(),
            to_date=signup.date() + timedelta(days=1),
            timezone="UTC",
            enabled=True,
            coverage_since=signup,
        )
    activation = overview.activation_d7
    assert activation.status == ("unavailable" if expected is None else "available")
    assert activation.mature_count == 1 and activation.immature_count == 0
    assert activation.activated_count == expected
    assert activation.rate == (None if expected is None else Decimal(expected))


@pytest.mark.usefixtures("overview_tables")
async def test_overview_cohort_boundaries_and_financial_truth() -> None:
    start = datetime(2026, 1, 1, 21, tzinfo=UTC)  # Jan 2 00:00 in Moscow
    signup = start + timedelta(hours=23, minutes=59)
    deadline = signup + timedelta(days=7)
    account_ids = [uuid4() for _ in range(5)]
    async with sessions.begin() as db:
        plan = SubscriptionPlan(
            plan_code="astrotype_plus_monthly", display_name="Plus", amount=1.0, billing_interval="month"
        )
        db.add(plan)
        await db.flush()
        for index, uid in enumerate(account_ids):
            at = {3: start, 4: start + timedelta(days=1)}.get(index, signup)
            db.add(
                fact(
                    BusinessEventInput(
                        event_type=EventType.REGISTRATION_COMPLETED,
                        entity_id=uid,
                        subject_id=uid,
                        occurred_at=at,
                        details=EventDetails(registration_method="oauth" if index == 1 else "email"),
                    )
                )
            )
        for index, at in [
            (0, signup + timedelta(minutes=2)),
            (1, deadline),
            (2, signup + timedelta(hours=1)),
            (2, signup - timedelta(seconds=1)),
            (4, signup + timedelta(minutes=2)),
            (3, start + timedelta(minutes=1)),
        ]:
            report_id = uuid4()
            ready = fact(
                BusinessEventInput(
                    event_type=EventType.BASIC_REPORT_READY,
                    entity_id=report_id,
                    subject_id=account_ids[index],
                    occurred_at=at,
                    product=Product.SELF,
                )
            )
            db.add(ready)
            await db.flush()
            db.add(
                SelfReadinessEvidence(
                    event_id=ready.id,
                    owner_id=account_ids[index],
                    report_id=report_id,
                    generation_id=uuid4(),
                    publish_not_before=at,
                    observed_at=at,
                )
            )
        duplicate = fact(
            BusinessEventInput(
                event_type=EventType.REGISTRATION_COMPLETED,
                entity_id=account_ids[0],
                subject_id=account_ids[0],
                occurred_at=signup,
            )
        )
        duplicate.semantic_key = "noncanonical-registration"
        db.add(duplicate)
        for index, (mode, amount, currency) in enumerate(
            [
                ("live", 0.1, "RUB"),
                ("live", 0.2, "RUB"),
                ("live", 0.01, "USD"),
                ("test", 999.99, "RUB"),
                ("live", 555.55, "RUB"),
                (None, 888.88, "RUB"),
            ]
        ):
            user = User(id=uuid4(), email=f"user-{index}@example.com", hashed_password=NO_LOGIN_HASH)
            db.add(user)
            binding = (
                YooKassaMerchantBinding(id=uuid4(), payment_mode=mode, merchant_account_id=f"shop-{index}")
                if mode
                else None
            )
            if binding is not None:
                db.add(binding)
            await db.flush()
            payment = Payment(
                id=uuid4(),
                user_id=user.id,
                provider="yookassa",
                provider_payment_id=f"psp-{index}",
                merchant_binding_id=binding.id if binding else None,
                payment_mode=mode,
                merchant_account_id=binding.merchant_account_id if binding else None,
                amount=amount,
                currency=currency,
                status="succeeded",
                paid_at=signup,
            )
            db.add(payment)
            await db.flush()
            if binding is not None and mode is not None and index < 4:
                db.add(
                    fact(
                        BusinessEventInput(
                            event_type=EventType.PAYMENT_CONFIRMED,
                            entity_id=payment.id,
                            source_id=binding.id,
                            subject_id=user.id,
                            occurred_at=signup,
                            mode=Mode(mode),
                            product=Product.PLUS,
                        )
                    )
                )
                if index == 0:
                    duplicate = fact(
                        BusinessEventInput(
                            event_type=EventType.PAYMENT_CONFIRMED,
                            entity_id=payment.id,
                            source_id=binding.id,
                            subject_id=user.id,
                            occurred_at=signup,
                            mode=Mode.LIVE,
                            product=Product.PLUS,
                        )
                    )
                    duplicate.semantic_key = "noncanonical-payment"
                    db.add(duplicate)
            if index in (0, 3, 4):
                # One plan; a canceled-at-end LIVE period counts until its exact end; TEST doesn't.
                if index in (0, 3) and mode is not None:
                    db.add(
                        fact(
                            BusinessEventInput(
                                event_type=EventType.SUBSCRIPTION_PERIOD_STARTED,
                                entity_id=payment.id,
                                subject_id=user.id,
                                occurred_at=signup,
                                mode=Mode(mode),
                                product=Product.PLUS,
                            )
                        )
                    )
                subscription = Subscription(
                    id=uuid4(),
                    user_id=user.id,
                    plan_id=plan.id,
                    latest_payment_id=payment.id,
                    current_period_start=signup,
                    current_period_end=deadline + timedelta(seconds=1),
                    status="cancel_scheduled",
                )
                db.add(subscription)
                await db.flush()
                payment.subscription_id = subscription.id
                db.add(
                    Entitlement(
                        user_id=user.id,
                        product="self",
                        source_payment_id=payment.id,
                        starts_at=signup,
                        expires_at=deadline + timedelta(seconds=1),
                        metadata_json={"subscription_id": str(subscription.id)},
                    )
                )

    async with sessions() as db:
        for as_of, status in [(deadline - timedelta(microseconds=1), "insufficient_history"), (deadline, "available")]:
            result = await build_overview(
                db,
                as_of=as_of,
                from_date=date(2026, 1, 2),
                to_date=date(2026, 1, 3),
                timezone="Europe/Moscow",
                enabled=True,
                coverage_since=start,
            )
            assert result.window_from == start
            assert result.registrations.model_dump() == {"email": 3, "oauth": 1, "unknown": 0}
            assert result.activation_d7.status == status
            if status == "available":
                assert result.activation_d7.mature_count == 4
                assert result.activation_d7.activated_count == 2
                assert result.activation_d7.rate == Decimal("0.5")
            else:
                assert result.activation_d7.mature_count == 1
                assert result.activation_d7.activated_count == 1
                assert result.activation_d7.immature_count == 3 and result.activation_d7.rate is None
            assert result.payments.model_dump() == {"live": 3, "test": 1, "unknown": 2}
            assert result.live_cash_received is None  # two receipts are not classified
            assert result.live_refunds is None
            assert result.paid_plus.active is None and result.paid_plus.status == "partial"
            assert result.paid_plus.proven_active == 1
        empty = await build_overview(
            db,
            as_of=deadline + timedelta(seconds=1),
            from_date=date(2026, 1, 4),
            to_date=date(2026, 1, 5),
            timezone="Europe/Moscow",
            enabled=True,
            coverage_since=start,
        )
        assert empty.activation_d7.status == "no_data" and empty.activation_d7.rate is None
        assert empty.paid_plus.active == 0 and empty.live_cash_received == []
        incomplete = await build_overview(
            db,
            as_of=deadline,
            from_date=date(2026, 1, 2),
            to_date=date(2026, 1, 3),
            timezone="Europe/Moscow",
            enabled=True,
            coverage_since=signup,
        )
        assert not incomplete.coverage.window_complete and incomplete.activation_d7.status == "unavailable"

    async with sessions.begin() as db:
        paid = (await db.scalars(select(Payment).where(Payment.provider_payment_id == "psp-0"))).one()
        grant = (await db.scalars(select(Entitlement).where(Entitlement.source_payment_id == paid.id))).one()
        older = Payment(user_id=paid.user_id, provider="yookassa", amount=1, currency="RUB", status="succeeded")
        db.add(older)
        await db.flush()
        grant.source_payment_id = older.id
    async with sessions() as db:
        no_same_payment_grant = await build_overview(
            db,
            as_of=deadline,
            from_date=date(2026, 1, 2),
            to_date=date(2026, 1, 3),
            timezone="Europe/Moscow",
            enabled=True,
            coverage_since=start,
        )
        assert no_same_payment_grant.paid_plus.proven_active == 0
        assert no_same_payment_grant.paid_plus.active is None


@pytest.mark.usefixtures("overview_tables")
async def test_overview_cash_and_checkout_coverage() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    uid, binding = uuid4(), uuid4()
    async with sessions.begin() as db:
        db.add(User(id=uid, email="ledger@example.com", hashed_password=NO_LOGIN_HASH))
        db.add(YooKassaMerchantBinding(id=binding, payment_mode="live", merchant_account_id="e23-shop"))
        await db.flush()
        for day, amount, currency, status, proof in [
            (0, 0.1, "RUB", "succeeded", "correct"),
            (0, 0.2, "RUB", "succeeded", "correct"),
            (0, 0.01, "USD", "succeeded", "correct"),
            (0, 10.0, "RUB", "pending", None),
            (0, 10.0, "RUB", "failed", None),
            (0, 10.0, "RUB", "pending", "no_reference"),
            (1, 100.0, "RUB", "succeeded", "wrong_subject"),
            (2, 0.001, "RUB", "succeeded", "correct"),
        ]:
            at = start + timedelta(days=day, hours=1)
            payment_id = uuid4()
            db.add(
                Payment(
                    id=payment_id,
                    user_id=uid,
                    provider="yookassa",
                    provider_payment_id=None if proof == "no_reference" else str(uuid4()),
                    merchant_binding_id=binding,
                    merchant_account_id="e23-shop",
                    payment_mode="live",
                    amount=amount,
                    currency=currency,
                    status=status,
                    paid_at=at if status == "succeeded" else None,
                )
            )
            db.add(
                fact(
                    BusinessEventInput(
                        event_type=EventType.CHECKOUT_CREATED,
                        entity_id=payment_id,
                        subject_id=uid,
                        occurred_at=at,
                        product=Product.PLUS,
                    )
                )
            )
            if status == "succeeded":
                db.add(
                    fact(
                        BusinessEventInput(
                            event_type=EventType.PAYMENT_CONFIRMED,
                            entity_id=payment_id,
                            source_id=binding,
                            subject_id=uuid4() if proof == "wrong_subject" else uid,
                            occurred_at=at,
                            mode=Mode.LIVE,
                            product=Product.PLUS,
                        )
                    )
                )
    async with sessions() as db:
        for day in range(1, 4):
            result = await build_overview(
                db,
                as_of=start + timedelta(days=4),
                from_date=date(2026, 1, day),
                to_date=date(2026, 1, day + 1),
                timezone="UTC",
                enabled=True,
                coverage_since=start,
            )
            if day == 1:
                assert result.live_cash_received is not None
                assert [(item.currency, item.amount) for item in result.live_cash_received] == [
                    ("RUB", Decimal("0.30")),
                    ("USD", Decimal("0.01")),
                ]
                assert result.checkouts == 6
                assert result.checkout_outcomes.model_dump() == {
                    "pending": 1,
                    "failed": 1,
                    "confirmed": 3,
                    "unknown": 1,
                }
            else:
                assert result.live_cash_received is None
                assert result.payments.unknown == (1 if day == 2 else 0)
                assert result.payments.live == (1 if day == 3 else 0)


@pytest.mark.usefixtures("overview_tables")
async def test_orphan_confirmation_and_duplicate_psp_receipt_fail_closed() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    uid, binding, rotated_binding, other_shop, orphan, late_ledger = (uuid4() for _ in range(6))
    async with sessions.begin() as db:
        db.add(User(id=uid, email="duplicate@example.com", hashed_password=NO_LOGIN_HASH))
        merchant_accounts = {binding: "duplicate-shop", rotated_binding: "duplicate-shop", other_shop: "other-shop"}
        db.add_all(
            YooKassaMerchantBinding(id=merchant, payment_mode="live", merchant_account_id=account)
            for merchant, account in merchant_accounts.items()
        )
        await db.flush()
        for day, payment_id, merchant, receipt in [
            (1, orphan, binding, None),
            (1, late_ledger, binding, None),
            (2, uuid4(), binding, "same-account"),
            (2, uuid4(), rotated_binding, "same-account"),
            (3, uuid4(), binding, "different-account"),
        ]:
            occurred = start + timedelta(days=day - 1, hours=1)
            if receipt is not None:
                db.add(
                    Payment(
                        id=payment_id,
                        user_id=uid,
                        provider="yookassa",
                        provider_payment_id=receipt,
                        merchant_binding_id=merchant,
                        merchant_account_id=merchant_accounts[merchant],
                        payment_mode="live",
                        amount=10,
                        currency="RUB",
                        status="succeeded",
                        paid_at=occurred,
                    )
                )
            db.add(
                fact(
                    BusinessEventInput(
                        event_type=EventType.PAYMENT_CONFIRMED,
                        entity_id=payment_id,
                        source_id=merchant,
                        subject_id=uid,
                        occurred_at=occurred,
                        mode=Mode.LIVE,
                        product=Product.PLUS,
                    )
                )
            )
        # A match outside the selected paid range is still an orphan in that range.
        # The same receipt with different/NULL merchant identity does not make day 3 ambiguous.
        for payment_id, historical_merchant, receipt in [
            (late_ledger, None, "late-ledger"),
            (uuid4(), other_shop, "different-account"),
            (uuid4(), None, "different-account"),
        ]:
            db.add(
                Payment(
                    id=payment_id,
                    user_id=uid,
                    provider="yookassa",
                    provider_payment_id=receipt,
                    merchant_binding_id=historical_merchant,
                    merchant_account_id=merchant_accounts[historical_merchant] if historical_merchant else None,
                    payment_mode="live" if historical_merchant else None,
                    amount=10,
                    currency="RUB",
                    status="succeeded",
                    paid_at=start + timedelta(days=3),
                )
            )
    async with sessions() as db:
        for day in (1, 2, 3):
            result = await build_overview(
                db,
                as_of=start + timedelta(days=4),
                from_date=date(2026, 1, day),
                to_date=date(2026, 1, day + 1),
                timezone="UTC",
                enabled=True,
                coverage_since=start,
            )
            if day < 3:
                assert result.payments.model_dump() == {"live": 0, "test": 0, "unknown": 2}
                assert result.live_cash_received is None
            else:
                assert result.payments.model_dump() == {"live": 1, "test": 0, "unknown": 0}
                assert result.live_cash_received is not None
                assert [(item.currency, item.amount) for item in result.live_cash_received] == [("RUB", Decimal("10"))]


@pytest.mark.usefixtures("overview_tables")
async def test_overview_real_rbac_and_read_only_transaction(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    async with sessions.begin() as db:
        ordinary = User(id=uuid4(), email="ordinary@example.com", hashed_password=NO_LOGIN_HASH, is_verified=True)
        operator = User(
            id=uuid4(), email="operator@example.com", hashed_password=NO_LOGIN_HASH, is_verified=True, is_superuser=True
        )
        db.add_all([ordinary, operator])

    async def authenticate(token: str) -> dict[str, str] | None:
        return {"sub": token} if token in (str(ordinary.id), str(operator.id)) else None

    async def use_test_db() -> AsyncIterator[object]:
        async with sessions() as db:
            yield db

    def no_redis() -> None:
        raise ConnectionError("Rate limiting is not under test")

    monkeypatch.setattr(middleware, "get_redis_client", no_redis)
    monkeypatch.setattr(dependencies, "_decode_valid_access_token", authenticate)
    monkeypatch.setitem(app.dependency_overrides, dependencies.get_db, use_test_db)
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", False)
    url = "/api/v1/admin/business/overview"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        assert (await client.get(url)).status_code == 401
        assert (await client.get(url, headers={"Authorization": f"Bearer {ordinary.id}"})).status_code == 403
        headers = {"Authorization": f"Bearer {operator.id}"}
        response = await client.get(url, headers=headers)
        assert response.status_code == 200 and response.headers["Cache-Control"] == "no-store"
        assert response.json()["coverage"]["status"] == "unavailable"
        assert response.json()["payments"]["live"] is None
        assert (await client.get(url, headers=headers, params={"from_date": "2026-01-01"})).status_code == 422
        invalid = await client.get(url, headers=headers, params={"from_date": "0001-01-01", "to_date": "0001-01-02"})
        assert invalid.status_code == 422
        monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
        monkeypatch.setattr(settings, "BUSINESS_MONITORING_COVERAGE_SINCE", datetime(2026, 1, 1, tzinfo=UTC))
        enabled = await client.get(url, headers=headers, params={"from_date": "2026-01-02", "to_date": "2026-01-03"})
        assert enabled.status_code == 200 and enabled.json()["live_cash_received"] == []
        # Keep landing observations independent of the business collection switch and date filters.
        monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", False)
        monkeypatch.setattr(settings, "LANDING_DOCUMENT_COUNTER_ENABLED", True)
        async with disposable_landing_redis(tmp_path.parent / "s05-rbac.sock", tmp_path) as landing_url:
            monkeypatch.setattr(settings, "LANDING_DOCUMENT_REDIS_URL", landing_url)
            redis = landing._redis()
            try:
                assert (await client.get(url, headers=headers)).json()["landing_documents"]["observed"] is None
                signal = await client.post("/_internal/landing-document", headers={"X-Astrotype-Landing-Signal": "1"})
                assert signal.status_code == 204
                for bearer, status in [(None, 401), (str(ordinary.id), 403)]:
                    denied = await client.get(url, headers={"Authorization": f"Bearer {bearer}"} if bearer else {})
                    assert denied.status_code == status and "landing_documents" not in denied.json()
                readback = await client.get(
                    url, headers=headers, params={"from_date": "2026-01-02", "to_date": "2026-01-03"}
                )
                assert readback.status_code == 200 and readback.headers["Cache-Control"] == "no-store"
                assert readback.json()["landing_documents"]["observed"] == 1
                assert await redis.dbsize() == 1
                monkeypatch.setattr(settings, "LANDING_DOCUMENT_COUNTER_ENABLED", False)
                assert (await client.get(url, headers=headers)).json()["landing_documents"]["observed"] is None
            finally:
                await redis.aclose()
                landing._redis_for_url.cache_clear()
    generator = admin.business_read_session()
    db = await anext(generator)
    try:
        assert await db.scalar(text("SHOW transaction_isolation")) == "repeatable read"
        assert await db.scalar(text("SHOW statement_timeout")) == "5s"
        with pytest.raises(DBAPIError) as caught:
            await db.execute(text("DELETE FROM business_events"))
        assert getattr(caught.value.orig, "sqlstate", None) == "25006"
    finally:
        await generator.aclose()
