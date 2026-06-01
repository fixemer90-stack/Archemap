"""Report PDF generation tasks."""

from __future__ import annotations

from workers.celery_app import app


@app.task(
    name="reports.generate_pdf",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=120,
    time_limit=180,
)
def generate_pdf(self, report_id: str, user_id: str, profile_name: str = "") -> dict:
    """Generate PDF for a report and upload to S3."""
    from app.modules.reports.tasks import generate_pdf_task

    try:
        return generate_pdf_task(report_id, user_id, profile_name)
    except Exception as exc:
        self.retry(exc=exc)
