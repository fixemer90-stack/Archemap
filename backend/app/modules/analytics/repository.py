"""PostgreSQL semantic uniqueness. All writes stay in the caller transaction."""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.models import BusinessEvent, BusinessEventOutbox
from app.modules.analytics.schemas import BusinessEventInput, OutboxClaim


class BusinessEventConflictError(ValueError):
    """A semantic identity already has different immutable business facts."""


def immutable_values(event: BusinessEventInput) -> dict[str, object]:
    return {
        "schema_version": event.schema_version,
        "event_type": event.event_type.value,
        "semantic_key": event.semantic_key,
        "entity_id": event.entity_id,
        "source_id": event.source_id,
        "subject_id": event.subject_id,
        "occurred_at": event.occurred_at,
        "mode": event.mode.value,
        "product": event.product.value if event.product is not None else None,
        "details": event.details.model_dump(mode="json", exclude_none=True),
    }


async def insert_event(
    session: AsyncSession, event: BusinessEventInput, recorded_at: datetime
) -> tuple[UUID, datetime]:
    values = immutable_values(event)
    # SAVEPOINT protects the event/outbox pair even if caller catches an error and commits.
    async with session.begin_nested():
        inserted_id = await session.scalar(
            insert(BusinessEvent)
            .values(id=uuid4(), created_at=recorded_at, updated_at=recorded_at, **values)
            .on_conflict_do_nothing(constraint="uq_business_events_semantic_key")
            .returning(BusinessEvent.id)
        )
        # Read persisted scalar columns, never a possibly dirty identity-map instance.
        table = BusinessEvent.metadata.tables[BusinessEvent.__tablename__]
        stored = (
            (await session.execute(select(table).where(table.c.semantic_key == event.semantic_key))).mappings().one()
        )
        if any(stored[key] != value for key, value in values.items()):
            raise BusinessEventConflictError("business event identity conflicts with stored facts")
        if inserted_id is not None:
            await session.execute(
                insert(BusinessEventOutbox).values(
                    id=uuid4(),
                    event_id=stored["id"],
                    destination="internal_projection",
                    status="pending",
                    attempts=0,
                    next_attempt_at=recorded_at,
                    created_at=recorded_at,
                    updated_at=recorded_at,
                    claim_token=None,
                    lease_until=None,
                    delivered_at=None,
                )
            )
    return stored["id"], stored["created_at"]


async def claim_internal(session: AsyncSession, now: datetime, lease_seconds: int) -> OutboxClaim | None:
    row = await session.scalar(
        select(BusinessEventOutbox)
        .where(
            BusinessEventOutbox.destination == "internal_projection",
            BusinessEventOutbox.status == "pending",
            BusinessEventOutbox.attempts < 10,
            BusinessEventOutbox.next_attempt_at <= now,
            or_(BusinessEventOutbox.lease_until.is_(None), BusinessEventOutbox.lease_until <= now),
        )
        .order_by(BusinessEventOutbox.next_attempt_at, BusinessEventOutbox.id)
        .limit(1)
        .with_for_update(skip_locked=True)
        .execution_options(populate_existing=True)
    )
    if row is None:
        return None
    token = uuid4()
    row.claim_token = token
    row.lease_until = now + timedelta(seconds=lease_seconds)
    row.attempts += 1
    row.updated_at = now
    await session.flush()
    return OutboxClaim(outbox_id=row.id, event_id=row.event_id, token=token)


async def finish_internal(
    session: AsyncSession,
    claim: OutboxClaim,
    now: datetime,
    *,
    retry_seconds: int | None,
) -> bool:
    values: dict[str, object] = {"claim_token": None, "lease_until": None, "updated_at": now}
    if retry_seconds is None:
        values.update(status="delivered", delivered_at=now)
    else:
        values["next_attempt_at"] = now + timedelta(seconds=retry_seconds)
    changed = await session.scalar(
        update(BusinessEventOutbox)
        .where(
            BusinessEventOutbox.id == claim.outbox_id,
            BusinessEventOutbox.event_id == claim.event_id,
            BusinessEventOutbox.destination == "internal_projection",
            BusinessEventOutbox.status == "pending",
            BusinessEventOutbox.claim_token == claim.token,
            BusinessEventOutbox.lease_until > now,
        )
        .values(**values)
        .returning(BusinessEventOutbox.id)
        .execution_options(synchronize_session=False)
    )
    return changed is not None
