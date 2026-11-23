"""Run only in the fresh PostgreSQL/Redis topology created by the S07 harness."""

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.modules.analytics.models import BusinessEventOutbox
from app.modules.analytics.operations import (
    COOLDOWN,
    IncidentCode,
    create_daily_digest,
    digest_target,
    evaluate_business_alerts,
    moscow_day_bounds,
    project_business_events,
)
from app.modules.analytics.operations_models import (
    BusinessDailyCount,
    BusinessOperationsHeartbeat,
    BusinessOperatorMessage,
    BusinessTelegramDelivery,
)
from app.modules.analytics.schemas import BusinessEventInput, EventType, Mode, Product
from app.modules.analytics.service import claim_outbox, complete_outbox, emit_business_event
from app.modules.analytics.telegram_delivery import DeliveryStatus, deliver_once
from app.modules.analytics.telegram_transport import TelegramDestination, TelegramTransport
from app.modules.astrotype_v2.models import NatalChart
from app.modules.career.models import CareerProfile, CareerSegmentGeneration
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User
from workers.celery_app import app

pytestmark = pytest.mark.skipif(not os.getenv("E23_S07_DISPOSABLE"), reason="use scripts/test_business_operations.sh")


@pytest.fixture
async def s07_sessions() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    scratch = Path(os.environ["E23_S07_DISPOSABLE"])
    expected = f"postgresql+asyncpg://e23_s07@/e23_s07_tests?host={scratch}"
    assert scratch.name.startswith("s07.") and (scratch / "pg" / "PG_VERSION").is_file()
    assert settings.DATABASE_URL == os.environ["TEST_DATABASE_URL"] == expected
    assert f"redis+socket://{scratch}/redis.sock?virtual_host=1" == settings.CELERY_BROKER_URL
    assert f"redis+socket://{scratch}/redis.sock?virtual_host=2" == settings.CELERY_RESULT_BACKEND
    assert settings.BUSINESS_MONITORING_ENABLED and not settings.BUSINESS_ALERTS_ENABLED
    engine = create_async_engine(expected, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT current_database()")) == "e23_s07_tests"
            assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "e23s07t001"
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


NOW = datetime(2026, 6, 1, 7, tzinfo=UTC)


async def _seed(session: AsyncSession, event: BusinessEventInput, *, recorded_at: datetime) -> None:
    await emit_business_event(session, event, recorded_at=recorded_at)


async def test_atomic_projection_fences_replay_and_digest_pins_moscow_window(
    s07_sessions: async_sessionmaker[AsyncSession],
) -> None:
    start, end = moscow_day_bounds(digest_target(NOW))
    known = BusinessEventInput(event_type=EventType.REGISTRATION_COMPLETED, entity_id=uuid4(), occurred_at=start)
    inside = BusinessEventInput(
        event_type=EventType.REPORT_READY,
        entity_id=uuid4(),
        occurred_at=end - timedelta(microseconds=1),
        product=Product.CHILD,
        mode=Mode.TEST,
    )
    outside = BusinessEventInput(
        event_type=EventType.REGISTRATION_COMPLETED,
        entity_id=uuid4(),
        occurred_at=end,
    )
    async with s07_sessions.begin() as session:
        assert not await create_daily_digest(session, now=NOW)
        for index, event in enumerate((inside, known, known, outside)):
            await _seed(session, event, recorded_at=NOW - timedelta(seconds=4 - index))
    async with s07_sessions() as uncommitted:
        assert await project_business_events(uncommitted, now=NOW) == 3
        await uncommitted.rollback()
    async with s07_sessions.begin() as session:
        assert await session.scalar(select(func.count()).select_from(BusinessDailyCount)) == 0
        assert await session.scalar(select(func.count()).select_from(BusinessOperationsHeartbeat)) == 0
        claim = await claim_outbox(session, now=NOW, lease_seconds=10)
        assert claim is not None
    async with s07_sessions.begin() as session:
        assert await project_business_events(session, now=NOW) == 2  # active S02 lease is not adopted
    async with s07_sessions.begin() as session:
        assert not await create_daily_digest(session, now=NOW)  # oldest in-window fact is leased
    after_lease = NOW + timedelta(seconds=10)

    async def race() -> int:
        async with s07_sessions.begin() as session:
            return await project_business_events(session, now=after_lease)

    assert sorted(await asyncio.gather(race(), race())) == [0, 1]
    async with s07_sessions.begin() as running_projector:
        assert await project_business_events(running_projector, now=after_lease) == 0
        async with s07_sessions.begin() as concurrent_digest:
            assert not await create_daily_digest(concurrent_digest, now=after_lease)
    async with s07_sessions.begin() as session:
        assert not await complete_outbox(session, claim, now=after_lease)
        assert await create_daily_digest(session, now=after_lease)
    async with s07_sessions.begin() as session:
        assert not await create_daily_digest(session, now=after_lease)
        message = await session.get(BusinessOperatorMessage, "digest:2026-05-31")
        assert message is not None
        assert message.payload == {
            "timezone": "Europe/Moscow",
            "from_utc": start.isoformat(),
            "to_utc": end.isoformat(),
            "projector_succeeded_at": after_lease.isoformat(),
            "coverage": "recorded_facts_only",
            "counts": [
                {"event_type": "registration_completed", "mode": "unknown", "product": None, "count": 1},
                {"event_type": "report_ready", "mode": "test", "product": "child", "count": 1},
            ],
        }
        assert await session.scalar(select(func.sum(BusinessDailyCount.event_count))) == 3


async def test_in_window_exhausted_projection_defers_digest_and_alerts_backlog(
    s07_sessions: async_sessionmaker[AsyncSession],
) -> None:
    now = NOW + timedelta(days=1)
    event = BusinessEventInput(
        event_type=EventType.REGISTRATION_COMPLETED,
        entity_id=uuid4(),
        occurred_at=moscow_day_bounds(digest_target(now))[0],
    )
    async with s07_sessions.begin() as session:
        await _seed(session, event, recorded_at=now - timedelta(minutes=11))
        await session.execute(
            update(BusinessEventOutbox).where(BusinessEventOutbox.status == "pending").values(attempts=10)
        )
        assert await project_business_events(session, now=now) == 0
        assert not await create_daily_digest(session, now=now)
        assert await evaluate_business_alerts(session, now=now) == (IncidentCode.PROJECTION_BACKLOG,)
    async with s07_sessions.begin() as session:
        await session.execute(
            update(BusinessEventOutbox).where(BusinessEventOutbox.status == "pending").values(attempts=9)
        )
        assert await project_business_events(session, now=now + timedelta(seconds=1)) == 1
        assert await evaluate_business_alerts(session, now=now + timedelta(seconds=1)) == (
            IncidentCode.PROJECTION_BACKLOG,
        )
        assert await create_daily_digest(session, now=now + timedelta(seconds=1))


async def _career_fixture(session: AsyncSession) -> tuple[UUID, UUID]:
    user_id, profile_id, chart_id, career_id = uuid4(), uuid4(), uuid4(), uuid4()
    await session.execute(insert(User).values(id=user_id, email="operations@example.com", hashed_password=""))
    await session.execute(
        insert(PersonProfile).values(
            id=profile_id,
            user_id=user_id,
            name="No export",
            birth_date=date(1990, 1, 1),
            birth_place="Fixture",
            latitude=0,
            longitude=0,
            timezone="UTC",
        )
    )
    await session.execute(
        insert(NatalChart).values(
            id=chart_id,
            user_id=user_id,
            profile_id=profile_id,
            engine_version="test",
            input_hash="fixture",
            birth_datetime_utc=NOW,
            timezone="UTC",
            latitude=0,
            longitude=0,
        )
    )
    await session.execute(
        insert(CareerProfile).values(
            id=career_id,
            user_id=user_id,
            profile_id=profile_id,
            chart_id=chart_id,
            generation_id=uuid4(),
            idempotency_key="fixture",
            scoring_version="test",
            reference_version="test",
            questionnaire_version="test",
        )
    )
    return career_id, chart_id


async def _segments(
    session: AsyncSession,
    ids: tuple[UUID, UUID],
    at: datetime,
    *,
    status: str,
    distinct: int,
    provider: str = "synthetic-outage-provider",
    error: str | None = None,
    sections: int = 1,
) -> None:
    for _ in range(distinct):
        generation_id = uuid4()
        await session.execute(
            insert(CareerSegmentGeneration),
            [
                {
                    "career_profile_id": ids[0],
                    "chart_id": ids[1],
                    "generation_id": generation_id,
                    "section_key": f"fixture_{index}",
                    "status": status,
                    "prompt_version": "test",
                    "provider": provider,
                    "updated_at": at,
                    "error": error,
                    "output_payload": {"not_for_operator": "private-sentinel"},
                }
                for index in range(sections)
            ],
        )


async def test_provider_incident_debounces_deduplicates_and_resolves_from_positive_recovery(
    s07_sessions: async_sessionmaker[AsyncSession],
) -> None:
    now = NOW + timedelta(days=2)
    async with s07_sessions.begin() as session:
        ids = await _career_fixture(session)
        await _segments(
            session,
            ids,
            now - timedelta(minutes=1),
            status="failed",
            distinct=1,
            sections=6,
            error="career_provider_failure",
        )
        await _segments(
            session,
            ids,
            now - timedelta(minutes=1),
            status="failed",
            distinct=3,
            provider="mock",
            error="career_provider_failure",
        )
        await _segments(
            session, ids, now - timedelta(minutes=1), status="failed", distinct=3, error="career_validation_failure"
        )
        assert not await evaluate_business_alerts(session, now=now)
        await _segments(
            session, ids, now - timedelta(seconds=1), status="failed", distinct=2, error="career_provider_failure"
        )
        assert await evaluate_business_alerts(session, now=now) == (IncidentCode.CAREER_PROVIDER,)
    async with s07_sessions.begin() as session:
        assert not await evaluate_business_alerts(session, now=now + timedelta(minutes=1))
        assert not await evaluate_business_alerts(session, now=now + timedelta(minutes=40))  # silence isn't recovery
        later = now + COOLDOWN
        await _segments(
            session, ids, later - timedelta(seconds=1), status="failed", distinct=3, error="career_provider_failure"
        )
        assert await evaluate_business_alerts(session, now=later) == (IncidentCode.CAREER_PROVIDER,)
    async with s07_sessions.begin() as session:
        await _segments(session, ids, later + timedelta(seconds=1), status="ready", distinct=4)
        assert await evaluate_business_alerts(session, now=later + timedelta(seconds=2)) == (
            IncidentCode.CAREER_PROVIDER,
        )
        assert not await evaluate_business_alerts(session, now=later + timedelta(seconds=3))
        messages = (
            await session.scalars(
                select(BusinessOperatorMessage)
                .where(BusinessOperatorMessage.code == IncidentCode.CAREER_PROVIDER)
                .order_by(BusinessOperatorMessage.created_at)
            )
        ).all()
        assert [message.kind for message in messages] == ["opened", "reminder", "resolved"]
        assert [message.payload for message in messages] == [{}, {}, {}]


@asynccontextmanager
async def _celery_process(log: Path, *args: str) -> AsyncIterator[asyncio.subprocess.Process]:
    with log.open("w") as output:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            *args,
            stdout=output,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            yield proc
        finally:
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=10)
                except TimeoutError:
                    proc.kill()
                    await proc.wait()


def _submit_projection() -> object:
    return app.send_task("analytics.project_business_events").get(timeout=25)


async def _observe_watchdog(broker: str) -> tuple[int, bytes]:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "app.modules.analytics.dead_man",
        env=os.environ | {"CELERY_BROKER_URL": broker},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(process.communicate(), timeout=20)
    assert process.returncode is not None
    return process.returncode, stdout


async def test_real_beat_redis_worker_dispatch_and_independent_watchdog(
    s07_sessions: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    # Prior synthetic test times are fixed; only the real DB clock is used by subprocesses.
    async with s07_sessions.begin() as session:
        now = await session.scalar(select(func.clock_timestamp()))
        assert now is not None and now > NOW + timedelta(days=3)
        day = digest_target(now)
        start, _ = moscow_day_bounds(day)
        await _seed(
            session,
            BusinessEventInput(event_type=EventType.ACCOUNT_VERIFIED, entity_id=uuid4(), occurred_at=start),
            recorded_at=now,
        )
    worker_log, beat_log = tmp_path / "worker.log", tmp_path / "beat.log"
    worker_args = (
        "-m",
        "celery",
        "-A",
        "workers.celery_app.app",
        "worker",
        "-Q",
        "celery",
        "--pool=solo",
        "--loglevel=INFO",
        "--hostname=s07@%h",
    )
    beat_args = (
        "-c",
        "from workers.celery_app import app; "
        "app.conf.beat_schedule = {k: dict(v, schedule=1.0) for k, v in app.conf.beat_schedule.items() "
        "if v['task'].startswith('analytics.')}; import sys; app.start(sys.argv[1:])",
        "beat",
        "--loglevel=INFO",
        "--schedule",
        str(tmp_path / "beat-state"),
    )
    try:
        async with _celery_process(worker_log, *worker_args) as worker, _celery_process(beat_log, *beat_args) as beat:
            async with asyncio.timeout(35):
                while True:
                    assert worker.returncode is None and beat.returncode is None
                    async with s07_sessions() as session:
                        message = await session.get(BusinessOperatorMessage, f"digest:{day}")
                        if message is not None:
                            assert message.payload["counts"] == [
                                {"event_type": "account_verified", "mode": "unknown", "product": None, "count": 1}
                            ]
                            break
                    await asyncio.sleep(0.2)
        broker_down = f"redis+socket://{tmp_path}/does-not-exist.sock?virtual_host=1"
        async with s07_sessions.begin() as session:
            await session.execute(
                update(BusinessOperationsHeartbeat).values(
                    succeeded_at=func.clock_timestamp() - text("interval '11 minutes'"),
                )
            )
        assert await _observe_watchdog(broker_down) == (1, b"business_projection_watchdog=stale\n")
        assert await _observe_watchdog(broker_down) == (1, b"business_projection_watchdog=stale\n")
        async with _celery_process(tmp_path / "replacement-worker.log", *worker_args):
            assert await asyncio.to_thread(_submit_projection) == 0  # replay, but heartbeat resumes
        assert await _observe_watchdog(broker_down) == (0, b"business_projection_watchdog=healthy\n")
        async with s07_sessions() as session:
            messages = (
                await session.scalars(
                    select(BusinessOperatorMessage.kind)
                    .where(BusinessOperatorMessage.code == IncidentCode.PROJECTOR_STALE)
                    .order_by(BusinessOperatorMessage.created_at)
                )
            ).all()
            assert messages == ["opened", "resolved"]
    except BaseException:
        for log in (worker_log, beat_log, tmp_path / "replacement-worker.log"):
            if log.exists():
                print(log.read_text())
        raise


async def _telegram_notice(
    sessions: async_sessionmaker[AsyncSession], *, payload: dict[str, object] | None = None
) -> tuple[datetime, str]:
    key = f"local-telegram-probe:{uuid4()}"
    async with sessions.begin() as session:
        active_since = await session.scalar(select(func.clock_timestamp()))
        assert active_since is not None
        await session.execute(
            insert(BusinessOperatorMessage).values(
                message_key=key,
                code=IncidentCode.PROJECTOR_STALE,
                kind="opened",
                created_at=func.clock_timestamp() + text("interval '0.001 seconds'"),
                payload=payload or {},
            )
        )
    await asyncio.sleep(0.01)
    return active_since, key


@pytest.mark.parametrize("accepted", [True, False])
async def test_telegram_single_attempt_fence_commits_before_http(
    s07_sessions: async_sessionmaker[AsyncSession], accepted: bool
) -> None:
    active_since, key = await _telegram_notice(s07_sessions)
    entered = asyncio.Event()
    release = asyncio.Event()
    sent = []

    async def receive(request: httpx.Request) -> httpx.Response:
        sent.append(request.content)
        async with s07_sessions() as session:
            row = await session.get(BusinessTelegramDelivery, key)
            assert row is not None and row.status == "indeterminate" and row.acknowledged_at is None
        entered.set()
        await release.wait()
        if not accepted:
            raise httpx.ReadTimeout("mock: response lost", request=request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 5, "chat": {"id": -1234}}})

    transport = TelegramTransport(
        TelegramDestination(SecretStr("123:synthetic"), -1234), mock_transport=httpx.MockTransport(receive)
    )
    assert (
        await deliver_once(s07_sessions, transport, active_since=active_since + timedelta(minutes=1))
        is DeliveryStatus.IDLE
    )
    async with asyncio.TaskGroup() as tasks:
        sending = tasks.create_task(deliver_once(s07_sessions, transport, active_since=active_since))
        await asyncio.wait_for(entered.wait(), timeout=3)
        assert await deliver_once(s07_sessions, transport, active_since=active_since) is DeliveryStatus.IDLE
        release.set()
    expected = DeliveryStatus.ACKNOWLEDGED if accepted else DeliveryStatus.INDETERMINATE
    assert sending.result() is expected
    assert await deliver_once(s07_sessions, transport, active_since=active_since) is DeliveryStatus.IDLE
    assert len(sent) == 1 and b"projector_stale" in sent[0] and key.encode() not in sent[0]
    async with s07_sessions() as session:
        row = await session.get(BusinessTelegramDelivery, key)
        assert row is not None and row.status == expected and (row.acknowledged_at is not None) == accepted


async def test_telegram_cancelled_runner_and_invalid_message_never_replay(
    s07_sessions: async_sessionmaker[AsyncSession],
) -> None:
    active_since, key = await _telegram_notice(s07_sessions)
    entered = asyncio.Event()
    sent = []

    async def receive(request: httpx.Request) -> httpx.Response:
        sent.append(request.content)
        entered.set()
        await asyncio.Future[None]()
        raise AssertionError("blocking transport should be cancelled")

    transport = TelegramTransport(
        TelegramDestination(SecretStr("123:synthetic"), -1234), mock_transport=httpx.MockTransport(receive)
    )
    async with asyncio.TaskGroup() as tasks:
        sending = tasks.create_task(deliver_once(s07_sessions, transport, active_since=active_since))
        await asyncio.wait_for(entered.wait(), timeout=3)
        sending.cancel()
    with pytest.raises(asyncio.CancelledError):
        sending.result()
    _, invalid_key = await _telegram_notice(s07_sessions, payload={"free_text": "do not export"})
    assert await deliver_once(s07_sessions, transport, active_since=active_since) is DeliveryStatus.INVALID_MESSAGE
    assert await deliver_once(s07_sessions, transport, active_since=active_since) is DeliveryStatus.IDLE
    assert len(sent) == 1
    async with s07_sessions() as session:
        old = await session.get(BusinessTelegramDelivery, key)
        invalid = await session.get(BusinessTelegramDelivery, invalid_key)
        assert old is not None and old.status == DeliveryStatus.INDETERMINATE
        assert invalid is not None and invalid.status == DeliveryStatus.INVALID_MESSAGE
