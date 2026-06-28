"""Deterministic post-processing for LLM self narratives before validation."""

from __future__ import annotations

import re
from typing import Any

from app.modules.report_narratives.schemas import NarrativeInput, SelfNarrative

_SECTION_TITLES: dict[str, str] = {
    "main_formula": "Главная формула",
    "world_perception": "Как вы воспринимаете мир",
    "emotions_and_communication": "Эмоции и общение",
    "strengths": "Сильные стороны",
    "vulnerabilities": "Уязвимости",
    "relationships": "Отношения и близость",
    "sexuality": "Сексуальность",
    "development": "Направление развития",
}

_FORBIDDEN_TEXT_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"полов(?:ому|ой)?\s+акту", "сексуальной близости"),
    (r"половой\s+акт", "сексуальная близость"),
    (r"проникнов\w*", "сексуальная близость"),
    (r"эякуляц\w*", "разрядка"),
    (r"генитал\w*", "телесная близость"),
    (r"оргазм\w*", "кульминация близости"),
    (r"диагноз\w*", "ярлык"),
    (r"психопат\w*", "жёсткий тип поведения"),
    (r"шизофр\w*", "крайняя дезорганизация"),
    (r"неизбеж\w*", "часто ощущается очень сильным"),
    (r"обреч\w*", "может восприниматься как тяжёлый сценарий"),
    (r"сужден\w*", "часто складывается"),
    (r"предначертан\w*", "как будто заранее задан"),
    (r"гарантир\w*", "может заметно усиливать"),
)


def harden_self_narrative(candidate: SelfNarrative, narrative_input: NarrativeInput) -> SelfNarrative:
    """Repair common model drift deterministically before validator checks."""
    data = candidate.model_dump(mode="json")
    allowed_fact_ids = _allowed_fact_ids(narrative_input)
    fallback_fact_ids = _default_fact_ids(narrative_input)

    _sanitize_texts_in_place(data)
    _repair_evidence_ids_in_place(data, narrative_input, allowed_fact_ids, fallback_fact_ids)
    data["sections"] = _normalize_sections(
        data.get("sections", []),
        narrative_input,
        allowed_fact_ids,
        fallback_fact_ids,
    )
    return SelfNarrative.model_validate(data)


def _normalize_sections(
    sections: list[dict[str, Any]],
    narrative_input: NarrativeInput,
    allowed_fact_ids: set[str],
    fallback_fact_ids: list[str],
) -> list[dict[str, Any]]:
    by_id = {section.get("id"): section for section in sections if isinstance(section, dict) and section.get("id")}
    normalized: list[dict[str, Any]] = []
    for section_id in narrative_input.product_boundaries.allowed_sections:
        section = by_id.get(section_id)
        if section is None:
            normalized.append(_build_missing_section(section_id, narrative_input, fallback_fact_ids))
            continue
        body = str(section.get("body") or "").strip()
        bullets = [str(bullet).strip() for bullet in section.get("bullets", []) if str(bullet).strip()]
        if not body:
            body = _build_missing_section(section_id, narrative_input, fallback_fact_ids)["body"]
        normalized_notes = []
        for note in section.get("evidence_notes", []):
            if not isinstance(note, dict):
                continue
            fact_ids = _sanitize_fact_ids(note.get("fact_ids", []), allowed_fact_ids, fallback_fact_ids)
            limitation_fact_ids = _sanitize_fact_ids(
                note.get("limitation_fact_ids", []),
                allowed_fact_ids,
                [],
            )
            normalized_notes.append(
                {
                    "claim": str(note.get("claim") or "").strip() or body,
                    "fact_ids": fact_ids,
                    "interpretation": note.get("interpretation"),
                    "limitation": note.get("limitation"),
                    "limitation_fact_ids": limitation_fact_ids,
                }
            )
        normalized.append(
            {
                "id": section_id,
                "title": str(section.get("title") or _SECTION_TITLES[section_id]),
                "body": body,
                "bullets": bullets,
                "evidence_notes": normalized_notes,
            }
        )
    return normalized


def _build_missing_section(
    section_id: str,
    narrative_input: NarrativeInput,
    fallback_fact_ids: list[str],
) -> dict[str, Any]:
    body, bullets = _section_content(section_id, narrative_input)
    if not body:
        body = (
            f"Этот раздел опирается на устойчивый паттерн «{_SECTION_TITLES[section_id].lower()}», "
            "который стоит уточнять через ваш lived experience."
        )
    return {
        "id": section_id,
        "title": _SECTION_TITLES[section_id],
        "body": body,
        "bullets": bullets,
        "evidence_notes": [
            {
                "claim": body,
                "fact_ids": list(fallback_fact_ids),
                "limitation_fact_ids": [],
            }
        ]
        if fallback_fact_ids
        else [],
    }


def _section_content(section_id: str, narrative_input: NarrativeInput) -> tuple[str, list[str]]:
    if section_id == "main_formula":
        bullets = [dominant.title for dominant in narrative_input.dominants[:2]]
        body_parts = [narrative_input.inner_mechanism.summary, narrative_input.dominants[0].body]
        return " ".join(part for part in body_parts if part), bullets
    if section_id == "world_perception":
        bullets = [fact.label for fact in narrative_input.key_facts[:2]]
        body_parts = [fact.meaning for fact in narrative_input.key_facts[:2]]
        return " ".join(part for part in body_parts if part), bullets
    if section_id == "emotions_and_communication":
        bullets = [aspect.label for aspect in narrative_input.key_aspects[:2]]
        body_parts = [aspect.meaning for aspect in narrative_input.key_aspects[:2]]
        return " ".join(part for part in body_parts if part), bullets
    if section_id == "strengths":
        claims = [item.claim for item in narrative_input.strengths]
        return " ".join(claims[:2]), claims
    if section_id == "vulnerabilities":
        claims = [item.claim for item in narrative_input.risks]
        return " ".join(claims[:2]), claims
    if section_id == "relationships":
        claims = [item.claim for item in narrative_input.relationship_patterns]
        return " ".join(claims[:2]), claims
    if section_id == "sexuality":
        claims = [item.claim for item in narrative_input.sexuality_patterns]
        return " ".join(claims[:2]), claims
    if section_id == "development":
        claims = [item.claim for item in narrative_input.development_recommendations]
        return " ".join(claims[:2]), claims
    return "", []


def _repair_evidence_ids_in_place(
    data: dict[str, Any],
    narrative_input: NarrativeInput,
    allowed_fact_ids: set[str],
    fallback_fact_ids: list[str],
) -> None:
    for index, item in enumerate(data.get("dominants", [])):
        source_dominant = narrative_input.dominants[index] if index < len(narrative_input.dominants) else None
        item["evidence_ids"] = _sanitize_fact_ids(
            item.get("evidence_ids", []),
            allowed_fact_ids,
            list(getattr(source_dominant, "evidence_ids", []) or fallback_fact_ids),
        )
    inner_mechanism = data.get("inner_mechanism") or {}
    for index, step in enumerate(inner_mechanism.get("steps", [])):
        source_step = (
            narrative_input.inner_mechanism.steps[index] if index < len(narrative_input.inner_mechanism.steps) else None
        )
        step["evidence_ids"] = _sanitize_fact_ids(
            step.get("evidence_ids", []),
            allowed_fact_ids,
            list(getattr(source_step, "evidence_ids", []) or fallback_fact_ids),
        )
    for index, item in enumerate(data.get("house_scenarios", [])):
        source_scenario = (
            narrative_input.house_scenarios[index] if index < len(narrative_input.house_scenarios) else None
        )
        item["evidence_ids"] = _sanitize_fact_ids(
            item.get("evidence_ids", []),
            allowed_fact_ids,
            list(getattr(source_scenario, "evidence_ids", []) or fallback_fact_ids),
        )
        _repair_note_list(item.get("evidence_notes", []), allowed_fact_ids, item["evidence_ids"])
    for index, item in enumerate(data.get("calibration_questions", [])):
        source_question = (
            narrative_input.calibration_questions[index] if index < len(narrative_input.calibration_questions) else None
        )
        item["evidence_ids"] = _sanitize_fact_ids(
            item.get("evidence_ids", []),
            allowed_fact_ids,
            list(getattr(source_question, "evidence_ids", []) or fallback_fact_ids),
        )
        question = str(item.get("question") or "").strip()
        if question and not question.endswith("?"):
            item["question"] = question.rstrip(".!") + "?"
    for index, item in enumerate(data.get("contradictions", [])):
        source_contradiction = (
            narrative_input.contradictions[index] if index < len(narrative_input.contradictions) else None
        )
        item["evidence_ids"] = _sanitize_fact_ids(
            item.get("evidence_ids", []),
            allowed_fact_ids,
            list(getattr(source_contradiction, "evidence_ids", []) or fallback_fact_ids),
        )
        _repair_note_list(item.get("evidence_notes", []), allowed_fact_ids, item["evidence_ids"])
    for index, item in enumerate(data.get("failure_modes", [])):
        source_failure_mode = (
            narrative_input.failure_modes[index] if index < len(narrative_input.failure_modes) else None
        )
        item["evidence_ids"] = _sanitize_fact_ids(
            item.get("evidence_ids", []),
            allowed_fact_ids,
            list(getattr(source_failure_mode, "evidence_ids", []) or fallback_fact_ids),
        )
        _repair_note_list(item.get("evidence_notes", []), allowed_fact_ids, item["evidence_ids"])
    maturity_levels = data.get("maturity_levels") or {}
    source_levels = narrative_input.maturity_levels
    for band_name in ("low", "medium", "high"):
        band = maturity_levels.get(band_name)
        if not isinstance(band, dict):
            continue
        source_band = getattr(source_levels, band_name)
        band["evidence_ids"] = _sanitize_fact_ids(
            band.get("evidence_ids", []),
            allowed_fact_ids,
            list(getattr(source_band, "evidence_ids", []) or fallback_fact_ids),
        )
        _repair_note_list(band.get("evidence_notes", []), allowed_fact_ids, band["evidence_ids"])
    hero = data.get("hero") or {}
    _repair_note_list(hero.get("evidence_notes", []), allowed_fact_ids, fallback_fact_ids)


def _repair_note_list(notes: list[dict[str, Any]], allowed_fact_ids: set[str], fallback_fact_ids: list[str]) -> None:
    for note in notes:
        if not isinstance(note, dict):
            continue
        note["fact_ids"] = _sanitize_fact_ids(note.get("fact_ids", []), allowed_fact_ids, fallback_fact_ids)
        note["limitation_fact_ids"] = _sanitize_fact_ids(
            note.get("limitation_fact_ids", []),
            allowed_fact_ids,
            [],
        )


def _sanitize_fact_ids(values: list[Any], allowed_fact_ids: set[str], fallback_fact_ids: list[str]) -> list[str]:
    cleaned = [str(value) for value in values if str(value) in allowed_fact_ids]
    if cleaned:
        return cleaned
    deduped_fallback: list[str] = []
    for value in fallback_fact_ids:
        text = str(value)
        if text in allowed_fact_ids and text not in deduped_fallback:
            deduped_fallback.append(text)
    return deduped_fallback


def _allowed_fact_ids(narrative_input: NarrativeInput) -> set[str]:
    allowed = {fact.id for fact in narrative_input.key_facts}
    allowed.update(fact.id for fact in narrative_input.key_aspects)
    for dominant in narrative_input.dominants:
        allowed.update(dominant.evidence_ids)
    for step in narrative_input.inner_mechanism.steps:
        allowed.update(step.evidence_ids)
    for scenario in narrative_input.house_scenarios:
        allowed.update(scenario.evidence_ids)
        for note in scenario.evidence_notes:
            allowed.update(note.fact_ids)
            allowed.update(note.limitation_fact_ids)
    for question in narrative_input.calibration_questions:
        allowed.update(question.evidence_ids)
    for contradiction in narrative_input.contradictions:
        allowed.update(contradiction.evidence_ids)
        for note in contradiction.evidence_notes:
            allowed.update(note.fact_ids)
            allowed.update(note.limitation_fact_ids)
    for failure_mode in narrative_input.failure_modes:
        allowed.update(failure_mode.evidence_ids)
        for note in failure_mode.evidence_notes:
            allowed.update(note.fact_ids)
            allowed.update(note.limitation_fact_ids)
    for band_name in ("low", "medium", "high"):
        band = getattr(narrative_input.maturity_levels, band_name)
        allowed.update(band.evidence_ids)
        for note in band.evidence_notes:
            allowed.update(note.fact_ids)
            allowed.update(note.limitation_fact_ids)
    for group_name in (
        "strengths",
        "risks",
        "relationship_patterns",
        "sexuality_patterns",
        "development_recommendations",
    ):
        for claim in getattr(narrative_input, group_name):
            allowed.update(claim.evidence_ids)
    return allowed


def _default_fact_ids(narrative_input: NarrativeInput) -> list[str]:
    candidates = [
        *[fact.id for fact in narrative_input.key_facts[:2]],
        *[fact.id for fact in narrative_input.key_aspects[:2]],
    ]
    seen: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.append(candidate)
    return seen


def _sanitize_texts_in_place(node: Any) -> None:
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if isinstance(value, str):
                node[key] = _sanitize_text(value)
            else:
                _sanitize_texts_in_place(value)
        return
    if isinstance(node, list):
        for index, value in enumerate(node):
            if isinstance(value, str):
                node[index] = _sanitize_text(value)
            else:
                _sanitize_texts_in_place(value)


def _sanitize_text(value: str) -> str:
    sanitized = value
    for pattern, replacement in _FORBIDDEN_TEXT_REPLACEMENTS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", sanitized).strip()
