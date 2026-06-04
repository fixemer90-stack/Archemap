# ruff: noqa: RUF001
"""Deterministic validators for structured self narratives."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from app.modules.report_narratives.exceptions import (
    NarrativeRecoveryAction,
    NarrativeValidationError,
)
from app.modules.report_narratives.schemas import (
    EvidenceBackedClaim,
    EvidenceNote,
    NarrativeInput,
    SelfNarrative,
)

_ALLOWED_PLANET_TOKENS = {
    "солнце",
    "луна",
    "меркурий",
    "венера",
    "марс",
    "юпитер",
    "сатурн",
    "уран",
    "нептун",
    "плутон",
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
}
_ALLOWED_SIGN_TOKENS = {
    "овне",
    "тельце",
    "близнецах",
    "раке",
    "льве",
    "деве",
    "весах",
    "скорпионе",
    "стрельце",
    "козероге",
    "водолее",
    "рыбах",
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
}
_ALLOWED_ASPECT_TOKENS = {
    "соединение",
    "оппозиция",
    "тригон",
    "квадрат",
    "секстиль",
    "квинконс",
    "conjunction",
    "opposition",
    "trine",
    "square",
    "sextile",
    "quincunx",
}
_CAREER_MARKERS = (
    "професси",
    "карьерн",
    "деньг",
    "доход",
    "зарплат",
    "финансов",
    "вакан",
    "резюме",
    "собесед",
    "управлен",
    "менедж",
    "должност",
)
_FORBIDDEN_LANGUAGE_MARKERS = (
    "диагноз",
    "болезн",
    "расстройств",
    "депресси",
    "психопат",
    "шизофр",
    "неизбеж",
    "обреч",
    "сужден",
    "предначертан",
    "гарантир",
    "половому акту",
    "половой акт",
    "проникнов",
    "эякуляц",
    "генитал",
    "оргазм",
)
_SECTION_ID_PATTERN = re.compile(r"\b([1-9]|1[0-2])\s+доме?\b", re.IGNORECASE)
_SOCTYPE_PATTERN = re.compile(r"\b[ЕЛСИ]{3}\b|\b[A-Z]{3}\b")


def validate_self_narrative(
    narrative: SelfNarrative | dict[str, Any],
    narrative_input: NarrativeInput | dict[str, Any],
) -> list[NarrativeValidationError]:
    """Validate structured Self narrative against deterministic input."""
    validated_input = NarrativeInput.model_validate(narrative_input)
    candidate = narrative if isinstance(narrative, SelfNarrative) else SelfNarrative.model_construct(**narrative)

    errors: list[NarrativeValidationError] = []
    errors.extend(_validate_required_sections(candidate, validated_input))
    errors.extend(_validate_career_cta(candidate))
    errors.extend(_validate_evidence_refs(candidate, validated_input))
    errors.extend(_validate_career_boundaries(candidate))
    errors.extend(_validate_forbidden_language(candidate))
    errors.extend(_validate_domain_terms(candidate, validated_input))
    return errors


def choose_narrative_recovery_action(
    errors: list[NarrativeValidationError],
    repair_attempts_used: int,
    llm_available: bool,
) -> NarrativeRecoveryAction:
    """Apply the MVP repair/fallback policy for invalid narrative output."""
    if not llm_available:
        return "fallback"
    if not errors:
        return "repair"
    if all(error.recoverable for error in errors) and repair_attempts_used < 1:
        return "repair"
    if all(error.recoverable for error in errors):
        return "fallback"
    return "narrative_failed"


def _validate_required_sections(
    narrative: SelfNarrative,
    narrative_input: NarrativeInput,
) -> list[NarrativeValidationError]:
    actual_ids = [section.id for section in getattr(narrative, "sections", []) or []]
    expected_ids = list(narrative_input.product_boundaries.allowed_sections)
    if actual_ids == expected_ids:
        return []
    return [
        NarrativeValidationError(
            code="invalid_section_order",
            message="Narrative sections must match the required Self section set and order.",
            location="sections",
            recoverable=True,
        )
    ]


def _validate_career_cta(narrative: SelfNarrative) -> list[NarrativeValidationError]:
    career_cta = getattr(narrative, "career_cta", None)
    if career_cta is not None:
        return []
    return [
        NarrativeValidationError(
            code="missing_career_cta",
            message="Self narrative must include career_cta.",
            location="career_cta",
            recoverable=True,
        )
    ]


def _validate_evidence_refs(
    narrative: SelfNarrative,
    narrative_input: NarrativeInput,
) -> list[NarrativeValidationError]:
    allowed_fact_ids = _allowed_fact_ids(narrative_input)
    errors: list[NarrativeValidationError] = []
    for location, note in _iter_evidence_notes(narrative):
        unknown_fact_ids = [fact_id for fact_id in note.fact_ids if fact_id not in allowed_fact_ids]
        if unknown_fact_ids:
            errors.append(
                NarrativeValidationError(
                    code="unknown_evidence_ref",
                    message=f"Narrative references unknown fact ids: {', '.join(unknown_fact_ids)}.",
                    location=location,
                    recoverable=True,
                )
            )
    return errors


def _validate_career_boundaries(narrative: SelfNarrative) -> list[NarrativeValidationError]:
    errors: list[NarrativeValidationError] = []
    for location, text in _iter_non_cta_texts(narrative):
        lowered = text.lower()
        if any(marker in lowered for marker in _CAREER_MARKERS):
            errors.append(
                NarrativeValidationError(
                    code="career_boundary_violation",
                    message="Self narrative contains career deep-dive language outside career_cta.",
                    location=location,
                    recoverable=False,
                )
            )
    return errors


def _validate_forbidden_language(narrative: SelfNarrative) -> list[NarrativeValidationError]:
    errors: list[NarrativeValidationError] = []
    for location, text in _iter_all_texts(narrative):
        lowered = text.lower()
        if any(marker in lowered for marker in _FORBIDDEN_LANGUAGE_MARKERS):
            errors.append(
                NarrativeValidationError(
                    code="forbidden_language",
                    message="Narrative contains forbidden fatalistic, medical, diagnostic, or graphic language.",
                    location=location,
                    recoverable=False,
                )
            )
    return errors


def _validate_domain_terms(
    narrative: SelfNarrative,
    narrative_input: NarrativeInput,
) -> list[NarrativeValidationError]:
    allowed_terms = _allowed_domain_terms(narrative_input)
    errors: list[NarrativeValidationError] = []

    for location, text in _iter_non_cta_texts(narrative):
        lowered = text.lower()
        unsupported_tokens = [token for token in _tokens_from_text(lowered) if token not in allowed_terms]
        unsupported_houses = [house for house in _SECTION_ID_PATTERN.findall(lowered) if house not in allowed_terms]
        unsupported_types = [
            soc_type for soc_type in _SOCTYPE_PATTERN.findall(text) if soc_type.lower() not in allowed_terms
        ]
        unknown = unsupported_tokens + unsupported_houses + unsupported_types
        if unknown:
            errors.append(
                NarrativeValidationError(
                    code="unsupported_domain_term",
                    message=f"Narrative introduces unsupported domain terms: {', '.join(sorted(set(unknown)))}.",
                    location=location,
                    recoverable=True,
                )
            )
    return errors


def _allowed_fact_ids(narrative_input: NarrativeInput) -> set[str]:
    allowed = {fact.id for fact in narrative_input.key_facts}
    allowed.update(fact.id for fact in narrative_input.key_aspects)
    for claim in _iter_claim_groups(narrative_input):
        allowed.update(claim.evidence_ids)
    return allowed


def _allowed_domain_terms(narrative_input: NarrativeInput) -> set[str]:
    allowed: set[str] = set()
    for item in narrative_input.key_facts:
        allowed.update(_tokens_from_text(item.label.lower()))
        allowed.update(_extract_house_terms(item.label))
    for aspect in narrative_input.key_aspects:
        allowed.update(_tokens_from_text(aspect.label.lower()))
        allowed.update(_extract_house_terms(aspect.label))
    allowed.add(narrative_input.socionics.type.lower())
    allowed.add(narrative_input.socionics.type_ru.lower())
    return allowed


def _extract_house_terms(item_label: str) -> set[str]:
    return set(_SECTION_ID_PATTERN.findall(item_label.lower()))


def _iter_claim_groups(narrative_input: NarrativeInput) -> Iterable[EvidenceBackedClaim]:
    for group_name in (
        "strengths",
        "risks",
        "relationship_patterns",
        "sexuality_patterns",
        "development_recommendations",
    ):
        yield from getattr(narrative_input, group_name)


def _iter_evidence_notes(narrative: SelfNarrative) -> Iterable[tuple[str, EvidenceNote]]:
    for index, note in enumerate(narrative.hero.evidence_notes):
        yield (f"hero.evidence_notes[{index}]", note)
    for section_index, section in enumerate(narrative.sections):
        for note_index, note in enumerate(section.evidence_notes):
            yield (f"sections[{section_index}].evidence_notes[{note_index}]", note)


def _iter_non_cta_texts(narrative: SelfNarrative) -> Iterable[tuple[str, str]]:
    yield ("title", narrative.title)
    yield ("hero.title", narrative.hero.title)
    yield ("hero.body", narrative.hero.body)
    yield ("final_summary", narrative.final_summary)
    for section_index, section in enumerate(narrative.sections):
        yield (f"sections[{section_index}].title", section.title)
        yield (f"sections[{section_index}].body", section.body)
        for bullet_index, bullet in enumerate(section.bullets):
            yield (f"sections[{section_index}].bullets[{bullet_index}]", bullet)
        for note_index, note in enumerate(section.evidence_notes):
            yield (f"sections[{section_index}].evidence_notes[{note_index}].claim", note.claim)


def _iter_all_texts(narrative: SelfNarrative) -> Iterable[tuple[str, str]]:
    yield from _iter_non_cta_texts(narrative)
    for bullet_index, bullet in enumerate(narrative.hero.bullets):
        yield (f"hero.bullets[{bullet_index}]", bullet)
    for note_index, note in enumerate(narrative.hero.evidence_notes):
        yield (f"hero.evidence_notes[{note_index}].claim", note.claim)
    career_cta = getattr(narrative, "career_cta", None)
    if career_cta is None:
        return
    yield ("career_cta.title", career_cta.title)
    yield ("career_cta.body", career_cta.body)
    yield ("career_cta.button_label", career_cta.button_label)
    for bullet_index, bullet in enumerate(career_cta.bullets):
        yield (f"career_cta.bullets[{bullet_index}]", bullet)


def _tokens_from_text(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-zA-Zа-яА-ЯёЁ]+", text.lower()))
    return {
        token
        for token in tokens
        if token in _ALLOWED_PLANET_TOKENS or token in _ALLOWED_SIGN_TOKENS or token in _ALLOWED_ASPECT_TOKENS
    }
