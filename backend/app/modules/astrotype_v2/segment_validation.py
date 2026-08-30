# ruff: noqa: RUF001
"""Validate Astrotype v2 LLM report segment outputs."""

from __future__ import annotations

import re

from app.modules.astrotype_v2.schemas import ReportSegmentOutputV2, SectionRenderInputV2


class SegmentValidationError(ValueError):
    """Raised when one v2 segment response violates the section contract."""


def validate_segment_output_v2(
    *,
    output: ReportSegmentOutputV2,
    section_input: SectionRenderInputV2,
) -> ReportSegmentOutputV2:
    """Validate one typed segment output against its curated section input."""

    if output.section_id != section_input.section_id:
        raise SegmentValidationError("section_id mismatch")

    allowed_evidence_ids = set(section_input.evidence_ids) | {
        evidence_id for theme in section_input.reference_themes for evidence_id in theme.evidence_ids
    }
    output_evidence_ids = set(output.evidence_ids)
    if not output_evidence_ids:
        raise SegmentValidationError("missing evidence ids")
    unknown_evidence_ids = output_evidence_ids - allowed_evidence_ids
    if unknown_evidence_ids:
        raise SegmentValidationError(f"unknown evidence ids: {sorted(unknown_evidence_ids)}")

    missing_evidence_ids = set(section_input.evidence_ids) - output_evidence_ids
    if missing_evidence_ids:
        raise SegmentValidationError(f"missing owned evidence ids: {sorted(missing_evidence_ids)}")

    owned_theme_ids = {theme.id for theme in section_input.owned_themes}
    forbidden_theme_ids = set(section_input.forbidden_theme_ids)
    covered_theme_ids = set(output.covered_theme_ids)
    expanded_forbidden = covered_theme_ids & forbidden_theme_ids
    if expanded_forbidden:
        raise SegmentValidationError(f"forbidden theme expansion: {sorted(expanded_forbidden)}")

    missing_owned = owned_theme_ids - covered_theme_ids
    if missing_owned:
        raise SegmentValidationError(f"missing owned theme coverage: {sorted(missing_owned)}")

    if _contains_excluded_terms(output.body):
        raise SegmentValidationError("excluded typology leakage")

    if _contains_raw_fact_dump(output.body):
        raise SegmentValidationError("raw fact dump segment body")

    if _contains_generic_filler(output.body):
        raise SegmentValidationError("generic filler segment body")

    if not output.continuation_complete:
        if not output.continuation_cursor:
            raise SegmentValidationError("continuation cursor required")
        if _is_technically_empty(output.body):
            raise SegmentValidationError("underdeveloped segment body")
        return output

    _validate_product_depth(body=output.body, section_id=section_input.section_id)
    _validate_required_depth_moves(output.body)
    return output


def section_depth_floor(section_id: str) -> tuple[int, int]:
    """Return minimum complete-section word and paragraph counts."""

    if section_id == "core_pattern":
        return 450, 4
    return 300, 3


def _paragraphs(body: str) -> list[str]:
    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n", body) if paragraph.strip()]


def _word_count(body: str) -> int:
    return len(re.findall(r"[\wЁёА-Яа-я-]+", body, flags=re.UNICODE))


def _is_technically_empty(body: str) -> bool:
    return len(_paragraphs(body)) < 3 or _word_count(body) < 80


def _validate_product_depth(*, body: str, section_id: str) -> None:
    min_words, min_paragraphs = section_depth_floor(section_id)
    paragraphs = _paragraphs(body)
    words = _word_count(body)
    if len(paragraphs) < min_paragraphs or words < min_words:
        raise SegmentValidationError(
            f"underdeveloped segment body: expected at least {min_words} words and {min_paragraphs} paragraphs"
        )


def _validate_required_depth_moves(body: str) -> None:
    lowered = body.lower()
    required_groups = {
        "mechanism": ("механизм", "внутренн", "психологическ"),
        "lived manifestation": (
            "проявля",
            "жизн",
            "повседнев",
            "на практике",
            "в поведени",
            "в отношени",
            "в конкретн",
            "реальн",
        ),
        "tension": ("напряж", "конфликт", "поляр", "противореч"),
        "protection shadow": ("защит", "тень", "под давлением", "компенсац"),
        "mature expression": ("зрел",),
    }
    missing = [label for label, markers in required_groups.items() if not any(marker in lowered for marker in markers)]
    if missing:
        raise SegmentValidationError(f"missing depth moves: {missing}")


def _contains_raw_fact_dump(body: str) -> bool:
    lowered = body.lower()
    technical_hits = sum(
        1
        for pattern in (
            r"\b(is in|with orb|orb of|house\s+\d+)\b",
            r"\b(sun|moon|mercury|venus|mars|jupiter|saturn)\s+(in|conjunct|square|opposition|trine|sextile)\b",
            r"\b\d+(?:\.\d+)?°\b",
            r"\baspect\b",
        )
        if re.search(pattern, lowered)
    )
    label_hits = len(re.findall(r"\b(?:sun|moon|mercury|venus|mars|jupiter|saturn|house|orb|aspect)\b", lowered))
    return technical_hits >= 2 or label_hits >= 10


def _contains_generic_filler(body: str) -> bool:
    lowered = body.lower()
    generic_phrases = (
        "уникальная энергия",
        "раскрыть свой потенциал",
        "вселенная помогает",
        "важно найти баланс",
        "следуйте своему сердцу",
        "this placement makes you",
        "you are a very special person",
    )
    return sum(1 for phrase in generic_phrases if phrase in lowered) >= 2


def _contains_excluded_terms(body: str) -> bool:
    lowered = body.lower()
    return any(fragment in lowered for fragment in ("socionics", "model a", "function strengths", "archetype"))
