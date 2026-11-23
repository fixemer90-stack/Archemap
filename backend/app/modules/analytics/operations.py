"""Bounded, PostgreSQL-owned projections and operator notification intents.

All public SQL operations take a transaction owned by their caller; rollback
never leaves a projected contribution or notification without its state change.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from sqlalchemy import Date, case, cast, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.models import BusinessEvent, BusinessEventOutbox
from app.modules.analytics.operations_models import (
    CAREER_OBSERVATION_PREDICATE,
    BusinessDailyCount,
    BusinessIncident,
    BusinessOperationsHeartbeat,
    BusinessOperatorMessage,
)
from app.modules.analytics.service import utc_time
from app.modules.analytics.watchdog_status import WatchdogStatus
from app.modules.career.models import CareerSegmentGeneration

MOSCOW = ZoneInfo("Europe/Moscow")
PROJECTOR = "projector"
STALE_AFTER = timedelta(minutes=10)
COOLDOWN = timedelta(hours=1)
PROVIDER_WINDOW = timedelta(minutes=30)
PROJECTION_BATCH_SIZE = 1_000


class IncidentCode(StrEnum):
    PROJECTOR_STALE = "projector_stale"
    PROJECTION_BACKLOG = "projection_backlog"
    CAREER_PROVIDER = "career_provider_degraded"


@dataclass(frozen=True, slots=True)
class ProviderSample:
    failed: int
    ready: int
    ready_after_failure: int


def provider_state(sample: ProviderSample) -> bool | None:
    if sample.failed >= 3 and sample.failed >= sample.ready:
        return True
    if sample.ready_after_failure >= 3 and sample.ready > sample.failed:
        return False
    return None  # low traffic or inconclusive evidence is not recovery


def digest_target(now: datetime) -> date:
    local = utc_time(now).astimezone(MOSCOW)
    return local.date() - timedelta(days=1 if local.time() >= time(10) else 2)


def moscow_day_bounds(day: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(day, time.min, MOSCOW).astimezone(UTC),
        datetime.combine(day + timedelta(days=1), time.min, MOSCOW).astimezone(UTC),
    )


async def _lock(session: AsyncSession, slot: int) -> bool:
    # Separate transaction locks: a hung broker/projector cannot block the watchdog.
    return (await session.scalar(select(func.pg_try_advisory_xact_lock(2307, slot)))) is True


async def _clock(session: AsyncSession, now: datetime | None) -> datetime:
    if now is None:
        now = await session.scalar(select(func.clock_timestamp()))
    assert now is not None
    return utc_time(now)


async def project_business_events(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Consume a bounded batch, upsert day buckets and heartbeat atomically.

    This is an in-database operation (no work across transactions), so the row
    lock replaces a separately committed claim. Existing live leases are never
    adopted; expired leases and attempt caps retain S02's semantics.
    """
    if not await _lock(session, 1):
        return 0
    started = await _clock(session, now)
    pending = (
        select(BusinessEventOutbox.id)
        .where(
            BusinessEventOutbox.destination == "internal_projection",
            BusinessEventOutbox.status == "pending",
            BusinessEventOutbox.attempts < 10,
            BusinessEventOutbox.next_attempt_at <= started,
            or_(BusinessEventOutbox.lease_until.is_(None), BusinessEventOutbox.lease_until <= started),
        )
        .order_by(BusinessEventOutbox.next_attempt_at, BusinessEventOutbox.id)
        .limit(PROJECTION_BATCH_SIZE)
        .with_for_update(skip_locked=True)
        .cte("due")
    )
    consumed = (
        update(BusinessEventOutbox)
        .where(BusinessEventOutbox.id == pending.c.id)
        .values(
            status="delivered",
            attempts=BusinessEventOutbox.attempts + 1,
            claim_token=None,
            lease_until=None,
            delivered_at=started,
            updated_at=started,
        )
        .returning(BusinessEventOutbox.event_id)
        .cte("consumed")
    )
    day = cast(func.timezone(MOSCOW.key, BusinessEvent.occurred_at), Date)
    product = func.coalesce(BusinessEvent.product, "")
    groups = (
        select(day, BusinessEvent.event_type, BusinessEvent.mode, product, func.count())
        .join_from(BusinessEvent, consumed, consumed.c.event_id == BusinessEvent.id)
        .group_by(day, BusinessEvent.event_type, BusinessEvent.mode, product)
    )
    daily = insert(BusinessDailyCount).from_select(
        ["business_date", "event_type", "mode", "product", "event_count"], groups
    )
    merged = (
        daily.on_conflict_do_update(
            index_elements=["business_date", "event_type", "mode", "product"],
            set_={"event_count": BusinessDailyCount.event_count + daily.excluded.event_count},
        )
        .returning(BusinessDailyCount.business_date)
        .cte("merged")
    )
    # The modifying CTE runs to completion even though only consumed rows are counted.
    count = await session.scalar(select(func.count()).select_from(consumed).add_cte(merged))
    succeeded = await _clock(session, now)
    heartbeat = insert(BusinessOperationsHeartbeat).values(job=PROJECTOR, succeeded_at=succeeded)
    await session.execute(
        heartbeat.on_conflict_do_update(
            index_elements=["job"],
            set_={
                "succeeded_at": func.greatest(BusinessOperationsHeartbeat.succeeded_at, heartbeat.excluded.succeeded_at)
            },
        )
    )
    return int(count or 0)


async def _heartbeat(session: AsyncSession) -> datetime | None:
    value: datetime | None = await session.scalar(
        select(BusinessOperationsHeartbeat.succeeded_at).where(BusinessOperationsHeartbeat.job == PROJECTOR)
    )
    return value


def _fresh(heartbeat: datetime | None, now: datetime) -> bool:
    return heartbeat is not None and now - STALE_AFTER < heartbeat <= now


async def create_daily_digest(session: AsyncSession, *, now: datetime | None = None) -> bool:
    # Freeze the committed counts and the corresponding watermark across digest readback.
    if not await _lock(session, 2) or not await _lock(session, 1):
        return False
    heartbeat = await _heartbeat(session)
    observed_at = await _clock(session, now)
    if heartbeat is None or not _fresh(heartbeat, observed_at):
        return False
    day = digest_target(observed_at)
    key = f"digest:{day.isoformat()}"
    if await session.get(BusinessOperatorMessage, key) is not None:
        return False
    start, end = moscow_day_bounds(day)
    # Never publish a known partial window, including due, leased or exhausted rows.
    pending = (
        select(BusinessEventOutbox.id)
        .join(BusinessEvent, BusinessEvent.id == BusinessEventOutbox.event_id)
        .where(
            BusinessEventOutbox.destination == "internal_projection",
            BusinessEventOutbox.status == "pending",
            BusinessEvent.occurred_at >= start,
            BusinessEvent.occurred_at < end,
        )
    )
    if await session.scalar(select(pending.exists())):
        return False
    rows = await session.execute(
        select(
            BusinessDailyCount.event_type,
            BusinessDailyCount.mode,
            BusinessDailyCount.product,
            BusinessDailyCount.event_count,
        )
        .where(BusinessDailyCount.business_date == day)
        .order_by(BusinessDailyCount.event_type, BusinessDailyCount.mode, BusinessDailyCount.product)
    )
    session.add(
        BusinessOperatorMessage(
            message_key=key,
            code="daily_business_digest",
            kind="digest",
            created_at=observed_at,
            payload={
                "timezone": MOSCOW.key,
                "from_utc": start.isoformat(),
                "to_utc": end.isoformat(),
                "projector_succeeded_at": heartbeat.isoformat(),
                "coverage": "recorded_facts_only",
                "counts": [
                    {"event_type": event, "mode": mode, "product": product or None, "count": count}
                    for event, mode, product, count in rows
                ],
            },
        )
    )
    return True


async def _record_incident(
    session: AsyncSession, code: IncidentCode, breached: bool | None, now: datetime
) -> str | None:
    if breached is None:
        return None
    incident = await session.get(BusinessIncident, code, populate_existing=True)
    if breached:
        if incident is None:
            incident = BusinessIncident(code=code, opened_at=now, last_notified_at=now, resolved_at=None)
            session.add(incident)
            kind = "opened"
        elif incident.resolved_at is not None:
            incident.opened_at = now
            incident.resolved_at = None
            kind = "opened"
        elif now - incident.last_notified_at >= COOLDOWN:
            kind = "reminder"
        else:
            return None
    elif incident is not None and incident.resolved_at is None:
        incident.resolved_at = now
        kind = "resolved"
    else:
        return None
    incident.last_notified_at = now
    session.add(
        BusinessOperatorMessage(
            message_key=f"{code}:{kind}:{now.isoformat()}", code=code, kind=kind, created_at=now, payload={}
        )
    )
    return kind


async def _career_sample(session: AsyncSession, now: datetime) -> ProviderSample:
    segment = CareerSegmentGeneration
    observed = (
        select(segment.generation_id, segment.status, segment.error, segment.updated_at)
        .where(
            text(CAREER_OBSERVATION_PREDICATE), segment.updated_at >= now - PROVIDER_WINDOW, segment.updated_at < now
        )
        .cte("observed")
    )
    failed = (observed.c.status == "failed") & (observed.c.error == "career_provider_failure")
    ready = observed.c.status == "ready"
    latest_failure = select(func.max(observed.c.updated_at)).where(failed).scalar_subquery()
    # Count generations, not sections/retries, and only newer successes for recovery.
    per_generation = (
        select(
            func.bool_or(case((failed, True), else_=False)).label("failed"),
            func.bool_or(ready).label("ready"),
            func.bool_or(ready & (or_(latest_failure.is_(None), observed.c.updated_at > latest_failure))).label(
                "recovered"
            ),
        )
        .group_by(observed.c.generation_id)
        .cte("per_generation")
    )
    sample = (
        await session.execute(
            select(
                func.count().filter(per_generation.c.failed),
                func.count().filter(~per_generation.c.failed & per_generation.c.ready),
                func.count().filter(~per_generation.c.failed & per_generation.c.recovered),
            )
        )
    ).one()
    return ProviderSample(sample[0], sample[1], sample[2])


async def evaluate_business_alerts(session: AsyncSession, *, now: datetime | None = None) -> tuple[str, ...]:
    if not await _lock(session, 3):
        return ()
    observed_at = await _clock(session, now)
    pending = select(BusinessEventOutbox.id).where(
        BusinessEventOutbox.status == "pending",
        BusinessEventOutbox.destination == "internal_projection",
        or_(BusinessEventOutbox.created_at <= observed_at - STALE_AFTER, BusinessEventOutbox.attempts >= 10),
    )
    backlog = (await session.scalar(select(pending.exists()))) is True
    provider = provider_state(await _career_sample(session, observed_at))
    raised = []
    for code, breached in ((IncidentCode.PROJECTION_BACKLOG, backlog), (IncidentCode.CAREER_PROVIDER, provider)):
        if await _record_incident(session, code, breached, observed_at) is not None:
            raised.append(code.value)
    return tuple(raised)


async def check_dead_man(session: AsyncSession, *, now: datetime | None = None) -> WatchdogStatus:
    """An independent PostgreSQL observer; invokes neither Redis nor Celery."""
    if not await _lock(session, 4):
        return WatchdogStatus.BUSY
    heartbeat = await _heartbeat(session)
    observed_at = await _clock(session, now)
    stale = not _fresh(heartbeat, observed_at)
    await _record_incident(session, IncidentCode.PROJECTOR_STALE, stale, observed_at)
    return WatchdogStatus.STALE if stale else WatchdogStatus.HEALTHY
