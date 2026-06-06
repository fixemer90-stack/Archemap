"""PDF generation for reports using WeasyPrint."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from jinja2 import Environment, FileSystemLoader

logger = structlog.get_logger()

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _fallback_warning(narrative_status: str | None, narrative_error: str | None) -> str | None:
    if narrative_status == "narrative_failed":
        reason = f" Причина: {narrative_error}" if narrative_error else ""
        return f"Текстовая narrative-версия недоступна, поэтому PDF собран из детерминированного отчёта.{reason}"
    if narrative_status and narrative_status != "ready":
        return "Текстовая narrative-версия ещё не готова, поэтому PDF собран из детерминированного отчёта."
    return None


def render_report_html(
    report_data: dict[str, Any],
    profile_name: str = "",
    *,
    narrative_content: dict[str, Any] | None = None,
    narrative_status: str | None = None,
    narrative_error: str | None = None,
) -> str:
    """Render report data into HTML using Jinja2 template."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("report.html")

    has_ready_narrative = bool(narrative_content) and narrative_status == "ready"
    html = template.render(
        report=report_data,
        technical_report=report_data,
        profile_name=profile_name,
        product=report_data.get("product", "self"),
        archetype=report_data.get("archetype", {}),
        claims=report_data.get("claims", []),
        chart=report_data.get("chart", {}),
        quality_warning=report_data.get("quality_warning"),
        provenance=report_data.get("provenance", {}),
        narrative=narrative_content if has_ready_narrative else None,
        narrative_status=narrative_status,
        narrative_error=narrative_error,
        fallback_warning=_fallback_warning(narrative_status, narrative_error),
    )
    return html


def generate_pdf(html: str) -> bytes:
    """Convert HTML to PDF using WeasyPrint."""
    from weasyprint import HTML

    logger.info("pdf_generation_start")
    pdf: bytes = HTML(string=html).write_pdf()
    logger.info("pdf_generation_success", size=len(pdf))
    return pdf


def generate_report_pdf(
    report_data: dict[str, Any],
    profile_name: str = "",
    *,
    narrative_content: dict[str, Any] | None = None,
    narrative_status: str | None = None,
    narrative_error: str | None = None,
) -> bytes:
    """Generate PDF from deterministic report data and optional saved narrative."""
    html = render_report_html(
        report_data,
        profile_name,
        narrative_content=narrative_content,
        narrative_status=narrative_status,
        narrative_error=narrative_error,
    )
    return generate_pdf(html)
