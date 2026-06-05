"""Report PDF and narrative generation tasks."""

from __future__ import annotations

from typing import Any

from app.config import settings
from workers.celery_app import app


@app.task(  # type: ignore[untyped-decorator]
    name="reports.generate_pdf",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=120,
    time_limit=180,
)
def generate_pdf(self: Any, report_id: str, user_id: str, profile_name: str = "") -> dict[str, Any]:
    """Generate PDF for a report and upload to S3."""
    from app.modules.reports.tasks import generate_pdf_task

    try:
        return generate_pdf_task(report_id, user_id, profile_name)
    except Exception as exc:
        raise self.retry(exc=exc) from exc


@app.task(  # type: ignore[untyped-decorator]
    name="reports.generate_report_narrative",
    bind=True,
    max_retries=settings.LLM_MAX_RETRIES,
    default_retry_delay=30,
    soft_time_limit=max(settings.LLM_TIMEOUT_SECONDS + 30, 60),
    time_limit=max(settings.LLM_TIMEOUT_SECONDS + 60, 90),
)
def generate_report_narrative(self: Any, report_id: str, force: bool = False) -> dict[str, Any]:
    """Generate structured narrative for a deterministic report."""
    from app.modules.report_narratives.tasks import (
        finalize_narrative_task_failure,
        generate_report_narrative_task,
        should_retry_narrative_task_error,
    )

    try:
        return generate_report_narrative_task(report_id, force=force)
    except Exception as exc:
        retries = int(getattr(self.request, "retries", 0))
        if should_retry_narrative_task_error(exc) and retries < settings.LLM_MAX_RETRIES:
            raise self.retry(exc=exc) from exc
        finalize_narrative_task_failure(report_id, str(exc))
        raise
