# ruff: noqa: RUF001
"""Deterministic fallback narrative for Self reports."""

from __future__ import annotations

from app.modules.report_narratives.schemas import (
    CareerCTA,
    EvidenceBackedClaim,
    EvidenceNote,
    HeroSection,
    NarrativeInput,
    NarrativeSection,
    SelfNarrative,
)

_SECTION_TITLES = {
    "main_formula": "Главная формула личности",
    "world_perception": "Как вы воспринимаете мир",
    "emotions_and_communication": "Эмоции и коммуникация",
    "strengths": "Сильные стороны",
    "vulnerabilities": "Уязвимости",
    "relationships": "Отношения",
    "sexuality": "Близость и сексуальность",
    "development": "Вектор развития",
}


def build_deterministic_self_fallback(
    narrative_input: NarrativeInput,
    reason: str | None = None,
) -> SelfNarrative:
    """Build a deterministic degraded-mode narrative without any LLM call."""
    fallback_reason = reason or "Текстовая версия временно недоступна."
    hero_note = _claim_to_note(narrative_input.strengths[0] if narrative_input.strengths else None)

    sections = [
        NarrativeSection(
            id=section_id,
            title=_SECTION_TITLES[section_id],
            body=_section_body(section_id, narrative_input),
            bullets=_section_bullets(section_id, narrative_input),
            evidence_notes=_section_notes(section_id, narrative_input),
        )
        for section_id in narrative_input.product_boundaries.allowed_sections
    ]

    return SelfNarrative(
        title="Ваш внутренний портрет",
        hero=HeroSection(
            id="hero",
            title="Краткое резюме",
            body=(
                f"Сейчас текстовая версия недоступна, поэтому ниже показано краткое "
                f"детерминированное резюме. {fallback_reason}"
            ),
            bullets=[
                narrative_input.calculation_quality.quality_label,
                f"Соционика: {narrative_input.socionics.type_ru}",
                f"Архетип: {narrative_input.archetype.primary}",
            ],
            evidence_notes=[hero_note] if hero_note is not None else [],
        ),
        sections=sections,
        career_cta=CareerCTA(
            title="Отдельный отчёт Career",
            body=(
                "Если захотите отдельно разобрать профессиональную роль, деньги, "
                "среду и стратегию роста, лучше открыть специальный Career-отчёт."
            ),
            bullets=["Профроли", "среда", "стратегия роста"],
            button_label="Открыть Career",
        ),
        final_summary=(
            "Это резервная детерминированная версия: факты сохранены, а расширенный "
            "связный narrative можно сгенерировать повторно позже."
        ),
    )


def _section_body(section_id: str, narrative_input: NarrativeInput) -> str:
    if section_id == "main_formula":
        return (
            f"В центре вашего профиля — сочетание архетипа «{narrative_input.archetype.primary}» "
            f"и соционического акцента {narrative_input.socionics.type_ru}."
        )
    if section_id == "world_perception":
        return _claim_or_default(
            narrative_input.strengths,
            "Ваш способ воспринимать мир будет уточнён в полной текстовой версии.",
        )
    if section_id == "emotions_and_communication":
        return _claim_or_default(
            narrative_input.risks,
            "Эмоционально-коммуникационный паттерн сохранён в детерминированных фактах и будет развёрнут позже.",
        )
    if section_id == "strengths":
        return _claim_or_default(
            narrative_input.strengths,
            "Ваши сильные стороны зафиксированы в evidence-backed claims.",
        )
    if section_id == "vulnerabilities":
        return _claim_or_default(
            narrative_input.risks,
            "Зоны перегрузки описаны кратко и без лишних обобщений.",
        )
    if section_id == "relationships":
        return _claim_or_default(
            narrative_input.relationship_patterns,
            "Паттерны отношений будут развёрнуты в полной narrative-версии.",
        )
    if section_id == "sexuality":
        return _claim_or_default(
            narrative_input.sexuality_patterns,
            "Блок близости и сексуальности сохранён в безопасной краткой форме.",
        )
    return _claim_or_default(
        narrative_input.development_recommendations,
        "Рекомендации развития будут уточнены после повторной генерации narrative-слоя.",
    )


def _section_bullets(section_id: str, narrative_input: NarrativeInput) -> list[str]:
    source_map = {
        "main_formula": narrative_input.strengths,
        "world_perception": narrative_input.strengths,
        "emotions_and_communication": narrative_input.risks,
        "strengths": narrative_input.strengths,
        "vulnerabilities": narrative_input.risks,
        "relationships": narrative_input.relationship_patterns,
        "sexuality": narrative_input.sexuality_patterns,
        "development": narrative_input.development_recommendations,
    }
    return [claim.claim for claim in source_map.get(section_id, [])[:2]]


def _section_notes(section_id: str, narrative_input: NarrativeInput) -> list[EvidenceNote]:
    source_map = {
        "main_formula": narrative_input.strengths,
        "world_perception": narrative_input.strengths,
        "emotions_and_communication": narrative_input.risks,
        "strengths": narrative_input.strengths,
        "vulnerabilities": narrative_input.risks,
        "relationships": narrative_input.relationship_patterns,
        "sexuality": narrative_input.sexuality_patterns,
        "development": narrative_input.development_recommendations,
    }
    claim = source_map.get(section_id, [None])[0]
    note = _claim_to_note(claim)
    return [note] if note is not None else []


def _claim_to_note(claim: EvidenceBackedClaim | None) -> EvidenceNote | None:
    if claim is None:
        return None
    return EvidenceNote(claim=claim.claim, fact_ids=list(claim.evidence_ids))


def _claim_or_default(claims: list[EvidenceBackedClaim], default: str) -> str:
    if not claims:
        return default
    return claims[0].claim
