"""Task helpers for asynchronous narrative generation."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.infrastructure.database import async_session_factory
from app.modules.llm import LLMProviderUnavailableError, LLMTimeoutError
from app.modules.report_narratives.models import ReportNarrative
from app.modules.report_narratives.service import ReportNarrativeService
from app.modules.reports.models import Report

T = TypeVar("T")


def _run_async(coro: Coroutine[Any, Any, T]) -> T:  # noqa: UP047
    """Run async code in a synchronous Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def generate_report_narrative_task(report_id: str, *, force: bool = False) -> dict[str, str]:
    """Synchronously invoke the async narrative generation flow."""
    narrative = _run_async(_generate_report_narrative_async(UUID(report_id), force=force))
    return {
        "report_id": report_id,
        "narrative_id": str(narrative.id),
        "status": narrative.status,
    }


def finalize_narrative_task_failure(report_id: str, error_message: str) -> None:
    """Persist terminal narrative failure state after retries are exhausted."""
    _run_async(_finalize_narrative_task_failure_async(UUID(report_id), error_message))


def should_retry_narrative_task_error(exc: Exception) -> bool:
    """Only provider timeouts/unavailability should be retried by Celery."""
    return isinstance(exc, (LLMTimeoutError, LLMProviderUnavailableError))


async def _generate_report_narrative_async(report_id: UUID, *, force: bool = False) -> ReportNarrative:
    async with async_session_factory() as db:
        service = ReportNarrativeService(db)
        try:
            narrative = await service.generate_for_report(report_id, force=force)
            await db.commit()
            return narrative
        except Exception:
            await db.commit()
            raise


async def _finalize_narrative_task_failure_async(report_id: UUID, error_message: str) -> None:
    async with async_session_factory() as db:
        report_result = await db.execute(select(Report).where(Report.id == report_id))
        report = report_result.scalar_one_or_none()
        if report is None:
            raise NotFoundError("Report not found")

        narrative_result = await db.execute(
            select(ReportNarrative)
            .where(ReportNarrative.report_id == report_id)
            .order_by(ReportNarrative.created_at.desc())
        )
        narrative = narrative_result.scalars().first()
        if narrative is not None:
            narrative.status = "narrative_failed"
            narrative.error_message = error_message
            narrative.generation_finished_at = datetime.now(UTC).replace(tzinfo=None)

        report.status = "narrative_failed"
        report.error_message = error_message
        await db.commit()
