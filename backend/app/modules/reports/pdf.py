"""PDF generation for reports using WeasyPrint."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from jinja2 import Environment, FileSystemLoader

logger = structlog.get_logger()

TEMPLATES_DIR = Path(__file__).parent / "templates"


def render_report_html(
    report_data: dict[str, Any],
    profile_name: str = "",
) -> str:
    """Render report data into HTML using Jinja2 template."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("report.html")

    html = template.render(
        report=report_data,
        profile_name=profile_name,
        product=report_data.get("product", "self"),
        archetype=report_data.get("archetype", {}),
        claims=report_data.get("claims", []),
        chart=report_data.get("chart", {}),
        quality_warning=report_data.get("quality_warning"),
        provenance=report_data.get("provenance", {}),
    )
    return html


def generate_pdf(html: str) -> bytes:
    """Convert HTML to PDF using WeasyPrint."""
    from weasyprint import HTML

    logger.info("pdf_generation_start")
    pdf = HTML(string=html).write_pdf()
    logger.info("pdf_generation_success", size=len(pdf))
    return pdf


def generate_report_pdf(
    report_data: dict[str, Any],
    profile_name: str = "",
) -> bytes:
    """Generate PDF from report data."""
    html = render_report_html(report_data, profile_name)
    return generate_pdf(html)
