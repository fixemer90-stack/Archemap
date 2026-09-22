# ruff: noqa: E501, RUF001
"""PDF rendering from the same progressive Career report payload used by the web reader."""

from __future__ import annotations

import html
from typing import Any

_DIMENSION_LABELS = {
    "leadership": "Лидерство",
    "analytical_thinking": "Аналитическое мышление",
    "systems_thinking": "Системное мышление",
    "communication": "Коммуникация",
    "creativity": "Творческий подход",
    "structure": "Структура",
    "autonomy": "Самостоятельность",
    "risk_tolerance": "Отношение к риску",
    "people_orientation": "Ориентация на людей",
    "innovation": "Новаторство",
    "long_term_focus": "Долгосрочный фокус",
    "execution": "Реализация",
}
_CATEGORY_LABELS = {
    "strong_match": "выраженное соответствие",
    "possible_match": "возможное соответствие",
    "context_dependent": "зависит от контекста",
}
_CONTEXT_LABELS = {
    "experience:senior": "Опыт: уверенный профессиональный уровень",
    "experience:mid": "Опыт: развивающийся профессиональный уровень",
    "experience:entry": "Опыт: начало профессионального пути",
    "constraints:provided": "Практические ограничения учтены в интерпретации",
    "change_goal:provided": "Цель изменений учтена в интерпретации",
    "current_activity:provided": "Текущая деятельность учтена в интерпретации",
}


def _text(value: object, fallback: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def _paragraphs(value: object) -> str:
    text = _text(value)
    parts = [part.strip() for part in text.split("\n\n") if part.strip()] or ([text] if text else [])
    return "".join(f"<p>{html.escape(part)}</p>" for part in parts)


def render_career_report_html(*, report_payload: dict[str, Any], profile_name: str = "") -> str:
    """Render print HTML without inventing facts beyond the persisted payload."""

    deterministic = report_payload.get("deterministic_payload")
    deterministic = deterministic if isinstance(deterministic, dict) else {}
    sections = report_payload.get("sections")
    sections = sections if isinstance(sections, list) else []
    states = report_payload.get("section_states")
    states = states if isinstance(states, list) else []
    greeting = f"Для {profile_name}" if profile_name else "Ваш профессиональный профиль"

    dimension_cards = []
    for item in deterministic.get("top_dimensions", []):
        if not isinstance(item, dict):
            continue
        key = _text(item.get("dimension"))
        label = _DIMENSION_LABELS.get(key, key.replace("_", " ").capitalize())
        score = item.get("score")
        dimension_cards.append(
            f'<article class="metric"><h3>{html.escape(label)}</h3><strong>{html.escape(str(score))}</strong>'
            "<p>Выраженность рабочей тенденции; число не является оценкой «хорошо» или «плохо».</p></article>"
        )

    narrative_sections = []
    for index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            continue
        narrative_sections.append(
            f'<section class="section"><div class="eyebrow">{index:02d}</div>'
            f"<h2>{html.escape(_text(section.get('title'), 'Раздел'))}</h2>"
            f'<div class="body">{_paragraphs(section.get("body"))}</div></section>'
        )

    failed = any(isinstance(item, dict) and item.get("status") == "failed" for item in states)
    failure_note = (
        '<aside class="notice"><strong>Часть пояснений временно недоступна.</strong> '
        "Базовый расчёт, готовые разделы и профессиональный контекст сохранены.</aside>"
        if failed
        else ""
    )

    contradiction_cards = []
    for item in deterministic.get("contradictions", []):
        if not isinstance(item, dict):
            continue
        contradiction_cards.append(
            "<li><strong>Полезная развилка.</strong> Способность и мотивация могут проявляться по-разному; "
            "проверяйте вывод по реальной роли и уровню ответственности.</li>"
        )

    role_cards = []
    for role in deterministic.get("role_matches", []):
        if not isinstance(role, dict):
            continue
        family = _text(role.get("role_family_key"), "профессиональная роль").replace("_", " ")
        category = _CATEGORY_LABELS.get(_text(role.get("category")), "зависит от контекста")
        raw_examples = role.get("profession_examples")
        examples = raw_examples if isinstance(raw_examples, list) else []
        example_text = ", ".join(str(item) for item in examples)
        role_cards.append(
            f'<article class="role"><h3>{html.escape(family.capitalize())}</h3>'
            f'<p class="badge">{html.escape(category)}</p>'
            + (
                f"<p><strong>Возможный пример, а не назначение:</strong> {html.escape(example_text)}</p>"
                if example_text
                else ""
            )
            + "</article>"
        )

    context_items = []
    for raw in deterministic.get("context_constraints", []):
        context_label = _CONTEXT_LABELS.get(str(raw))
        if context_label:
            context_items.append(f"<li>{html.escape(context_label)}</li>")

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
.metric strong {{ color:#9a6d22; font-size:18pt; }} .metric p,.badge {{ color:#647087; font-size:9.5pt; }}
.section {{ margin:0 0 20px; page-break-inside:avoid; }} .body p {{ margin:0 0 9px; }}
.notice {{ background:#fff6df; border-left:3px solid #bc8a35; margin:14px 0 20px; padding:12px; }}
.basis {{ border-top:1px solid #e5d7b8; margin-top:24px; padding-top:16px; }}
.footer {{ color:#81745c; font-size:9pt; margin-top:24px; }}
</style></head><body>
<header class="cover"><div class="eyebrow">Astrotype Career</div><h1>Профессиональный профиль</h1>
<p class="lead">{html.escape(greeting)}. Отчёт описывает рабочую механику, условия и возможные траектории — не назначает профессию и не гарантирует результат.</p></header>
{failure_note}
<section><div class="eyebrow">Профессиональные акценты</div><h2>Как читать показатели</h2><div class="grid">{"".join(dimension_cards)}</div></section>
{"".join(narrative_sections)}
<section><div class="eyebrow">Контекст</div><h2>Развилки и ограничения</h2><ul>{"".join(contradiction_cards + context_items)}</ul></section>
<section><div class="eyebrow">Возможные направления</div><h2>Семейства ролей</h2><div class="grid">{"".join(role_cards)}</div></section>
<section class="basis"><h2>Основа интерпретации</h2><p>Использованы сохранённые расчёты, ответы и версии правил этого отчёта. Технические идентификаторы скрыты из читательского слоя.</p></section>
<footer class="footer">Astrotype · Career report</footer>
</body></html>"""


def generate_career_report_pdf(*, report_payload: dict[str, Any], profile_name: str = "") -> bytes:
    from weasyprint import HTML

    html_document = render_career_report_html(report_payload=report_payload, profile_name=profile_name)
    rendered = HTML(string=html_document).write_pdf()
    if rendered is None:
        raise RuntimeError("WeasyPrint returned no PDF bytes")
    return bytes(rendered)
