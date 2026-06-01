"""Celery tasks for report PDF generation."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar
from uuid import UUID

import structlog
from sqlalchemy import select

from app.infrastructure.database import async_session_factory
from app.modules.reports.models import Report
from app.modules.reports.pdf import generate_report_pdf
from app.modules.reports.storage import S3Storage, build_report_key, get_signed_ttl

logger = structlog.get_logger()

T = TypeVar("T")


def _run_async(coro: Coroutine[Any, Any, T]) -> T:  # noqa: UP047
    """Run async code in sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def generate_pdf_task(report_id: str, user_id: str, profile_name: str = "") -> dict[str, Any]:
    """Generate PDF for a report and upload to S3.

    Called asynchronously by Celery after report generation.
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

        # Generate PDF
        pdf_bytes = generate_report_pdf(report.report_data, profile_name)

        # Upload to S3
        storage = S3Storage()
        key = build_report_key(
            user_id=str(user_id),
            report_id=str(report_id),
            version=report.version,
        )
        await storage.upload(key, pdf_bytes, content_type="application/pdf")

        # Generate signed URL
        ttl = get_signed_ttl(report.mode)
        signed_url = storage.get_signed_url(key, expires_in=ttl)

        # Update report
        report.pdf_url = signed_url
        report.pdf_generated = True
        await db.commit()

        return {
            "report_id": str(report_id),
            "pdf_url": signed_url,
            "key": key,
        }
