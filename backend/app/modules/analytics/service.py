"""Caller-owned transaction API. No commit, HTTP, jobs or external destinations."""

from asyncio import CancelledError
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.repository import claim_internal, finish_internal, insert_event
from app.modules.analytics.schemas import BusinessEventInput, OutboxClaim


@dataclass(frozen=True, slots=True)
class RecordedBusinessEvent:
    id: UUID
    created_at: datetime


def utc_time(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("aware clock required")
    return value.astimezone(UTC)


async def emit_business_event(
    session: AsyncSession,
    event: BusinessEventInput,
    *,
    recorded_at: datetime | None = None,
) -> RecordedBusinessEvent:
    """Persist a fact and internal intent without committing the caller transaction.

    Identity is event type + canonical local entity UUID, never a client-provided key.
    A retry must retain original occurrence time and all immutable input facts.
    A failed emit aborts the entire unit of work, including caller writes.
    """
    try:
        validated = BusinessEventInput.model_validate(event)
        clock = datetime.now(UTC) if recorded_at is None else utc_time(recorded_at)
        event_id, created_at = await insert_event(session, validated, clock)
    except (Exception, CancelledError):
        await session.rollback()
        raise
    return RecordedBusinessEvent(event_id, created_at)


async def claim_outbox(
    session: AsyncSession,
    *,
    now: datetime,
    lease_seconds: int,
) -> OutboxClaim | None:
    """Claim only internal idempotent work. Caller must commit before processing.

    Ten failed/expired attempts exhaust the row for explicit operator review;
    no background dispatcher or external uploader is installed here.
    """
    if type(lease_seconds) is not int or not 1 <= lease_seconds <= 3600:
        raise ValueError("lease seconds must be an integer in [1, 3600]")
    return await claim_internal(session, utc_time(now), lease_seconds)


async def complete_outbox(session: AsyncSession, claim: OutboxClaim, *, now: datetime) -> bool:
    """Finalize in the same transaction as an idempotent internal projection write."""
    return await finish_internal(session, claim, utc_time(now), retry_seconds=None)


async def retry_outbox(
    session: AsyncSession,
    claim: OutboxClaim,
    *,
    now: datetime,
    delay_seconds: int,
) -> bool:
    """Release a current lease for bounded internal retry; no exception text stored."""
    if type(delay_seconds) is not int or not 1 <= delay_seconds <= 86400:
        raise ValueError("retry seconds must be an integer in [1, 86400]")
    return await finish_internal(session, claim, utc_time(now), retry_seconds=delay_seconds)
