"""Real Self publication, independent PostgreSQL visibility, and E23 overview."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.analytics.models import BusinessEvent, BusinessEventOutbox, SelfReadinessEvidence
from app.modules.analytics.overview import build_overview
from app.modules.analytics.schemas import BusinessEventInput, EventType
from app.modules.analytics.self_readiness import observe_self_readiness
from app.modules.analytics.service import RecordedBusinessEvent, emit_business_event
from app.modules.astrotype_v2 import models as self_models
from app.modules.astrotype_v2.repository import AstrotypeV2Repository
from app.modules.authorization.models import Entitlement
from app.modules.payments.models import Payment, YooKassaMerchantBinding
from app.modules.profiles.models import PersonProfile
from app.modules.subscriptions.models import Subscription, SubscriptionPlan
from app.modules.users.models import User
from tests.conftest import test_engine
from tests.conftest import test_session_factory as sessions
from tests.integration.test_business_event_outbox import (
    _setup_database,
    pytestmark,
    registration_tables,
    self_report_tables,
)
from workers.tasks import astrotype_v2 as self_worker

# Import pytest fixture dependencies and the destructive-suite opt-in marker.
__all__ = ["_setup_database", "pytestmark", "registration_tables", "self_report_tables"]
NO_LOGIN_HASH = "!"


@pytest.fixture
async def self_d7_tables(self_report_tables: None) -> AsyncIterator[None]:
    metadata = BusinessEvent.metadata
    tables = tuple(
        metadata.tables[model.__tablename__]
        for model in (SubscriptionPlan, Subscription, YooKassaMerchantBinding, Payment, Entitlement)
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(metadata.create_all, tables=tables, checkfirst=False)
    try:
        yield
    finally:
        async with test_engine.begin() as conn:
            await conn.run_sync(metadata.drop_all, tables=tables)


@pytest.mark.usefixtures("self_d7_tables")
@pytest.mark.parametrize(
    "scenario",
    ["on-time", "late-commit", "precommit-wall-clock", "intent-failure", "intent-advisory-wait", "observation-failure"],
)
async def test_self_foundation_commit_controls_overview_d7(monkeypatch: pytest.MonkeyPatch, scenario: str) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_ENABLED", False)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    monkeypatch.setattr(self_worker, "async_session_factory", sessions)
    user_id, profile_id, generation_id = UUID(int=81), UUID(int=82), UUID(int=83)
    async with sessions.begin() as db:
        db.add(User(id=user_id, email="self-d7@example.com", hashed_password=NO_LOGIN_HASH, is_verified=True))
        await db.flush()
        db.add(
            PersonProfile(
                id=profile_id,
                user_id=user_id,
                name="Fixture",
                birth_date=date(1990, 1, 1),
                birth_time=time(12),
                birth_time_accuracy="exact",
                birth_place="Moscow",
                latitude=55.75,
                longitude=37.61,
                timezone="Europe/Moscow",
            )
        )
        await db.flush()
        db.add(self_models.NatalReportGeneration(generation_id=generation_id, user_id=user_id, profile_id=profile_id))

    crosses_deadline = scenario in {"late-commit", "precommit-wall-clock"}
    advisory_wait = scenario == "intent-advisory-wait"
    advisory_key = 230704071
    if advisory_wait:
        async with sessions.begin() as db:
            await db.execute(
                text(f"""
                CREATE OR REPLACE FUNCTION wait_for_d7_proof() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN PERFORM pg_advisory_xact_lock({advisory_key}); RETURN NEW; END; $$
                """)
            )
            await db.execute(
                text("""
                CREATE TRIGGER wait_for_d7_proof BEFORE INSERT ON business_self_readiness_evidence
                FOR EACH ROW EXECUTE FUNCTION wait_for_d7_proof()
            """)
            )
    if scenario.endswith("-failure"):
        operation = "INSERT" if scenario == "intent-failure" else "UPDATE"
        async with sessions.begin() as db:
            await db.execute(
                text("""
                CREATE FUNCTION reject_d7_proof() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'proof-only failure'; END; $$
            """)
            )
            await db.execute(
                text(f"""
                CREATE TRIGGER reject_d7_proof BEFORE {operation} ON business_self_readiness_evidence
                FOR EACH ROW EXECUTE FUNCTION reject_d7_proof()
            """)
            )

    if scenario == "precommit-wall-clock":

        async def emit_with_wall_clock(db: AsyncSession, fact: BusinessEventInput) -> RecordedBusinessEvent:
            if fact.event_type == EventType.BASIC_REPORT_READY:
                now = await db.scalar(select(func.clock_timestamp()))
                assert now is not None
                fact = fact.model_copy(update={"occurred_at": now})
            return await emit_business_event(db, fact)

        monkeypatch.setattr(self_worker, "emit_business_event", emit_with_wall_clock)

    real_generation_session = self_worker._generation_session
    deadline: datetime | None = None
    pre_commit: datetime | None = None
    post_commit: datetime | None = None
    invisible_before_commit = False
    accessible_after_commit = False
    generation_pid: int | None = None
    generation_started = asyncio.Event()
    timeout_settings = text("SELECT current_setting('statement_timeout'), current_setting('lock_timeout')")

    @asynccontextmanager
    async def generation_session_with_deadline(generation: UUID) -> AsyncIterator[AsyncSession]:
        async with real_generation_session(generation) as db:
            real_commit = db.commit

            async def commit() -> None:
                nonlocal deadline, pre_commit, post_commit, invisible_before_commit, accessible_after_commit
                nonlocal generation_pid
                if deadline is not None:
                    await real_commit()
                    return
                report_id = await db.scalar(select(self_models.NatalReport.id))
                if report_id is None:
                    await real_commit()  # Initial running checkpoint.
                    await db.execute(text("SET LOCAL statement_timeout = '8s'"))
                    await db.execute(text("SET LOCAL lock_timeout = '7s'"))
                    generation_pid = await db.scalar(select(func.pg_backend_pid()))
                    generation_started.set()
                    return
                assert (await db.execute(timeout_settings)).one() == ("8s", "7s")
                async with sessions() as observer:
                    delay = timedelta(milliseconds=100) if crosses_deadline else timedelta(seconds=30)
                    deadline = await observer.scalar(select(func.clock_timestamp() + delay))
                    assert deadline is not None
                    if crosses_deadline:
                        await observer.execute(select(func.pg_sleep_until(deadline)))
                    pre_commit = await observer.scalar(select(func.clock_timestamp()))
                    invisible_before_commit = (
                        await observer.get(self_models.NatalReport, report_id) is None
                        and await observer.scalar(select(SelfReadinessEvidence.event_id)) is None
                    )
                await real_commit()
                async with sessions() as observer:
                    visible = await AstrotypeV2Repository(observer).get_report_for_user(
                        report_id=report_id, user_id=user_id, profile_id=profile_id
                    )
                    accessible_after_commit = visible is not None and bool(visible.deterministic_payload)
                    post_commit = await observer.scalar(select(func.clock_timestamp()))

            monkeypatch.setattr(db, "commit", commit)
            yield db

    monkeypatch.setattr(self_worker, "_generation_session", generation_session_with_deadline)

    async def run_worker() -> dict[str, object]:
        return await self_worker._generate_natal_report_v2_async(
            user_id=str(user_id), profile_id=str(profile_id), generation_id=str(generation_id), force=True
        )

    if advisory_wait:
        async with sessions.begin() as holder:
            holder_pid = await holder.scalar(select(func.pg_backend_pid()))
            await holder.execute(select(func.pg_advisory_xact_lock(advisory_key)))
            task = asyncio.create_task(run_worker())
            try:
                async with asyncio.timeout(5), sessions() as observer:
                    await generation_started.wait()
                    # A database lock wait is observable only by polling PostgreSQL.
                    while True:
                        blocked = await observer.scalar(
                            text("""
                            SELECT :holder = ANY(pg_blocking_pids(:waiter)) AND EXISTS (
                                SELECT 1 FROM pg_locks WHERE pid = :waiter AND locktype = 'advisory' AND NOT granted
                            )
                            """),
                            {"holder": holder_pid, "waiter": generation_pid},
                        )
                        if blocked:
                            break
                        await asyncio.sleep(0.01)
                done, _ = await asyncio.wait({task}, timeout=3)
                assert task in done, "proof INSERT must time out server-side while its advisory blocker is still held"
                result = task.result()
                async with sessions() as observer:
                    assert not await observer.scalar(select(func.pg_try_advisory_xact_lock(advisory_key)))
                    committed = (
                        await observer.execute(
                            select(self_models.NatalReport.id, BusinessEvent.id, BusinessEventOutbox.id)
                            .join(BusinessEvent, BusinessEvent.entity_id == self_models.NatalReport.id)
                            .join(BusinessEventOutbox, BusinessEventOutbox.event_id == BusinessEvent.id)
                            .where(BusinessEvent.event_type == "basic_report_ready")
                        )
                    ).one()
                    assert str(committed[0]) == result["report_id"]
            finally:
                await holder.rollback()
                if not task.done():
                    await asyncio.wait_for(task, timeout=10)
        async with sessions.begin() as db:
            await db.execute(text("DROP TRIGGER wait_for_d7_proof ON business_self_readiness_evidence"))
            await db.execute(text("DROP FUNCTION wait_for_d7_proof()"))
    else:
        result = await run_worker()
    assert result["status"] == "complete"
    assert invisible_before_commit and accessible_after_commit
    assert deadline is not None and pre_commit is not None and post_commit is not None
    assert (pre_commit >= deadline) is crosses_deadline
    assert (post_commit >= deadline) is crosses_deadline
    proof: SelfReadinessEvidence | None
    async with sessions() as db:
        proof = (await db.scalars(select(SelfReadinessEvidence))).one_or_none()
    if scenario.endswith("-failure"):
        async with sessions.begin() as db:
            await db.execute(text("DROP TRIGGER reject_d7_proof ON business_self_readiness_evidence"))
            await db.execute(text("DROP FUNCTION reject_d7_proof()"))
    if scenario == "intent-failure" or advisory_wait:
        assert proof is None
    else:
        assert proof is not None
        assert proof.publish_not_before <= pre_commit
        assert proof.owner_id == user_id and proof.generation_id == generation_id
        if scenario == "observation-failure":
            assert proof.observed_at is None
            # Even immutable intent is not proof if the source link is stale at observation.
            async with sessions.begin() as db:
                await db.execute(update(self_models.NatalReportGeneration).values(report_id=None))
            assert await observe_self_readiness(sessions, event_id=proof.event_id) == 0
            async with sessions.begin() as db:
                await db.execute(update(self_models.NatalReportGeneration).values(report_id=proof.report_id))
            # Recover a terminal foundation via the reconciler, not by regenerating.
            assert await self_worker._reconcile_interrupted_narratives(before=post_commit) == 0
            async with sessions() as db:
                recovered = await db.get(SelfReadinessEvidence, proof.event_id)
                assert recovered is not None and recovered.observed_at is not None
                assert recovered.observed_at > post_commit
                # The commit was in time, but the only durable upper bound is too late.
                deadline = recovered.observed_at
                proof = recovered
        else:
            assert proof.observed_at is not None and proof.observed_at >= post_commit

    # A forced duplicate delivery reuses the same foundation and cannot create or
    # replace proof (even after a proof-only write error has cleared).
    replay = await run_worker()
    assert replay["report_id"] == result["report_id"]
    assert await observe_self_readiness(sessions) == 0
    async with sessions() as db:
        final_proof = (await db.scalars(select(SelfReadinessEvidence))).one_or_none()
        if proof is None:
            assert final_proof is None
        else:
            assert final_proof is not None
            assert (final_proof.event_id, final_proof.observed_at, final_proof.publish_not_before) == (
                proof.event_id,
                proof.observed_at,
                proof.publish_not_before,
            )
    signup = deadline - timedelta(days=7)
    async with sessions.begin() as db:
        await emit_business_event(
            db,
            BusinessEventInput(event_type=EventType.REGISTRATION_COMPLETED, entity_id=user_id, occurred_at=signup),
        )
    async with sessions.begin() as db:
        await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        report = (await db.scalars(select(self_models.NatalReport))).one()
        assert report.created_at < deadline
        fact = (await db.scalars(select(BusinessEvent).where(BusinessEvent.event_type == "basic_report_ready"))).one()
        assert fact.entity_id == report.id
        assert (
            await db.scalar(
                select(func.count()).select_from(BusinessEventOutbox).where(BusinessEventOutbox.event_id == fact.id)
            )
            == 1
        )
        cohort = signup.date()
        overview = await build_overview(
            db,
            as_of=max(post_commit, deadline, datetime.now(UTC)) + timedelta(seconds=1),
            from_date=cohort,
            to_date=cohort + timedelta(days=1),
            timezone="UTC",
            enabled=True,
            coverage_since=datetime.combine(cohort, time.min, tzinfo=UTC),
        )
    d7 = overview.activation_d7
    expected = 1 if scenario == "on-time" else None
    assert (d7.status, d7.mature_count, d7.immature_count, d7.activated_count, d7.rate) == (
        "available" if expected is not None else "unavailable",
        1,
        0,
        expected,
        Decimal(1) if expected is not None else None,
    ), f"occurred_at={fact.occurred_at}, pre_commit={pre_commit}, deadline={deadline}, post_commit={post_commit}"
