# ruff: noqa: RUF001
"""Renderer-neutral presentation contract for persisted Career report payloads."""

from __future__ import annotations

from typing import Any

from app.modules.career.narrative import CAREER_SECTION_ORDER

PRESENTATION_CONTRACT_VERSION = "career_report_presentation_v1"

_SECTION_TITLES = {
    "professional_summary": "Ваш профессиональный профиль",
    "work_style": "Как вы работаете",
    "strengths": "Сильные стороны",
    "decision_making": "Стиль принятия решений",
    "leadership_and_influence": "Лидерство и влияние",
    "optimal_environment": "Оптимальная рабочая среда",
    "risk_environment": "Что может снижать эффективность",
    "career_archetypes": "Профессиональные архетипы",
    "role_families": "Подходящие типы ролей",
    "career_paths": "Возможные карьерные траектории",
}
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
    "strong_match": "Выраженное соответствие",
    "possible_match": "Возможное соответствие",
    "context_dependent": "Зависит от контекста",
}
_CONTEXT_LABELS = {
    "experience:senior": "Опыт: уверенный профессиональный уровень",
    "experience:mid": "Опыт: развивающийся профессиональный уровень",
    "experience:entry": "Опыт: начало профессионального пути",
    "current_activity:provided": "Текущая деятельность учтена",
    "change_goal:provided": "Цель изменений учтена",
    "constraints:provided": "Практические ограничения учтены",
}
_CONTRADICTION_LABELS = {
    "leadership_without_people_management": (
        "Способность вести за собой может не совпадать с желанием управлять людьми."
    ),
}
_DIMENSION_EXPLANATION = "Выраженность рабочей тенденции; число не является оценкой «хорошо» или «плохо»."
_TECHNICAL_BASIS = (
    "Отчёт собран из сохранённых расчётов, ответов и версий правил. "
    "Технический слой нужен для проверяемости и не заменяет профессиональную консультацию или реальный опыт."
)


def _text(value: object, fallback: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def _records(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _humanize(value: str) -> str:
    return value.replace("_", " ").replace(":", ": ").capitalize()


def _number(value: object) -> int | float | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, (int, float)) else None


def _notice(report_status: str) -> dict[str, str] | None:
    if report_status == "narrative_failed":
        return {
            "kind": "narrative_failed",
            "title": "Часть пояснений временно недоступна.",
            "body": "Базовый профиль, показатели и уже готовые разделы остаются доступными.",
        }
    if report_status in {
        "deterministic_ready",
        "generating_sections",
        "narrative_pending",
        "generating",
        "pending",
    }:
        return {
            "kind": "deterministic_ready",
            "title": "Пояснения ещё готовятся.",
            "body": "Базовый профиль и показатели уже доступны; десять разделов будут заполняться по мере готовности.",
        }
    return None


def build_career_report_presentation(report_payload: dict[str, Any]) -> dict[str, Any]:
    """Derive the semantic web/PDF contract from one persisted read payload."""

    deterministic_value = report_payload.get("deterministic_payload")
    deterministic = deterministic_value if isinstance(deterministic_value, dict) else {}
    sections_by_key = {_text(item.get("section_key")): item for item in _records(report_payload.get("sections"))}
    states_by_key = {_text(item.get("section_key")): item for item in _records(report_payload.get("section_states"))}

    blocks: list[dict[str, Any]] = []
    for key in CAREER_SECTION_ORDER:
        section = sections_by_key.get(key)
        state = states_by_key.get(key)
        body = _text(section.get("body")) if section else ""
        source_status = _text(state.get("status")) if state else ""
        status = "ready" if body else (source_status if source_status in {"failed", "pending"} else "pending")
        blocks.append(
            {
                "kind": "narrative",
                "key": key,
                "title": _text(section.get("title"), _SECTION_TITLES[key]) if section else _SECTION_TITLES[key],
                "status": status,
                "body": body or None,
            }
        )

    dimension_items = []
    for item in _records(deterministic.get("top_dimensions")):
        key = _text(item.get("dimension"))
        confidence = _number(item.get("confidence"))
        dimension_items.append(
            {
                "key": key,
                "label": _DIMENSION_LABELS.get(key, _humanize(key)),
                "score": _number(item.get("score")) or 0,
                "confidence": confidence,
                "confidence_label": (
                    "Основания согласованы"
                    if confidence is not None and confidence >= 0.75
                    else "Лучше проверить на опыте"
                ),
                "explanation": _DIMENSION_EXPLANATION,
            }
        )
    blocks.append(
        {
            "kind": "dimensions",
            "key": "dimensions",
            "title": "Выраженные рабочие тенденции",
            "items": dimension_items,
        }
    )

    contradiction_items = []
    for item in _records(deterministic.get("contradictions")):
        code = _text(item.get("code"), "contextual_tension")
        contradiction_items.append(
            {
                "key": code,
                "label": _CONTRADICTION_LABELS.get(
                    code,
                    "Способность и мотивация могут проявляться по-разному; проверьте вывод в контексте реальной роли.",
                ),
                "fact_key": _text(item.get("fact_key")),
                "capability_score": _number(item.get("capability_score")),
                "motivation_score": _number(item.get("motivation_score")),
            }
        )
    blocks.append(
        {
            "kind": "contradictions",
            "key": "contradictions",
            "title": "Полезные развилки",
            "items": contradiction_items,
        }
    )

    blocks.append(
        {
            "kind": "context",
            "key": "context",
            "title": "Учтённый контекст",
            "items": [
                {"key": key, "label": _CONTEXT_LABELS.get(key, _humanize(key))}
                for key in _strings(deterministic.get("context_constraints"))
            ],
        }
    )

    role_items = []
    for item in _records(deterministic.get("role_matches")):
        key = _text(item.get("role_family_key"), "context_dependent")
        role_items.append(
            {
                "key": key,
                "title": _humanize(key),
                "category": _CATEGORY_LABELS.get(_text(item.get("category")), "Зависит от контекста"),
                "reasons": [_humanize(reason) for reason in _strings(item.get("reasons"))],
                "examples": _strings(item.get("profession_examples")),
                "example_label": "Возможный пример, а не назначение",
            }
        )
    blocks.append(
        {
            "kind": "roles",
            "key": "roles",
            "title": "Семейства ролей",
            "items": role_items,
        }
    )
    blocks.append(
        {
            "kind": "technical_basis",
            "key": "technical_basis",
            "title": "Основа интерпретации",
            "body": _TECHNICAL_BASIS,
        }
    )

    report_status = _text(report_payload.get("status"), "pending")
    return {
        "contract_version": PRESENTATION_CONTRACT_VERSION,
        "report_status": report_status,
        "notice": _notice(report_status),
        "blocks": blocks,
    }
