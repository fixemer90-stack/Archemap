"""Durable dispatcher for committed birth-data refinement generations."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.profiles.refinement import BirthDataRevisionRepository

DISPATCH_CLAIM_TTL = timedelta(minutes=5)
logger = structlog.get_logger()


def _send_generation(
    *, revision_id: uuid.UUID, profile_id: uuid.UUID, user_id: uuid.UUID, generation_id: uuid.UUID
) -> Any:
    from workers.tasks.astrotype_v2 import generate_natal_report_v2

    return generate_natal_report_v2.apply_async(
        kwargs={
            "profile_id": str(profile_id),
            "user_id": str(user_id),
            "generation_id": str(generation_id),
            "revision_id": str(revision_id),
            "force": True,
        },
        task_id=f"birth-refinement-{generation_id}",
    )


async def dispatch_birth_data_revision(
    session: AsyncSession,
    *,
    revision_id: uuid.UUID,
    sender: Callable[..., Any] = _send_generation,
    now: datetime | None = None,
) -> bool:
    """Claim and dispatch one durable refinement row.

    The claim is committed before broker publication. Stale claims are retried by
    the periodic dispatcher. Celery receives a stable task id, while the worker
    performs its own generation claim before doing any report work.
    """

    current = now or datetime.now(UTC)
    repository = BirthDataRevisionRepository(session)
    revision = await repository.claim_dispatch(
        revision_id=revision_id,
        stale_before=current - DISPATCH_CLAIM_TTL,
    )
    if revision is None:
        return True
    await session.commit()

    try:
        sender(
            revision_id=revision.id,
            profile_id=revision.profile_id,
            user_id=revision.user_id,
            generation_id=revision.generation_id,
        )
    except Exception:
        await repository.release_dispatch(revision_id=revision.id, error_code="broker_unavailable")
        await session.commit()
        logger.warning(
            "birth_data_refinement_dispatch_failed",
            revision_id=str(revision.id),
            generation_id=str(revision.generation_id),
            error_code="broker_unavailable",
        )
        return False

    await repository.mark_dispatched(revision_id=revision.id)
    await session.commit()
    return True


async def dispatch_pending_birth_data_revisions(
    session: AsyncSession,
    *,
    limit: int = 100,
    sender: Callable[..., Any] = _send_generation,
    now: datetime | None = None,
) -> tuple[int, int]:
    current = now or datetime.now(UTC)
    repository = BirthDataRevisionRepository(session)
    revision_ids = await repository.list_dispatchable(
        stale_before=current - DISPATCH_CLAIM_TTL,
        limit=limit,
    )
    dispatched = 0
    failed = 0
    for revision_id in revision_ids:
        if await dispatch_birth_data_revision(session, revision_id=revision_id, sender=sender, now=current):
            dispatched += 1
        else:
            failed += 1
    return dispatched, failed
