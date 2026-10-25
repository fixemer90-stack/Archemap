# ruff: noqa: RUF001
"""Offline PDF rendering of the same validated Child presentation used on web."""

from __future__ import annotations

import html
from typing import Any

from app.modules.child.presentation import PRESENTATION_CONTRACT_VERSION


def render_child_report_html(presentation: dict[str, Any]) -> str:
    if presentation.get("contract_version") != PRESENTATION_CONTRACT_VERSION:
        raise ValueError("Unsupported Child presentation version")
    metadata = presentation["metadata"]

    def escape(value: object) -> str:
        return html.escape(str(value), quote=True)

    meta = "".join(
        f'<meta name="{name}" content="{escape(value)}">'
        for name, value in {
            "child-core-version": metadata["core_report_version"],
            "child-age-snapshot-id": metadata["age_snapshot_id"],
            "child-age-as-of": metadata["as_of_date"],
            "child-age-guidance-version": metadata.get("age_guidance_version") or "core",
            "child-presentation-version": PRESENTATION_CONTRACT_VERSION,
        }.items()
    )
    age = presentation["age"]
    blocks = []
    for index, section in enumerate(presentation["sections"], 1):
        body = section.get("body")
        prose = "".join(f"<p>{escape(part)}</p>" for part in str(body).split("\n\n")) if body else ""
        actions = "".join(f"<li>{escape(action)}</li>" for action in section.get("actions", []))
        notice = ""
        if not body and section["status"] in {"failed", "pending", "in_progress", "retry_waiting"}:
            notice = '<p class="muted">Развёрнутое пояснение пока недоступно. Сохранённые ориентиры приведены ниже.</p>'
        numerical_age = (
            f"<p>Возраст на дату {escape(age['as_of_date'])}</p>"
            f"<p>{escape(age['age_years'])} лет · {escape(age['age_months'])} мес. · {escape(age['age_days'])} дн.</p>"
            if section["key"] == "current_age"
            else ""
        )
        confidence = f'<p class="muted">{escape(section["confidence_note"])}</p>'
        blocks.append(
            f'<section data-section-key="{escape(section["key"])}">'
            f'<div class="eyebrow">{index:02d}</div><h2>{escape(section["title"])}</h2>'
            f"{numerical_age}{prose}{notice}" + (f"<ul>{actions}</ul>" if actions else "") + confidence + "</section>"
        )
    dated = f"Возрастной блок зафиксирован на {escape(age['as_of_date'])}."
    if age["stale"]:
        dated += " Это сохранённая версия; актуальный возрастной блок можно обновить отдельно от основного отчёта."
    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>Astrotype — контакт с ребёнком</title><meta name="author" content="Astrotype">{meta}
<style>
@page {{ size: A4; margin: 19mm 18mm 20mm; @bottom-center {{ content: counter(page); color:#756e80; font-size:9pt; }} }}
body {{ font: 10.5pt/1.6 "DejaVu Sans",sans-serif; color:#282236; background:white; }}
h1,h2 {{ font-family:"DejaVu Serif",serif; line-height:1.25; color:#3c2a64; }}
h1 {{ font-size:28pt; margin:12mm 0 7mm; }} h2 {{ font-size:17pt; margin:2mm 0 5mm; }}
header {{ border-bottom:2px solid #cdb682; padding-bottom:8mm; margin-bottom:8mm; }}
section {{ margin:8mm 0; }} h2,.eyebrow {{ break-after:avoid; }} p,li {{ widows:3; orphans:3; overflow-wrap:anywhere; }}
.eyebrow {{ font-size:8pt; color:#76658f; letter-spacing:1.5px; }}
.muted,aside {{ color:#625970; }} aside {{ padding:5mm; background:#f6f3fa; border-left:2px solid #8163b1; }}
li {{ margin:2mm 0; }} footer {{ margin-top:8mm; padding-top:4mm; border-top:1px solid #d9d3e1; font-size:9pt; }}
</style></head><body><header><div class="eyebrow">ASTROTYPE · ВЗАИМОДЕЙСТВИЕ</div>
<h1>{escape(presentation["title"])}</h1><p>{escape(presentation["introduction"])}</p></header>
<aside>{dated}</aside>{"".join(blocks)}
<footer>{escape(presentation["technical_basis"]["note"])}</footer></body></html>"""


def render_child_report_pdf(presentation: dict[str, Any]) -> bytes:
    from weasyprint import HTML

    def deny_external_resources(url: str, *args: Any, **kwargs: Any) -> Any:
        raise ValueError("External resources are disabled for Child PDF")

    rendered = HTML(string=render_child_report_html(presentation), url_fetcher=deny_external_resources).write_pdf(
        custom_metadata=True
    )
    if rendered is None:
        raise RuntimeError("Child PDF renderer returned no bytes")
    return bytes(rendered)
