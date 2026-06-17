"""Celery tasks for report PDF generation."""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any, TypeVar
from uuid import UUID

import structlog
from sqlalchemy import select

from app.infrastructure import model_registry as _model_registry  # noqa: F401
from app.infrastructure.celery_async import run_async_in_worker
from app.infrastructure.database import async_session_factory
from app.modules.report_narratives.service import get_latest_narrative_for_report
from app.modules.reports.models import Report
from app.modules.reports.pdf import generate_report_pdf

logger = structlog.get_logger()

T = TypeVar("T")


def _run_async(coro: Coroutine[Any, Any, T]) -> T:  # noqa: UP047
    """Run async code in sync Celery task."""
    return run_async_in_worker(coro)


def generate_pdf_task(report_id: str, user_id: str, profile_name: str = "") -> dict[str, Any]:
    """Generate PDF bytes for a report from persisted JSON.

    Legacy task entrypoint retained for compatibility, but the application no
    longer stores generated PDF artifacts in S3. Runtime downloads are rendered
    on demand by the reports API.
    """
    logger.info("pdf_task_start", report_id=report_id)

    try:
        result = _run_async(
            _generate_pdf_async(
                report_id=UUID(report_id),
                user_id=UUID(user_id),
                profile_name=profile_name,
            )
        )
        logger.info("pdf_task_success", report_id=report_id)
        return result
    except Exception as e:
        logger.error("pdf_task_failed", report_id=report_id, error=str(e))
        raise


async def _generate_pdf_async(
    report_id: UUID,
    user_id: UUID,
    profile_name: str,
) -> dict[str, Any]:
    """Async PDF generation logic."""
    async with async_session_factory() as db:
        # Load report
        result = await db.execute(select(Report).where(Report.id == report_id, Report.user_id == user_id))
        report = result.scalar_one_or_none()
        if report is None:
            raise ValueError(f"Report {report_id} not found")

        if not report.report_data:
            raise ValueError(f"Report {report_id} has no data")

        # Load latest saved narrative if present; PDF must never trigger a new LLM call.
        narrative = await get_latest_narrative_for_report(db=db, report_id=report_id, report=report)

        # Generate PDF from persisted JSON. Do not upload/store the artifact.
        pdf_bytes = generate_report_pdf(
            report.report_data,
            profile_name,
            narrative_content=narrative.content if narrative is not None else None,
            narrative_status=narrative.status if narrative is not None else None,
            narrative_error=narrative.error_message if narrative is not None else None,
        )

        return {
            "report_id": str(report_id),
            "size": len(pdf_bytes),
            "stored": False,
        }
