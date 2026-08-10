"""Deterministic outline planning for Astrotype v2 natal reports."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.synthesis import NatalSynthesisV2, SynthesisThemeV2

OUTLINE_CONTRACT_VERSION = "report_outline_v2"
DEBUG_OUTLINE_CONTRACT_VERSION = "report_outline_debug_v2"

SECTION_ORDER = [
    "core_pattern",
    "perception_and_mind",
    "emotional_regulation",
    "agency_and_desire",
    "relationships_and_intimacy",
    "growth_vector",
]

_SECTION_META = {
    "core_pattern": ("Ядро личности", "Explain the central personality pattern and dominant chart logic."),
    "perception_and_mind": ("Мышление и восприятие", "Explain mental style, attention and interpretation filters."),
    "emotional_regulation": ("Эмоциональная регуляция", "Explain emotional rhythm, sensitivity and inner regulation."),
    "agency_and_desire": ("Воля и действие", "Explain action style, desire, initiative and embodiment."),
    "relationships_and_intimacy": ("Близость и отношения", "Explain attachment, closeness and relational dynamics."),
    "growth_vector": ("Вектор роста", "Explain development tasks, integration and mature expression."),
}

_REFERENCE_NEIGHBORS = {
    "core_pattern": ("perception_and_mind", "emotional_regulation"),
    "perception_and_mind": ("core_pattern", "agency_and_desire"),
    "emotional_regulation": ("core_pattern", "relationships_and_intimacy"),
    "agency_and_desire": ("perception_and_mind", "growth_vector"),
    "relationships_and_intimacy": ("emotional_regulation", "growth_vector"),
    "growth_vector": ("agency_and_desire", "relationships_and_intimacy"),
}


@dataclass(frozen=True, slots=True)
class ThemeClusterV2:
    """Scored group of themes owned by one report section."""

    section_id: str
    theme_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    score: float

    def to_payload(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "theme_ids": list(self.theme_ids),
            "evidence_ids": list(self.evidence_ids),
            "score": self.score,
        }


@dataclass(frozen=True, slots=True)
class SectionPlanV2:
    """Theme ownership contract for one report section."""

    id: str
    title: str
    purpose: str
    owned_theme_ids: list[str]
    reference_theme_ids: list[str]
    forbidden_theme_ids: list[str]
    evidence_ids: list[str]

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "purpose": self.purpose,
            "owned_theme_ids": list(self.owned_theme_ids),
            "reference_theme_ids": list(self.reference_theme_ids),
            "forbidden_theme_ids": list(self.forbidden_theme_ids),
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True, slots=True)
class ReportOutlineV2:
    """Deterministic anti-duplication outline for v2 section generation."""

    chart_id: uuid.UUID
    source_version: str
    sections: tuple[SectionPlanV2, ...]
    theme_clusters: tuple[ThemeClusterV2, ...]
    section_keys: list[str]
    global_narrative_arc: str
    contract_version: str = OUTLINE_CONTRACT_VERSION

    def to_payload(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "chart_id": str(self.chart_id),
            "source_version": self.source_version,
            "section_keys": list(self.section_keys),
            "global_narrative_arc": self.global_narrative_arc,
            "theme_clusters": [cluster.to_payload() for cluster in self.theme_clusters],
            "sections": [section.to_payload() for section in self.sections],
        }


def score_theme_clusters(synthesis: NatalSynthesisV2) -> tuple[ThemeClusterV2, ...]:
    """Group synthesized themes by owning section and score each group deterministically."""

    clusters: list[ThemeClusterV2] = []
    for section_id in SECTION_ORDER:
        themes = tuple(theme for theme in synthesis.dominant_themes if theme.primary_section == section_id)
        theme_ids = tuple(theme.id for theme in sorted(themes, key=_theme_rank_key))
        evidence_ids = tuple(sorted({evidence_id for theme in themes for evidence_id in theme.evidence_ids}))
        score = round(sum(theme.weight for theme in themes), 6)
        clusters.append(
            ThemeClusterV2(
                section_id=section_id,
                theme_ids=theme_ids,
                evidence_ids=evidence_ids,
                score=score,
            )
        )
    return tuple(clusters)


def build_report_outline_v2(*, synthesis: NatalSynthesisV2, source_version: str = "v2.0") -> ReportOutlineV2:
    """Build ownership/reference/forbidden section plans from deterministic synthesis."""

    clusters = score_theme_clusters(synthesis)
    themes_by_id = {theme.id: theme for theme in synthesis.dominant_themes}
    themes_by_section = _themes_by_section(synthesis.dominant_themes)
    all_theme_ids = sorted(themes_by_id)

    sections: list[SectionPlanV2] = []
    for section_id in SECTION_ORDER:
        owned_theme_ids = [theme.id for theme in sorted(themes_by_section.get(section_id, ()), key=_theme_rank_key)]
        reference_theme_ids = _reference_theme_ids(section_id, themes_by_section)
        forbidden_theme_ids = [
            theme_id for theme_id in all_theme_ids if theme_id not in set(owned_theme_ids) | set(reference_theme_ids)
        ]
        evidence_ids = sorted(
            {evidence_id for theme_id in owned_theme_ids for evidence_id in themes_by_id[theme_id].evidence_ids}
        )
        title, purpose = _SECTION_META[section_id]
        sections.append(
            SectionPlanV2(
                id=section_id,
                title=title,
                purpose=purpose,
                owned_theme_ids=owned_theme_ids,
                reference_theme_ids=reference_theme_ids,
                forbidden_theme_ids=forbidden_theme_ids,
                evidence_ids=evidence_ids,
            )
        )

    return ReportOutlineV2(
        chart_id=synthesis.chart_id,
        source_version=source_version,
        sections=tuple(sections),
        theme_clusters=clusters,
        section_keys=list(SECTION_ORDER),
        global_narrative_arc=_global_narrative_arc(synthesis),
    )


def build_report_outline_row(*, synthesis: NatalSynthesisV2, source_version: str = "v2.0") -> models.ReportOutline:
    """Build an ORM row containing the deterministic outline payload."""

    outline = build_report_outline_v2(synthesis=synthesis, source_version=source_version)
    return models.ReportOutline(
        chart_id=synthesis.chart_id,
        status="ready",
        outline=outline.to_payload(),
        section_keys=outline.section_keys,
        source_version=source_version,
    )


def render_debug_outline_payload(*, outline: ReportOutlineV2, synthesis: NatalSynthesisV2) -> dict[str, Any]:
    """Render deterministic outline inspection data without text generation fields."""

    themes_by_id = {theme.id: theme for theme in synthesis.dominant_themes}
    return {
        "contract_version": DEBUG_OUTLINE_CONTRACT_VERSION,
        "chart_id": str(outline.chart_id),
        "source_version": outline.source_version,
        "sections": [
            {
                "id": section.id,
                "title": section.title,
                "owned_themes": [_debug_theme_payload(themes_by_id[theme_id]) for theme_id in section.owned_theme_ids],
                "reference_theme_ids": list(section.reference_theme_ids),
                "forbidden_theme_ids": list(section.forbidden_theme_ids),
                "evidence_ids": list(section.evidence_ids),
            }
            for section in outline.sections
        ],
    }


def _themes_by_section(themes: tuple[SynthesisThemeV2, ...]) -> dict[str, tuple[SynthesisThemeV2, ...]]:
    grouped: dict[str, list[SynthesisThemeV2]] = {section_id: [] for section_id in SECTION_ORDER}
    for theme in themes:
        grouped.setdefault(theme.primary_section, []).append(theme)
    return {
        section_id: tuple(sorted(section_themes, key=_theme_rank_key)) for section_id, section_themes in grouped.items()
    }


def _reference_theme_ids(section_id: str, themes_by_section: dict[str, tuple[SynthesisThemeV2, ...]]) -> list[str]:
    references: list[str] = []
    for neighbor_section_id in _REFERENCE_NEIGHBORS[section_id]:
        neighbor_themes = themes_by_section.get(neighbor_section_id, ())
        if neighbor_themes:
            references.append(neighbor_themes[0].id)
    return sorted(references)


def _global_narrative_arc(synthesis: NatalSynthesisV2) -> str:
    if not synthesis.dominant_themes:
        return "No deterministic themes available."
    top_titles = ", ".join(theme.title for theme in tuple(sorted(synthesis.dominant_themes, key=_theme_rank_key))[:3])
    return f"Deterministic arc from strongest natal themes: {top_titles}."


def _debug_theme_payload(theme: SynthesisThemeV2) -> dict[str, Any]:
    return {
        "id": theme.id,
        "title": theme.title,
        "summary": theme.summary,
        "fact_keys": list(theme.fact_keys),
        "evidence_ids": list(theme.evidence_ids),
        "weight": theme.weight,
        "confidence": theme.confidence,
    }


def _theme_rank_key(theme: SynthesisThemeV2) -> tuple[float, str]:
    return (-theme.weight, theme.id)
