"""S08 on a dedicated migrated disposable PostgreSQL database; no external network."""

import asyncio
import os
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.modules.analytics import yandex_conversion
from app.modules.analytics.attribution import bind_attribution, revoke_attribution
from app.modules.analytics.attribution_settings import AttributionPolicy
from app.modules.analytics.models import BusinessEvent
from app.modules.analytics.schemas import BusinessEventInput, EventType, Mode, Product
from app.modules.analytics.service import emit_business_event
from app.modules.analytics.yandex_conversion import (
    CurrentConsent,
    ExportResult,
    export_initial_purchase,
    read_s05_consent,
    refresh_upload_status,
)
from app.modules.analytics.yandex_conversion_models import YandexConversionExport
from app.modules.analytics.yandex_transport import UploadPhase
from app.modules.payments.models import Payment
from app.modules.payments.providers.yookassa import YooKassaProvider
from app.modules.payments.service import PaymentsService
from app.modules.subscriptions.service import SubscriptionsService
from app.modules.users.models import User


@pytest.fixture
async def sessions() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    url = os.getenv("TEST_YANDEX_EXPORT_DATABASE_URL")
    if not url:
        pytest.skip("explicit S08 disposable migrated PostgreSQL database required")
    dsn = make_url(url)
    socket_dir = dsn.query.get("host")
    assert dsn.drivername == "postgresql+asyncpg" and dsn.host is None
    assert isinstance(socket_dir, str) and socket_dir.startswith("/")
    assert dsn.username == "e23_s08" and dsn.database == "e23_s08_tests"
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT current_database()")) == "e23_s08_tests"
            assert await connection.scalar(text("SELECT current_schemas(false)")) == ["public"]
            assert await connection.scalar(text("SELECT inet_server_addr() IS NULL")) is True
            expected = os.getenv("TEST_YANDEX_EXPORT_SCHEMA_REVISION", "e23s08b001")
            assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == expected
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@pytest.fixture
def export_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "YANDEX_METRICA_EXPORT_ENABLED", True)
    monkeypatch.setenv("YANDEX_METRICA_EXPORT_COUNTER_ID", "123")
    monkeypatch.setenv("YANDEX_METRICA_EXPORT_TARGET", "plus_initial_purchase")
    monkeypatch.setenv("YANDEX_METRICA_EXPORT_OAUTH_TOKEN", "test-only-oauth-secret")
    monkeypatch.setenv("YANDEX_METRICA_EXPORT_POLICY_VERSION", "approved-v1")
    monkeypatch.setenv("YANDEX_METRICA_EXPORT_NOT_BEFORE", (datetime.now(UTC) - timedelta(days=1)).isoformat())


@pytest.fixture(autouse=True)
def reject_real_http(monkeypatch: pytest.MonkeyPatch) -> None:
    async def reject(_transport: httpx.AsyncHTTPTransport, _request: httpx.Request) -> httpx.Response:
        raise AssertionError("S08 integration tests may only use HTTP mocks")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", reject)


async def _purchase(
    sessions: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch, *, mode: str = "live"
) -> tuple[UUID, UUID, datetime]:
    """Canonical S03 checkout/confirmation, with only the PSP methods mocked."""
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    monkeypatch.setattr(settings, "YOOKASSA_PROVENANCE_ENABLED", mode != "legacy")
    monkeypatch.setattr(settings, "YOOKASSA_MERCHANT_BINDING_ID", uuid4())
    monkeypatch.setattr(settings, "YOOKASSA_PAYMENT_MODE", mode if mode != "legacy" else None)
    monkeypatch.setattr(settings, "YOOKASSA_SHOP_ID", "synthetic-shop")
    monkeypatch.setattr(settings, "YOOKASSA_SECRET_KEY", "synthetic-key")
    canonical: dict[str, Any] = {}
    provider_id = str(uuid4())

    async def create_payment(_provider: YooKassaProvider, **values: Any) -> dict[str, Any]:
        canonical.update(
            id=provider_id,
            status="succeeded",
            paid=True,
            test=mode == "test",
            recipient={"account_id": "synthetic-shop"},
            amount={"value": f"{values['amount']:.2f}", "currency": values["currency"]},
            metadata=values["metadata"],
        )
        return {"id": provider_id, "status": "pending"}

    async def get_payment(_provider: YooKassaProvider, payment_id: str) -> dict[str, Any]:
        assert payment_id == provider_id
        return canonical

    monkeypatch.setattr(YooKassaProvider, "create_payment", create_payment)
    monkeypatch.setattr(YooKassaProvider, "get_payment", get_payment)
    async with sessions.begin() as session:
        owner = User(email=f"{uuid4()}@example.invalid", hashed_password=uuid4().hex)
        session.add(owner)
        await session.flush()
        checkout = await SubscriptionsService(session).create_checkout(
            user_id=owner.id, plan_code="astrotype_plus_monthly", return_url="https://example.invalid"
        )
    async with sessions.begin() as session:
        await PaymentsService(session).handle_webhook("yookassa", {"event": "payment.succeeded", "object": canonical})
    async with sessions.begin() as session:
        payment = await session.get(Payment, checkout.payment_id)
        assert payment is not None and payment.paid_at is not None and payment.status == "succeeded"
        if mode == "legacy":
            assert payment.merchant_binding_id is None
            # Even an optimistic fact cannot grant a historical payment a real binding.
            await emit_business_event(
                session,
                BusinessEventInput(
                    event_type=EventType.SUBSCRIPTION_PERIOD_STARTED,
                    entity_id=payment.id,
                    subject_id=owner.id,
                    mode=Mode.LIVE,
                    product=Product.PLUS,
                    occurred_at=payment.paid_at,
                ),
            )
            event = await emit_business_event(
                session,
                BusinessEventInput(
                    event_type=EventType.PAYMENT_CONFIRMED,
                    entity_id=payment.id,
                    source_id=uuid4(),
                    subject_id=owner.id,
                    mode=Mode.LIVE,
                    product=Product.PLUS,
                    occurred_at=payment.paid_at,
                ),
            )
            return event.id, owner.id, payment.paid_at
        event_id = await session.scalar(
            select(BusinessEvent.id).where(
                BusinessEvent.event_type == "payment_confirmed", BusinessEvent.entity_id == payment.id
            )
        )
        assert event_id is not None
        return event_id, owner.id, payment.paid_at


def _no_http(_request: httpx.Request) -> httpx.Response:
    pytest.fail("provider must not be contacted")


@pytest.mark.usefixtures("export_env")
@pytest.mark.parametrize("gate", ["off", "missing-token", "login-only", "malformed-counter"])
async def test_disabled_never_touches_db_or_http(monkeypatch: pytest.MonkeyPatch, gate: str) -> None:
    if gate == "off":
        monkeypatch.setattr(settings, "YANDEX_METRICA_EXPORT_ENABLED", False)
    elif gate == "malformed-counter":
        monkeypatch.setenv("YANDEX_METRICA_EXPORT_COUNTER_ID", "00123")
    else:
        monkeypatch.delenv("YANDEX_METRICA_EXPORT_OAUTH_TOKEN")
        if gate == "login-only":
            monkeypatch.setattr(settings, "YANDEX_CLIENT_SECRET", "synthetic-login-secret")

    async def no_consent(*args: object, **kwargs: object) -> CurrentConsent:
        pytest.fail("disabled entrypoint must not read consent")

    no_db = async_sessionmaker[AsyncSession]()  # No bind: opening SQL would fail.
    fake = httpx.MockTransport(_no_http)
    monkeypatch.setattr(yandex_conversion, "read_s05_consent", no_consent)
    assert await export_initial_purchase(uuid4(), sessions=no_db, mock_transport=fake) == ExportResult("disabled")
    assert await refresh_upload_status(uuid4(), sessions=no_db, mock_transport=fake) == ExportResult("disabled")


@pytest.mark.usefixtures("export_env")
@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("legacy", "unproven_purchase"),
        ("test", "unproven_purchase"),
        ("renewal", "unproven_purchase"),
        ("refunded", "unproven_purchase"),
        ("before-cutoff", "outside_window"),
        ("future", "outside_window"),
        ("too-old", "outside_window"),
        ("missing", "no_current_consent"),
        ("revoked", "no_current_consent"),
        ("other-owner", "no_current_consent"),
        ("policy-mismatch", "no_current_consent"),
        ("id-missing", "no_current_consent"),
        ("counter-mismatch", "no_current_consent"),
        ("malformed-id", "no_current_consent"),
        ("late-capture", "no_current_consent"),
        ("late-consent", "no_current_consent"),
        ("expired", "no_current_consent"),
    ],
)
async def test_ineligible_purchase_or_consent_is_durably_skipped(
    sessions: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch, case: str, reason: str
) -> None:
    event_id, owner, occurred_at = await _purchase(
        sessions, monkeypatch, mode=case if case in {"legacy", "test"} else "live"
    )
    now = occurred_at + timedelta(seconds=5)
    if case == "before-cutoff":
        monkeypatch.setenv("YANDEX_METRICA_EXPORT_NOT_BEFORE", now.isoformat())
    elif case == "future":
        now -= timedelta(seconds=10)
    elif case == "too-old":
        now += timedelta(days=21)
    elif case in {"renewal", "refunded"}:
        async with sessions.begin() as session:
            fact = await session.get(BusinessEvent, event_id)
            assert fact is not None
            payment = await session.get(Payment, fact.entity_id)
            assert payment is not None
            if case == "renewal":
                payment.metadata_json = {**(payment.metadata_json or {}), "billing_reason": "renewal"}
            else:
                payment.status, payment.refunded_at = "refunded", now
    before = occurred_at - timedelta(minutes=1)
    base = CurrentConsent(owner, "approved-v1", 123, before, before, now + timedelta(days=1), True, "01001")
    checks = 0

    async def read_consent(
        session: AsyncSession,
        *,
        owner_id: UUID,
        approved_policy_version: str,
        approved_counter_id: int,
        occurred_at: datetime,
        now: datetime,
        for_dispatch: bool = False,
    ) -> CurrentConsent | None:
        nonlocal checks
        checks += 1
        assert await session.get(YandexConversionExport, event_id) is None
        assert (owner_id, approved_policy_version, approved_counter_id, for_dispatch) == (
            owner,
            "approved-v1",
            123,
            False,
        )
        assert occurred_at == base.consented_at + timedelta(minutes=1)
        match case:
            case "missing":
                return None
            case "revoked":
                return replace(base, is_current=False)
            case "other-owner":
                return replace(base, owner_id=uuid4())
            case "policy-mismatch":
                return replace(base, policy_version="old-policy")
            case "counter-mismatch":
                return replace(base, counter_id=456)
            case "id-missing":
                return replace(base, client_id=None)
            case "malformed-id":
                return replace(base, client_id="=SUM(C2)")
            case "late-capture":
                return replace(base, captured_at=now)
            case "late-consent":
                return replace(base, consented_at=now)
            case "expired":
                return replace(base, expires_at=now)
        pytest.fail("unproven purchase must not read consent")

    monkeypatch.setattr(yandex_conversion, "read_s05_consent", read_consent)
    for _ in range(2):
        assert await export_initial_purchase(
            event_id,
            sessions=sessions,
            clock=lambda: now,
            mock_transport=httpx.MockTransport(_no_http),
        ) == ExportResult("skipped", reason=reason)
    assert checks == int(reason == "no_current_consent")
    async with sessions() as session:
        row = await session.get(YandexConversionExport, event_id)
        assert row is not None and (row.reason, row.upload_id) == (reason, None)


@pytest.mark.usefixtures("export_env")
@pytest.mark.parametrize(
    "case",
    [
        "current",
        "revoked-between-reads",
        "bound-after-purchase",
        "policy-not-approved",
        "retention-expired",
        "legacy-counter",
        "wrong-stored-counter",
        "wrong-approved-counter",
    ],
)
async def test_real_s05_port_rechecks_committed_consent(
    sessions: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    event_id, owner, original = await _purchase(sessions, monkeypatch)
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_APPROVED", "true")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_VERSION", "approved-v1")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_RETENTION_DAYS", "7")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_COUNTER_ID", "456" if case == "wrong-approved-counter" else "123")
    now = original + timedelta(seconds=5)
    if case == "policy-not-approved":
        monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_APPROVED", "false")
    if case == "retention-expired":
        now = original + timedelta(days=7)
    async with sessions.begin() as session:
        assert await bind_attribution(
            session,
            owner_id=owner,
            policy=AttributionPolicy("approved-v1", timedelta(days=7), 456 if case == "wrong-stored-counter" else 123),
            client_id="123456",
            captured_at=original - timedelta(seconds=60),
            now=original + timedelta(seconds=1 if case == "bound-after-purchase" else -1),
        )
        if case == "legacy-counter":
            await session.execute(
                text("UPDATE analytics_attributions SET counter_id=NULL WHERE owner_id=:owner"), {"owner": owner}
            )
    reads: list[bool] = []

    async def read_and_revoke(
        session: AsyncSession,
        *,
        owner_id: UUID,
        approved_policy_version: str,
        approved_counter_id: int,
        occurred_at: datetime,
        now: datetime,
        for_dispatch: bool = False,
    ) -> CurrentConsent | None:
        snapshot = await read_s05_consent(
            session,
            owner_id=owner_id,
            approved_policy_version=approved_policy_version,
            approved_counter_id=approved_counter_id,
            for_dispatch=for_dispatch,
            occurred_at=occurred_at,
            now=now,
        )
        reads.append(snapshot is not None)
        if len(reads) == 1:
            async with sessions.begin() as revoke_session:
                await revoke_attribution(revoke_session, owner_id=owner_id, now=now)
        return snapshot

    posts: list[bytes] = []

    async def provider(request: httpx.Request) -> httpx.Response:
        assert case == "current"
        posts.append(await request.aread())
        return httpx.Response(200, json={"uploading": {"id": 1234, "status": "UPLOADED"}})

    mock = httpx.MockTransport(provider)
    if case == "revoked-between-reads":
        monkeypatch.setattr(yandex_conversion, "read_s05_consent", read_and_revoke)
    result = await export_initial_purchase(event_id, sessions=sessions, clock=lambda: now, mock_transport=mock)
    if case == "revoked-between-reads":
        assert reads == [True, False]
    if case == "current":
        assert result == ExportResult("upload_received", upload_id=1234, upload_phase=UploadPhase.UPLOADED)
        assert len(posts) == 1 and b"123456,plus_initial_purchase," in posts[0]
    else:
        assert result == ExportResult("skipped", reason="no_current_consent")
        assert not posts


@pytest.mark.usefixtures("export_env")
async def test_only_one_insert_wins_when_both_senders_pass_initial_checks(
    sessions: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    event_id, owner, occurred_at = await _purchase(sessions, monkeypatch)
    both_read = asyncio.Barrier(2)
    first_reads = 0
    posts = 0

    async def read_consent(
        session: AsyncSession,
        *,
        owner_id: UUID,
        approved_policy_version: str,
        approved_counter_id: int,
        occurred_at: datetime,
        now: datetime,
        for_dispatch: bool = False,
    ) -> CurrentConsent:
        nonlocal first_reads
        assert owner_id == owner
        if await session.get(YandexConversionExport, event_id) is None:
            first_reads += 1
            await both_read.wait()
        before = occurred_at - timedelta(minutes=1)
        return CurrentConsent(
            owner_id, approved_policy_version, approved_counter_id, before, before, now + timedelta(days=1), True, "123"
        )

    def provider(request: httpx.Request) -> httpx.Response:
        nonlocal posts
        assert request.method == "POST"
        posts += 1
        return httpx.Response(200, json={"uploading": {"id": 1234, "status": "UPLOADED"}})

    monkeypatch.setattr(yandex_conversion, "read_s05_consent", read_consent)
    mock = httpx.MockTransport(provider)
    now = occurred_at + timedelta(seconds=5)
    async with asyncio.timeout(15):
        results = await asyncio.gather(
            *(
                export_initial_purchase(event_id, sessions=sessions, clock=lambda: now, mock_transport=mock)
                for _ in range(2)
            )
        )
    receipt = ExportResult("upload_received", upload_id=1234, upload_phase=UploadPhase.UPLOADED)
    assert first_reads == 2 and posts == 1
    assert receipt in results and all(result in (receipt, ExportResult("outcome_unknown")) for result in results)
    assert await export_initial_purchase(event_id, sessions=sessions, clock=lambda: now, mock_transport=mock) == receipt
    assert posts == 1


@pytest.mark.usefixtures("export_env")
@pytest.mark.parametrize("outcome", ["processed", "timeout", "cancelled", "persist-failed"])
async def test_durable_fence_blocks_concurrent_and_crashed_senders(
    sessions: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    event_id, owner, occurred_at = await _purchase(sessions, monkeypatch)
    now = occurred_at + timedelta(seconds=5)
    entered, release = asyncio.Event(), asyncio.Event()
    calls: list[str] = []

    async def read_consent(
        session: AsyncSession,
        *,
        owner_id: UUID,
        approved_policy_version: str,
        approved_counter_id: int,
        occurred_at: datetime,
        now: datetime,
        for_dispatch: bool = False,
    ) -> CurrentConsent:
        assert owner_id == owner
        before = occurred_at - timedelta(minutes=1)
        return CurrentConsent(
            owner_id,
            approved_policy_version,
            approved_counter_id,
            before,
            before,
            now + timedelta(days=1),
            True,
            "10023456",
        )

    async def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "GET":
            assert request.url.path.endswith("/uploading/1234")
            return httpx.Response(200, json={"uploading": {"id": 1234, "status": "PROCESSED"}})
        body = await request.aread()
        assert f"10023456,plus_initial_purchase,{int(occurred_at.timestamp())}\r\n".encode() in body
        assert str(event_id).encode() not in body and str(owner).encode() not in body
        async with sessions() as session:
            row = await session.get(YandexConversionExport, event_id)
            assert row is not None and row.status == "outcome_unknown" and row.upload_id is None
        entered.set()
        await release.wait()
        if outcome == "timeout":
            raise httpx.ReadTimeout("lost response", request=request)
        return httpx.Response(200, json={"uploading": {"id": 1234, "status": "UPLOADED"}})

    fake = httpx.MockTransport(provider)
    monkeypatch.setattr(yandex_conversion, "read_s05_consent", read_consent)

    async def export() -> ExportResult:
        return await export_initial_purchase(event_id, sessions=sessions, clock=lambda: now, mock_transport=fake)

    async with asyncio.timeout(15):
        winner = asyncio.create_task(export())
        try:
            await entered.wait()
            assert await export() == ExportResult("outcome_unknown")
            if outcome == "persist-failed":
                async with sessions.begin() as session:
                    await session.execute(
                        text("""ALTER TABLE analytics_yandex_conversion_exports
                        ADD CONSTRAINT fixture_receipt_failure CHECK (status <> 'upload_received') NOT VALID""")
                    )
            if outcome == "cancelled":
                winner.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await winner
            else:
                release.set()
                if outcome == "persist-failed":
                    with pytest.raises(IntegrityError, match="fixture_receipt_failure"):
                        await winner
                else:
                    assert await winner == (
                        ExportResult("upload_received", upload_id=1234, upload_phase=UploadPhase.UPLOADED)
                        if outcome == "processed"
                        else ExportResult("outcome_unknown")
                    )
        finally:
            if not winner.done():
                winner.cancel()
                await asyncio.gather(winner, return_exceptions=True)
            if outcome == "persist-failed":
                async with sessions.begin() as session:
                    await session.execute(
                        text("""ALTER TABLE analytics_yandex_conversion_exports
                        DROP CONSTRAINT IF EXISTS fixture_receipt_failure""")
                    )

    observed = await refresh_upload_status(event_id, sessions=sessions, mock_transport=fake)
    expected = (
        ExportResult("upload_received", upload_id=1234, upload_phase=UploadPhase.PROCESSED)
        if outcome == "processed"
        else ExportResult("outcome_unknown")
    )
    assert observed == expected
    assert await export() == expected
    assert calls == (["POST", "GET"] if outcome == "processed" else ["POST"])
    async with sessions() as session:
        row = await session.get(YandexConversionExport, event_id)
        assert row is not None and (row.status, row.upload_id, row.upload_phase) == (
            expected.status,
            expected.upload_id,
            expected.upload_phase,
        )


async def _bind_for_purchase(
    sessions: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch, owner: UUID, occurred_at: datetime
) -> None:
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_APPROVED", "true")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_VERSION", "approved-v1")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_RETENTION_DAYS", "7")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_COUNTER_ID", "123")
    async with sessions.begin() as session:
        assert await bind_attribution(
            session,
            owner_id=owner,
            policy=AttributionPolicy("approved-v1", timedelta(days=7), 123),
            client_id="123456",
            captured_at=occurred_at - timedelta(minutes=1),
            now=occurred_at - timedelta(seconds=1),
        )


async def _observe_wait(sessions: async_sessionmaker[AsyncSession], blocker: int, query_pattern: str) -> None:
    async with asyncio.timeout(4):
        while True:
            # New transaction per poll: pg_stat_activity is itself snapshotted.
            async with sessions() as observer:
                blocked = await observer.scalar(
                    text("""
                    SELECT EXISTS (SELECT 1 FROM pg_stat_activity
                      WHERE :blocker = ANY(pg_blocking_pids(pid)) AND query LIKE :query_pattern)
                """),
                    {"blocker": blocker, "query_pattern": query_pattern},
                )
            if blocked:
                return
            await asyncio.sleep(0.01)


@pytest.mark.usefixtures("export_env")
async def test_revoke_wins_while_final_dispatch_waits_on_owner(
    sessions: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    event_id, owner, occurred_at = await _purchase(sessions, monkeypatch)
    await _bind_for_purchase(sessions, monkeypatch, owner, occurred_at)
    now = occurred_at + timedelta(seconds=3)
    mock = httpx.MockTransport(_no_http)
    async with asyncio.TaskGroup() as tasks:
        async with sessions.begin() as revoke:
            pid = await revoke.scalar(text("SELECT pg_backend_pid()"))
            assert isinstance(pid, int)
            await revoke_attribution(revoke, owner_id=owner, now=now)
            # The unlocked preflight still sees the old consent. Only the
            # final FOR UPDATE must wait and then reread the committed tombstone.
            exporter = tasks.create_task(
                export_initial_purchase(event_id, sessions=sessions, clock=lambda: now, mock_transport=mock)
            )
            await _observe_wait(sessions, pid, "%analytics_attributions%FOR UPDATE%")
            async with sessions() as observer:
                row = await observer.get(YandexConversionExport, event_id)
                assert row is not None and row.status == "outcome_unknown"
        assert await exporter == ExportResult("skipped", reason="no_current_consent")
    assert (
        await export_initial_purchase(event_id, sessions=sessions, clock=lambda: now, mock_transport=mock)
        == exporter.result()
    )


@pytest.mark.usefixtures("export_env")
async def test_dispatch_wins_before_http_and_holds_owner_until_attempt_ends(
    sessions: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    event_id, owner, occurred_at = await _purchase(sessions, monkeypatch)
    await _bind_for_purchase(sessions, monkeypatch, owner, occurred_at)
    now = occurred_at + timedelta(seconds=3)
    locked, allow_http, entered_http, finish_http = (asyncio.Event() for _ in range(4))
    locked_pid = 0
    calls: list[str] = []

    async def observe_consent(
        session: AsyncSession,
        *,
        owner_id: UUID,
        approved_policy_version: str,
        approved_counter_id: int,
        occurred_at: datetime,
        now: datetime,
        for_dispatch: bool = False,
    ) -> CurrentConsent | None:
        nonlocal locked_pid
        result = await read_s05_consent(
            session,
            owner_id=owner_id,
            approved_policy_version=approved_policy_version,
            approved_counter_id=approved_counter_id,
            occurred_at=occurred_at,
            now=now,
            for_dispatch=for_dispatch,
        )
        if for_dispatch:
            assert result is not None
            pid = await session.scalar(text("SELECT pg_backend_pid()"))
            assert isinstance(pid, int)
            locked_pid = pid
            locked.set()
            await allow_http.wait()
        return result

    async def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        entered_http.set()
        await finish_http.wait()
        return httpx.Response(200, json={"uploading": {"id": 1234, "status": "UPLOADED"}})

    async def revoke() -> None:
        async with sessions.begin() as session:
            await session.execute(text("SET LOCAL synchronous_commit = off"))
            await revoke_attribution(session, owner_id=owner, now=now)
            assert await session.scalar(text("SHOW synchronous_commit")) == "on"

    monkeypatch.setattr(yandex_conversion, "read_s05_consent", observe_consent)
    mock = httpx.MockTransport(provider)
    async with asyncio.timeout(8), asyncio.TaskGroup() as tasks:
        exporter = tasks.create_task(
            export_initial_purchase(event_id, sessions=sessions, clock=lambda: now, mock_transport=mock)
        )
        await locked.wait()
        revoker = tasks.create_task(revoke())
        await _observe_wait(sessions, locked_pid, "INSERT INTO analytics_attributions%")
        assert not calls and not revoker.done()
        allow_http.set()
        await entered_http.wait()
        await _observe_wait(sessions, locked_pid, "INSERT INTO analytics_attributions%")
        assert not revoker.done()
        finish_http.set()
    expected = ExportResult("upload_received", upload_id=1234, upload_phase=UploadPhase.UPLOADED)
    assert exporter.result() == expected
    async with sessions() as observer:
        assert (
            await observer.scalar(
                text("SELECT revoked_at FROM analytics_attributions WHERE owner_id=:owner"), {"owner": owner}
            )
            == now
        )
    assert (
        await export_initial_purchase(event_id, sessions=sessions, clock=lambda: now, mock_transport=mock) == expected
    )
    assert calls == ["POST"]


@pytest.mark.usefixtures("export_env")
@pytest.mark.parametrize("block_at", ["owner_lock", "http"])
async def test_dispatch_deadline_releases_locks_and_never_replays(
    sessions: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch, block_at: str
) -> None:
    event_id, owner, occurred_at = await _purchase(sessions, monkeypatch)
    await _bind_for_purchase(sessions, monkeypatch, owner, occurred_at)
    assert yandex_conversion.DISPATCH_DEADLINE_SECONDS == 10.0
    monkeypatch.setattr(yandex_conversion, "DISPATCH_DEADLINE_SECONDS", 0.5)
    now = occurred_at + timedelta(seconds=3)
    calls: list[str] = []

    async def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        await asyncio.Event().wait()  # Mock HTTPX phase timeouts cannot stop this.
        pytest.fail("deadline must cancel the in-flight POST")

    mock = httpx.MockTransport(provider)

    async def export() -> ExportResult:
        return await export_initial_purchase(event_id, sessions=sessions, clock=lambda: now, mock_transport=mock)

    async with asyncio.timeout(5), sessions.begin() as blocker:
        if block_at == "owner_lock":
            await blocker.execute(
                text("SELECT owner_id FROM analytics_attributions WHERE owner_id=:owner FOR UPDATE"), {"owner": owner}
            )
        assert await export() == ExportResult("outcome_unknown")
        await revoke_attribution(blocker, owner_id=owner, now=now)
    assert await export() == ExportResult("outcome_unknown")
    assert calls == (["POST"] if block_at == "http" else [])
