"""Recovery dispatcher for committed birth-data refinements."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select

from app.config import settings
from app.infrastructure.celery_async import run_async_in_worker
from app.infrastructure.database import async_session_factory
from app.modules.profiles.dispatch import dispatch_pending_birth_data_revisions
from app.modules.profiles.models import ProfileBirthDataRevision
from app.modules.profiles.observability import birth_data_refinement_telemetry
from workers.celery_app import app

logger = structlog.get_logger()


@app.task(name="profiles.dispatch_birth_data_refinements")  # type: ignore[untyped-decorator]
def dispatch_birth_data_refinements() -> dict[str, Any]:
    return run_async_in_worker(_dispatch_birth_data_refinements_async())


async def _dispatch_birth_data_refinements_async() -> dict[str, Any]:
    async with async_session_factory() as session:
        dispatched, failed = await dispatch_pending_birth_data_revisions(session)
    return {"dispatched": dispatched, "failed": failed}


@app.task(name="profiles.monitor_birth_data_refinements")  # type: ignore[untyped-decorator]
def monitor_birth_data_refinements() -> dict[str, Any]:
    return run_async_in_worker(_monitor_birth_data_refinements_async())


async def _monitor_birth_data_refinements_async(*, now: datetime | None = None) -> dict[str, Any]:
    current_time = now or datetime.now(UTC)
    stuck_cutoff = current_time - timedelta(minutes=settings.BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES)
    failed_cutoff = current_time - timedelta(minutes=settings.BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES)
    async with async_session_factory() as session:
        stuck_result = await session.execute(
            select(func.count())
            .select_from(ProfileBirthDataRevision)
            .where(
                ProfileBirthDataRevision.status.in_(("queued", "processing")),
                ProfileBirthDataRevision.updated_at < stuck_cutoff,
            )
        )
        failed_result = await session.execute(
            select(func.count())
            .select_from(ProfileBirthDataRevision)
            .where(
                ProfileBirthDataRevision.error_code.in_(("narrative_generation_failed", "report_generation_failed")),
                ProfileBirthDataRevision.updated_at >= failed_cutoff,
            )
        )
        stuck = int(stuck_result.scalar_one())
        recent_failed = int(failed_result.scalar_one())

    birth_data_refinement_telemetry.set_stuck_generations(stuck)
    birth_data_refinement_telemetry.set_recent_failures(recent_failed)
    alerted = stuck > 0 or recent_failed > 0
    if alerted:
        logger.warning(
            "birth_data_refinement_alert",
            stuck=stuck,
            recent_failed=recent_failed,
            stuck_after_minutes=settings.BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES,
            monitor_window_minutes=settings.BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES,
        )
    return {"stuck": stuck, "recent_failed": recent_failed, "alerted": alerted}
