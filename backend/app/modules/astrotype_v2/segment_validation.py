"""Validate Astrotype v2 LLM report segment outputs."""

from __future__ import annotations

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
    unknown_evidence_ids = set(output.evidence_ids) - allowed_evidence_ids
    if unknown_evidence_ids:
        raise SegmentValidationError(f"unknown evidence ids: {sorted(unknown_evidence_ids)}")

    owned_theme_ids = {theme.id for theme in section_input.owned_themes}
    forbidden_theme_ids = set(section_input.forbidden_theme_ids)
    covered_theme_ids = set(output.covered_theme_ids)
    expanded_forbidden = covered_theme_ids & forbidden_theme_ids
    if expanded_forbidden:
        raise SegmentValidationError(f"forbidden theme expansion: {sorted(expanded_forbidden)}")

    missing_owned = owned_theme_ids - covered_theme_ids
    if missing_owned:
        raise SegmentValidationError(f"missing owned theme coverage: {sorted(missing_owned)}")

    if _is_underdeveloped(output.body):
        raise SegmentValidationError("underdeveloped segment body")

    if _contains_excluded_terms(output.body):
        raise SegmentValidationError("excluded typology leakage")

    return output


def _is_underdeveloped(body: str) -> bool:
    paragraphs = [paragraph.strip() for paragraph in body.split("\n\n") if paragraph.strip()]
    word_count = len(body.split())
    return len(paragraphs) < 3 or word_count < 35


def _contains_excluded_terms(body: str) -> bool:
    lowered = body.lower()
    return any(fragment in lowered for fragment in ("socionics", "model a", "function strengths", "archetype"))
