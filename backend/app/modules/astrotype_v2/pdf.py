"""PDF rendering for Astrotype v2 reports."""

from __future__ import annotations

import html
from typing import Any


def _text(value: object, fallback: str = "") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _paragraphs(body: object) -> str:
    text = _text(body)
    parts = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not parts and text:
        parts = [text]
    return "\n".join(f"<p>{html.escape(part)}</p>" for part in parts)


def render_v2_report_html(*, report_payload: dict[str, Any], profile_name: str = "") -> str:
    """Render a self-contained reader-facing HTML document for a natal report PDF."""

    assembled = report_payload.get("assembled_payload") or {}
    narrative = report_payload.get("narrative_payload") or {}
    reader_view = assembled.get("reader_view") if isinstance(assembled, dict) else {}
    hero = reader_view.get("hero") if isinstance(reader_view, dict) else {}
    sections = narrative.get("sections") if isinstance(narrative, dict) else []
    title = _text(hero.get("title") if isinstance(hero, dict) else None, "Натальный портрет личности")
    greeting = f"Здравствуйте, {profile_name}." if profile_name else "Здравствуйте."

    section_html: list[str] = []
    if isinstance(sections, list):
        for index, section in enumerate(sections, start=1):
            if not isinstance(section, dict):
                continue
            display = section.get("reader_display") if isinstance(section.get("reader_display"), dict) else {}
            section_title = _text(section.get("title"), f"Раздел {index}")
            eyebrow = _text(display.get("eyebrow") if isinstance(display, dict) else None, f"{index:02d}")
            subtitle = _text(display.get("subtitle") if isinstance(display, dict) else None)
            body_html = _paragraphs(section.get("body"))
            section_html.append(
                f"""
                <section class="section">
                  <div class="eyebrow">{html.escape(eyebrow)}</div>
                  <h2>{html.escape(section_title)}</h2>
                  {f'<p class="subtitle">{html.escape(subtitle)}</p>' if subtitle else ""}
                  <div class="body">{body_html}</div>
                </section>
                """
            )

    if not section_html:
        section_html.append(
            '<section class="section"><h2>Нарратив готовится</h2>'
            "<p>Базовый расчёт сохранён, нарративные разделы ещё не доступны.</p></section>"
        )

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title)}</title>
  <style>
    @page {{ size: A4; margin: 20mm 17mm; }}
    body {{ font-family: DejaVu Sans, Arial, sans-serif; color: #172033; line-height: 1.55; }}
    .cover {{ border-bottom: 2px solid #d8b45a; margin-bottom: 24px; padding-bottom: 18px; }}
    .eyebrow {{ color: #9f7628; font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }}
    h1 {{ font-size: 30px; margin: 8px 0 10px; }}
    h2 {{ font-size: 21px; margin: 8px 0 6px; page-break-after: avoid; }}
    .intro, .subtitle {{ color: #4d5a73; }}
    .section {{ page-break-inside: avoid; margin: 0 0 22px; }}
    .body p {{ margin: 0 0 10px; }}
    .footer {{ border-top: 1px solid #eadfbf; color: #7a6c4d; font-size: 11px; margin-top: 28px; padding-top: 10px; }}
  </style>
</head>
<body>
  <section class="cover">
    <div class="eyebrow">Astrotype Signature</div>
    <h1>{html.escape(title)}</h1>
    <p class="intro">{html.escape(greeting)} Ваш натальный портрет сохранён в формате PDF.</p>
  </section>
  {"".join(section_html)}
  <footer class="footer">Astrotype · Натальный портрет</footer>
</body>
</html>"""


def generate_v2_report_pdf(*, report_payload: dict[str, Any], profile_name: str = "") -> bytes:
    """Generate PDF bytes for a v2 natal report."""

    from weasyprint import HTML

    html_document = render_v2_report_html(report_payload=report_payload, profile_name=profile_name)
    pdf = HTML(string=html_document).write_pdf()
    if pdf is None:
        raise RuntimeError("WeasyPrint returned no PDF bytes")
    return bytes(pdf)
