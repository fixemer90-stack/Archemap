"""Owner attribution, consent revocation and the read-only S08 boundary."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.attribution_models import AnalyticsAttribution as Attribution
from app.modules.analytics.attribution_settings import (
    CLIENT_ID_PATTERN,
    PENDING_SECONDS,
    AttributionPolicy,
    approved_attribution_policy,
)
from app.modules.analytics.service import utc_time


@dataclass(frozen=True, slots=True)
class ActiveAttribution:
    owner_id: UUID
    policy_version: str
    counter_id: int
    client_id: str = field(repr=False)
    captured_at: datetime
    bound_at: datetime
    expires_at: datetime


def receipt_is_fresh(captured_at: datetime, now: datetime) -> bool:
    return captured_at <= now < captured_at + timedelta(seconds=PENDING_SECONDS)


async def bind_attribution(
    session: AsyncSession,
    *,
    owner_id: UUID,
    policy: AttributionPolicy,
    client_id: str | None,
    captured_at: datetime,
    now: datetime,
) -> bool:
    """Only the authenticated collector calls this with a consumed server receipt."""
    captured_at, now = utc_time(captured_at), utc_time(now)
    expires_at = captured_at + policy.retention
    if now >= expires_at or not receipt_is_fresh(captured_at, now):
        return False
    if client_id is not None and not re.fullmatch(CLIENT_ID_PATTERN, client_id):
        raise ValueError("invalid ClientID")
    statement = insert(Attribution).values(
        owner_id=owner_id,
        policy_version=policy.version,
        counter_id=policy.counter_id,
        client_id=client_id,
        captured_at=captured_at,
        bound_at=now,
        expires_at=expires_at,
        revoked_at=None,
    )
    # One active consent interval per owner. A null observation cannot erase a
    # known ID or refresh its clock; an outstanding pre-revocation ticket cannot
    # revive consent even if it is attached after the revoke transaction commits.
    eligible = (
        (Attribution.revoked_at.is_not(None) & (Attribution.revoked_at < captured_at))
        | (Attribution.expires_at <= now)
        | (Attribution.policy_version != policy.version)
        | (Attribution.counter_id.is_distinct_from(policy.counter_id) & statement.excluded.client_id.is_not(None))
        | (Attribution.client_id.is_(None) & (statement.excluded.client_id.is_not(None)))
    )
    changed = await session.scalar(
        statement.on_conflict_do_update(
            index_elements=[Attribution.owner_id],
            set_={
                key: statement.excluded[key]
                for key in (
                    "policy_version",
                    "counter_id",
                    "client_id",
                    "captured_at",
                    "bound_at",
                    "expires_at",
                    "revoked_at",
                )
            },
            where=eligible & (Attribution.revoked_at.is_(None) | (Attribution.revoked_at < captured_at)),
        ).returning(Attribution.owner_id)
    )
    return changed is not None


async def revoke_attribution(session: AsyncSession, *, owner_id: UUID, now: datetime) -> None:
    """Clear the ID; briefly retain only a stamp to fence pending receipts."""
    now = utc_time(now)
    # Never acknowledge revocation before the primary has flushed its commit.
    await session.execute(text("SET LOCAL synchronous_commit = on"))
    values = {
        "policy_version": None,
        "counter_id": None,
        "client_id": None,
        "captured_at": None,
        "bound_at": None,
        "revoked_at": now,
        "expires_at": now + timedelta(seconds=PENDING_SECONDS),
    }
    await session.execute(
        insert(Attribution)
        .values(owner_id=owner_id, **values)
        .on_conflict_do_update(
            index_elements=[Attribution.owner_id],
            set_=values,
            where=(Attribution.revoked_at.is_(None) | (Attribution.revoked_at < now))
            & (Attribution.captured_at.is_(None) | (Attribution.captured_at <= now)),
        )
    )


async def read_active_attribution(
    session: AsyncSession,
    *,
    owner_id: UUID,
    approved_policy_version: str,
    approved_counter_id: int,
    occurred_at: datetime,
    now: datetime,
    for_dispatch: bool = False,
) -> ActiveAttribution | None:
    """S08: require current consent at both original occurrence and send-time.

    The optional final read locks the exact eligible owner row until the caller
    ends the transaction. S05's revoke upsert (and rebind/purge) must acquire
    that same row lock. Never use an unlocked snapshot for dispatch.
    """
    occurred_at, now = utc_time(occurred_at), utc_time(now)
    policy = approved_attribution_policy()
    if (
        policy is None
        or policy.version != approved_policy_version
        or policy.counter_id != approved_counter_id
        or occurred_at > now
    ):
        return None
    statement = select(
        Attribution.client_id, Attribution.captured_at, Attribution.bound_at, Attribution.expires_at
    ).where(
        Attribution.owner_id == owner_id,
        Attribution.policy_version == policy.version,
        Attribution.counter_id == approved_counter_id,
        Attribution.revoked_at.is_(None),
        Attribution.client_id.is_not(None),
        Attribution.bound_at <= occurred_at,
        Attribution.expires_at > now,
        Attribution.captured_at > now - policy.retention,
    )
    if for_dispatch:
        statement = statement.with_for_update()
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        return None
    client_id, captured_at, bound_at, expires_at = row._tuple()
    if client_id is None or captured_at is None or bound_at is None:
        return None
    return ActiveAttribution(
        owner_id,
        policy.version,
        policy.counter_id,
        client_id,
        captured_at,
        bound_at,
        min(expires_at, captured_at + policy.retention),
    )


async def purge_expired_attribution(session: AsyncSession, *, now: datetime, limit: int = 1_000) -> None:
    """Local retention-operation primitive; caller owns schedule and commit."""
    if type(limit) is not int or not 1 <= limit <= 10_000:
        raise ValueError("invalid purge batch size")
    expired = (
        select(Attribution.owner_id)
        .where(Attribution.expires_at <= utc_time(now))
        .order_by(Attribution.expires_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    await session.execute(delete(Attribution).where(Attribution.owner_id.in_(expired)))
