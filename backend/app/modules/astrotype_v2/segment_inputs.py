"""Build curated per-section render inputs for Astrotype v2 LLM segments."""

from __future__ import annotations

from app.modules.astrotype_v2.outline import ReportOutlineV2, SectionPlanV2
from app.modules.astrotype_v2.schemas import SectionRenderInputV2, SectionThemeInputV2
from app.modules.astrotype_v2.synthesis import NatalSynthesisV2, SynthesisThemeV2


def build_section_render_inputs_v2(
    *, outline: ReportOutlineV2, synthesis: NatalSynthesisV2
) -> list[SectionRenderInputV2]:
    """Create one restricted render input for every upper report section."""

    themes_by_id = {theme.id: theme for theme in synthesis.dominant_themes}
    return [
        _build_section_input(section=section, outline=outline, synthesis=synthesis, themes_by_id=themes_by_id)
        for section in outline.sections
    ]


def _build_section_input(
    *,
    section: SectionPlanV2,
    outline: ReportOutlineV2,
    synthesis: NatalSynthesisV2,
    themes_by_id: dict[str, SynthesisThemeV2],
) -> SectionRenderInputV2:
    owned_themes = [_theme_input(themes_by_id[theme_id]) for theme_id in section.owned_theme_ids]
    reference_themes = [_theme_input(themes_by_id[theme_id]) for theme_id in section.reference_theme_ids]
    return SectionRenderInputV2(
        chart_id=outline.chart_id,
        source_version=outline.source_version,
        section_id=section.id,
        section_title=section.title,
        section_purpose=section.purpose,
        owned_themes=owned_themes,
        reference_themes=reference_themes,
        forbidden_theme_ids=list(section.forbidden_theme_ids),
        evidence_ids=sorted(section.evidence_ids),
        already_explained={
            "owned_theme_ids": list(section.owned_theme_ids),
            "global_narrative_arc": outline.global_narrative_arc,
            "input_fact_keys_hash_source": list(synthesis.input_fact_keys),
        },
        style_contract=_style_contract(),
        depth_contract=_depth_contract(),
        continuation_policy=_continuation_policy(section.id),
    )


def _theme_input(theme: SynthesisThemeV2) -> SectionThemeInputV2:
    return SectionThemeInputV2(
        id=theme.id,
        title=theme.title,
        summary=theme.summary,
        fact_keys=list(theme.fact_keys),
        evidence_ids=list(theme.evidence_ids),
        weight=theme.weight,
        confidence=theme.confidence,
        polarity=theme.polarity,
        fact_type=theme.fact_type,
        psychological_mechanism=theme.psychological_mechanism,
        lived_manifestation=theme.lived_manifestation,
        inner_tension=theme.inner_tension,
        protective_strategy=theme.protective_strategy,
        immature_expression=theme.immature_expression,
        mature_expression=theme.mature_expression,
        integration_question=theme.integration_question,
        evidence_strength=theme.evidence_strength,
        contradictions=list(theme.contradictions),
        compensations=list(theme.compensations),
    )


def _style_contract() -> dict[str, object]:
    return {
        "language": "ru",
        "tone": "dense, specific, human, non-fatalistic",
        "format": "structured JSON only; no markdown",
        "boundaries": [
            "write only the requested upper personality section",
            "do not render deterministic lower calculation tables or infographic data",
            "do not mention excluded typology systems, labels or function taxonomies",
        ],
    }


def _depth_contract() -> dict[str, object]:
    return {
        "mode": "expanded_section",
        "coverage": "cover every owned theme and evidence id with developed prose",
        "technical_emptiness_floor": {"paragraphs": 3, "words": 80},
        "section_targets": {
            "core_pattern": {"words": "700-1200", "paragraphs": "6-9"},
            "other_upper_sections": {"words": "450-900", "paragraphs": "4-7"},
        },
        "required_moves": [
            "central formula",
            "psychological mechanism",
            "lived manifestation",
            "inner tension or polarity",
            "protective or shadow strategy",
            "mature integrated expression",
            "soft self-check or integration cue",
        ],
        "quality": [
            "write a deep psychological reading of one section, not a broad overview",
            "explain the inner mechanism, not a generic horoscope claim",
            "do not structure prose as a placement or aspect summary",
            "use reference themes only for continuity and do not expand forbidden themes",
            "preserve long valid prose when it is grounded and coherent",
        ],
    }


def _continuation_policy(section_id: str) -> dict[str, object]:
    return {
        "continuation_supported": True,
        "retry_scope": "section_only",
        "section_id": section_id,
        "if_cut": "persist completed part and continue the same section without adding new facts",
    }
