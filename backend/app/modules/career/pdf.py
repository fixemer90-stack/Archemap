# ruff: noqa: E501
"""PDF rendering from the shared Career presentation contract."""

from __future__ import annotations

import html
from typing import Any

from app.modules.career.presentation import build_career_report_presentation


def _text(value: object, fallback: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def _paragraphs(value: object) -> str:
    text = _text(value)
    parts = [part.strip() for part in text.split("\n\n") if part.strip()] or ([text] if text else [])
    return "".join(f"<p>{html.escape(part)}</p>" for part in parts)


def _narrative_block(block: dict[str, Any], index: int) -> str:
    body = _text(block.get("body"))
    status = _text(block.get("status"), "pending")
    if body:
        content = _paragraphs(body)
    elif status == "failed":
        content = '<p class="placeholder">Пояснение не удалось получить. Расчёт и остальные разделы сохранены.</p>'
    else:
        content = '<p class="placeholder">Пояснение готовится. Базовые показатели уже доступны ниже.</p>'
    return (
        f'<section class="section" data-presentation-key="{html.escape(_text(block.get("key")))}">'
        f'<div class="eyebrow">{index:02d}</div><h2>{html.escape(_text(block.get("title"), "Раздел"))}</h2>'
        f'<div class="body">{content}</div></section>'
    )


def _dimension_block(block: dict[str, Any]) -> str:
    cards = []
    for item in block.get("items", []):
        if not isinstance(item, dict):
            continue
        confidence = _text(item.get("confidence_label"))
        cards.append(
            '<article class="metric">'
            f"<h3>{html.escape(_text(item.get('label')))}</h3>"
            f"<strong>{html.escape(str(item.get('score', 0)))}</strong>"
            + (f'<p class="muted">Уверенность: {html.escape(confidence.lower())}.</p>' if confidence else "")
            + "</article>"
        )
    note = _text(block.get("note"))
    return (
        '<section class="evidence" data-presentation-key="dimensions">'
        f'<div class="eyebrow">Практические акценты</div><h2>{html.escape(_text(block.get("title")))}</h2>'
        + (f'<p class="muted">{html.escape(note)}</p>' if note else "")
        + f'<div class="grid">{"".join(cards)}</div></section>'
    )


def _contradiction_block(block: dict[str, Any]) -> str:
    items = []
    for item in block.get("items", []):
        if not isinstance(item, dict):
            continue
        scores = []
        if item.get("capability_score") is not None:
            scores.append(f"способность: {html.escape(str(item['capability_score']))}")
        if item.get("motivation_score") is not None:
            scores.append(f"мотивация: {html.escape(str(item['motivation_score']))}")
        suffix = f' <span class="muted">({"; ".join(scores)})</span>' if scores else ""
        items.append(f"<li>{html.escape(_text(item.get('label')))}{suffix}</li>")
    return (
        '<section class="evidence" data-presentation-key="contradictions">'
        f"<h2>{html.escape(_text(block.get('title')))}</h2><ul>{''.join(items)}</ul></section>"
    )


def _context_block(block: dict[str, Any]) -> str:
    items = "".join(
        f"<li>{html.escape(_text(item.get('label')))}</li>" for item in block.get("items", []) if isinstance(item, dict)
    )
    return (
        '<section class="evidence" data-presentation-key="context">'
        f"<h2>{html.escape(_text(block.get('title')))}</h2><ul>{items}</ul></section>"
    )


def _roles_block(block: dict[str, Any]) -> str:
    cards = []
    for item in block.get("items", []):
        if not isinstance(item, dict):
            continue
        examples = ", ".join(str(value) for value in item.get("examples", []))
        reasons = ", ".join(str(value) for value in item.get("reasons", []))
        cards.append(
            '<article class="role">'
            f"<h3>{html.escape(_text(item.get('title')))}</h3>"
            f'<p class="badge">{html.escape(_text(item.get("category")))}</p>'
            + (
                f"<p><strong>{html.escape(_text(item.get('example_label')))}:</strong> {html.escape(examples)}</p>"
                if examples
                else ""
            )
            + (f'<p class="muted">Основания: {html.escape(reasons)}</p>' if reasons else "")
            + "</article>"
        )
    return (
        '<section class="evidence" data-presentation-key="roles">'
        f'<div class="eyebrow">Возможные направления</div><h2>{html.escape(_text(block.get("title")))}</h2>'
        f'<div class="grid">{"".join(cards)}</div></section>'
    )


def render_career_report_html(*, report_payload: dict[str, Any], profile_name: str = "") -> str:
    """Render A4 HTML from the same semantic manifest consumed by the web reader."""

    manifest = build_career_report_presentation(report_payload)
    greeting = f"Для {profile_name}" if profile_name else "Ваш профессиональный профиль"
    notice = manifest.get("notice")
    notice_html = ""
    if isinstance(notice, dict):
        notice_html = (
            '<aside class="notice">'
            f"<strong>{html.escape(_text(notice.get('title')))}</strong> "
            f"{html.escape(_text(notice.get('body')))}</aside>"
        )

    rendered_blocks: list[str] = []
    narrative_index = 0
    for block in manifest["blocks"]:
        kind = block["kind"]
        if kind == "narrative":
            narrative_index += 1
            rendered_blocks.append(_narrative_block(block, narrative_index))
        elif kind == "dimensions":
            rendered_blocks.append(_dimension_block(block))
        elif kind == "contradictions":
            rendered_blocks.append(_contradiction_block(block))
        elif kind == "context":
            rendered_blocks.append(_context_block(block))
        elif kind == "roles":
            rendered_blocks.append(_roles_block(block))
        elif kind == "technical_basis":
            rendered_blocks.append(
                '<section class="basis" data-presentation-key="technical_basis">'
                f"<h2>{html.escape(_text(block.get('title')))}</h2>"
                f"<p>{html.escape(_text(block.get('body')))}</p></section>"
            )

    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8" /><title>Astrotype Career</title>
<style>
@page {{ size: A4; margin: 18mm 16mm; }}
body {{ color:#20283a; font-family:DejaVu Sans,Arial,sans-serif; font-size:11.5pt; line-height:1.58; }}
.cover {{ border-bottom:2px solid #bc8a35; margin-bottom:22px; padding-bottom:18px; }}
.eyebrow {{ color:#9a6d22; font-size:9pt; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }}
h1 {{ font-size:28pt; line-height:1.1; margin:8px 0; }} h2 {{ font-size:18pt; margin:5px 0 9px; }} h3 {{ margin:0 0 5px; }}
.lead {{ color:#536077; max-width:90%; }} .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
.metric,.role {{ border:1px solid #e5d7b8; border-radius:8px; padding:12px; page-break-inside:avoid; }}
.metric strong {{ color:#9a6d22; font-size:18pt; }} .metric p,.badge,.muted,.placeholder {{ color:#647087; font-size:9.5pt; }}
.section,.evidence {{ margin:0 0 20px; page-break-inside:avoid; }} .body p {{ margin:0 0 9px; }}
.notice {{ background:#fff6df; border-left:3px solid #bc8a35; margin:14px 0 20px; padding:12px; }}
.basis {{ border-top:1px solid #e5d7b8; margin-top:24px; padding-top:16px; }}
.footer {{ color:#81745c; font-size:9pt; margin-top:24px; }}
</style></head><body>
<header class="cover"><div class="eyebrow">Astrotype Career</div><h1>Профессиональный профиль</h1>
<p class="lead">{html.escape(greeting)}. Отчёт описывает рабочую механику, условия и возможные траектории — не назначает профессию и не гарантирует результат.</p></header>
{notice_html}
{"".join(rendered_blocks)}
<footer class="footer">Astrotype · Career report · {html.escape(manifest["contract_version"])}</footer>
</body></html>"""


def generate_career_report_pdf(*, report_payload: dict[str, Any], profile_name: str = "") -> bytes:
    from weasyprint import HTML

    html_document = render_career_report_html(report_payload=report_payload, profile_name=profile_name)
    rendered = HTML(string=html_document).write_pdf()
    if rendered is None:
        raise RuntimeError("WeasyPrint returned no PDF bytes")
    return bytes(rendered)
