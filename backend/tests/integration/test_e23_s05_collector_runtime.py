"""S05 runtime proof on an explicitly disposable, Alembic-upgraded DB and local Redis."""

import asyncio
import os
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.config import settings
from app.core.security import create_access_token
from app.infrastructure.database import async_session_factory
from app.main import app
from app.modules.analytics.attribution import purge_expired_attribution, read_active_attribution
from app.modules.analytics.attribution_models import AnalyticsAttribution
from app.modules.analytics.models import BusinessEvent, BusinessEventOutbox
from app.modules.astrotype_v2.models import NatalChart, NatalReport
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User

pytestmark = pytest.mark.skipif(
    os.getenv("E23_S05_DISPOSABLE") != "1", reason="requires dedicated migrated S05 PostgreSQL and Redis"
)
ORIGIN = "http://localhost:3000"
API = "/api/v1/analytics"
POLICY = "synthetic-test-v1"


async def _seed(owner: UUID, outsider: UUID) -> UUID:
    async with async_session_factory() as session:
        assert await session.scalar(text("SELECT current_database()")) == "e23_s05_tests"
        assert await session.scalar(text("SELECT to_regclass('analytics_attributions') IS NOT NULL")) is True
        session.add_all(
            User(id=user, email=f"{user}@example.test", hashed_password="", is_verified=True)
            for user in (owner, outsider)
        )
        await session.flush()
        profile = PersonProfile(
            id=uuid4(),
            user_id=owner,
            name="PRIVATE_SENTINEL",
            birth_date=date(1990, 1, 1),
            birth_place="PRIVATE_BIRTHPLACE",
            latitude=0,
            longitude=0,
            timezone="UTC",
        )
        session.add(profile)
        await session.flush()
        chart = NatalChart(
            id=uuid4(),
            user_id=owner,
            profile_id=profile.id,
            engine_version="test",
            input_hash="test",
            birth_datetime_utc=datetime(1990, 1, 1, tzinfo=UTC),
            timezone="UTC",
            latitude=0,
            longitude=0,
        )
        session.add(chart)
        await session.flush()
        report = NatalReport(id=uuid4(), chart_id=chart.id, deterministic_payload={"secret": "PRIVATE_REPORT"})
        session.add(report)
        await session.commit()
        return report.id


async def test_mounted_owner_consent_and_collector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", [ORIGIN])
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_APPROVED", "true")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_VERSION", POLICY)
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_RETENTION_DAYS", "7")
    monkeypatch.setenv("ANALYTICS_ATTRIBUTION_COUNTER_ID", "123")
    owner, outsider = uuid4(), uuid4()
    report = await _seed(owner, outsider)
    headers = {"origin": ORIGIN, "x-analytics-request": "1", "sec-fetch-site": "same-origin"}
    owner_token, _ = create_access_token(str(owner))
    outsider_token, _ = create_access_token(str(outsider))
    owner_headers = {**headers, "authorization": f"Bearer {owner_token}"}
    outsider_headers = {**headers, "authorization": f"Bearer {outsider_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url=ORIGIN, headers=headers) as client:

        async def capture(client_id: str | None, version: str = POLICY) -> str:
            response = await client.post(
                f"{API}/attribution/capture",
                json={
                    "granted": True,
                    "policy_version": version,
                    "client_id": client_id,
                    **({"source_counter_id": "123"} if client_id is not None else {}),
                },
            )
            assert response.status_code == 201, response.text
            assert set(response.json()) == {"receipt"}
            receipt = response.json()["receipt"]
            assert isinstance(receipt, str)
            if client_id is not None:
                assert client_id not in response.text
            return receipt

        async def attach(receipt: str, auth: dict[str, str]) -> int:
            return (await client.post(f"{API}/attribution/attach", headers=auth, json={"receipt": receipt})).status_code

        body = {"event": "report_opened", "product": "self", "report_id": str(report)}
        missing = await client.post(f"{API}/events", headers=outsider_headers, json={**body, "report_id": str(uuid4())})
        foreign = await client.post(f"{API}/events", headers=outsider_headers, json=body)
        assert missing.status_code == foreign.status_code == 404 and missing.json() == foreign.json()
        first, second = await asyncio.gather(
            client.post(f"{API}/events", headers=owner_headers, json=body),
            client.post(f"{API}/events", headers=owner_headers, json=body),
        )
        assert first.status_code == second.status_code == 204
        async with async_session_factory() as session:
            event = (await session.scalars(select(BusinessEvent).where(BusinessEvent.subject_id == owner))).one()
            assert event.event_type == "report_opened" and event.product == "self"
            assert event.details == {} and event.entity_id != report
            outbox = (
                await session.scalars(select(BusinessEventOutbox).where(BusinessEventOutbox.event_id == event.id))
            ).one()
            assert outbox.destination == "internal_projection"
        for size in (8, 8, 8, 4):
            batch = await asyncio.gather(
                *(client.post(f"{API}/events", headers=owner_headers, json=body) for _ in range(size))
            )
            assert all(result.status_code == 204 for result in batch)
        assert (await client.post(f"{API}/events", headers=owner_headers, json=body)).status_code == 429

        bad = await client.post(
            f"{API}/attribution/capture", json={"granted": True, "policy_version": "wrong-version", "client_id": None}
        )
        assert bad.status_code == 404
        null = await capture(None)
        assert await attach(null, headers) == 401
        assert await attach(null, owner_headers) == 204
        assert await attach(null, outsider_headers) == 404
        null_now = datetime.now(UTC)
        async with async_session_factory() as session:
            null_row = await session.get(AnalyticsAttribution, owner)
            assert null_row is not None and null_row.policy_version == POLICY and null_row.client_id is None
            assert (
                await read_active_attribution(
                    session,
                    owner_id=owner,
                    approved_policy_version=POLICY,
                    approved_counter_id=123,
                    occurred_at=null_now,
                    now=null_now,
                )
                is None
            )

        stale_counter = await capture("12345678901234567890")
        monkeypatch.setenv("ANALYTICS_ATTRIBUTION_COUNTER_ID", "456")
        assert await attach(stale_counter, owner_headers) == 404
        monkeypatch.setenv("ANALYTICS_ATTRIBUTION_COUNTER_ID", "123")
        assert await attach(stale_counter, owner_headers) == 404
        receipt = await capture("12345678901234567890")
        pending_pre_revoke = await capture("98765432109876543210")
        simultaneous = await asyncio.gather(attach(receipt, owner_headers), attach(receipt, owner_headers))
        assert sorted(simultaneous) == [204, 404]
        assert await attach(receipt, outsider_headers) == 404
        now = datetime.now(UTC)
        async with async_session_factory() as session:
            eligible = await read_active_attribution(
                session,
                owner_id=owner,
                approved_policy_version=POLICY,
                approved_counter_id=123,
                occurred_at=now,
                now=now,
            )
            assert eligible is not None and eligible.owner_id == owner and eligible.policy_version == POLICY
            assert eligible.counter_id == 123
            assert eligible.client_id == "12345678901234567890" and eligible.captured_at <= eligible.bound_at <= now
            for user, version, event_at, as_of in (
                (outsider, POLICY, now, now),
                (owner, "wrong-version", now, now),
                (owner, POLICY, eligible.bound_at - timedelta(microseconds=1), now),
                (owner, POLICY, now + timedelta(seconds=1), now),
                (owner, POLICY, now, eligible.expires_at),
            ):
                assert (
                    await read_active_attribution(
                        session,
                        owner_id=user,
                        approved_policy_version=version,
                        approved_counter_id=123,
                        occurred_at=event_at,
                        now=as_of,
                    )
                    is None
                )
        assert await attach(await capture(None), owner_headers) == 204
        async with async_session_factory() as session:
            row_after_null = await session.get(AnalyticsAttribution, owner)
            assert row_after_null is not None
            assert (row_after_null.client_id, row_after_null.bound_at, row_after_null.expires_at) == (
                eligible.client_id,
                eligible.bound_at,
                eligible.expires_at,
            )
        monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_APPROVED", "false")
        monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", False)
        response = await client.post(f"{API}/attribution/revoke", headers=owner_headers, json={})
        assert response.status_code == 204
        monkeypatch.setenv("ANALYTICS_ATTRIBUTION_POLICY_APPROVED", "true")
        assert await attach(pending_pre_revoke, owner_headers) == 204
        async with async_session_factory() as session:
            row = await session.get(AnalyticsAttribution, owner)
            assert row is not None and row.client_id is None and row.counter_id is None and row.revoked_at is not None
            assert (
                await read_active_attribution(
                    session,
                    owner_id=owner,
                    approved_policy_version=POLICY,
                    approved_counter_id=123,
                    occurred_at=now,
                    now=datetime.now(UTC),
                )
                is None
            )
        assert await attach(await capture("11111111111111111111"), owner_headers) == 204
        discarded = await capture("22222222222222222222")
        assert (await client.post(f"{API}/attribution/discard", json={"receipt": discarded})).status_code == 204
        assert await attach(discarded, outsider_headers) == 404

    async with async_session_factory() as session:
        await purge_expired_attribution(session, now=now + timedelta(days=8))
        await session.commit()
    async with async_session_factory() as session:
        assert await session.get(AnalyticsAttribution, owner) is None
        assert await session.get(NatalReport, report) is not None
        assert await session.get(User, owner) is not None
