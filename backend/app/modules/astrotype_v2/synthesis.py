"""Deterministic synthesis builders for Astrotype v2 natal facts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.modules.astrotype_v2 import models

SYNTHESIS_CONTRACT_VERSION = "natal_synthesis_v2"

_SECTION_BY_HINT = {
    "placements": "core_pattern",
    "identity": "core_pattern",
    "core": "core_pattern",
    "mind": "perception_and_mind",
    "perception": "perception_and_mind",
    "emotional": "emotional_regulation",
    "emotional_regulation": "emotional_regulation",
    "agency": "agency_and_desire",
    "desire": "agency_and_desire",
    "relationships": "relationships_and_intimacy",
    "relationship": "relationships_and_intimacy",
    "intimacy": "relationships_and_intimacy",
    "growth": "growth_vector",
    "patterns": "growth_vector",
    "balances": "core_pattern",
    "aspects": "core_pattern",
}

_TENSION_POLARITIES = {"tension", "challenge", "conflict", "friction"}
_RESOURCE_POLARITIES = {"resource", "gift", "support", "strength"}
_GROWTH_POLARITIES = {"growth", "development", "vector"}


@dataclass(frozen=True, slots=True)
class SynthesisThemeV2:
    """One deterministic theme derived from one or more persisted natal facts."""

    id: str
    title: str
    summary: str
    primary_section: str
    fact_keys: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    weight: float
    confidence: float
    polarity: str | None = None
    fact_type: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """Return a stable JSON-serializable representation."""

        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "primary_section": self.primary_section,
            "fact_keys": list(self.fact_keys),
            "evidence_ids": list(self.evidence_ids),
            "weight": self.weight,
            "confidence": self.confidence,
            "polarity": self.polarity,
            "fact_type": self.fact_type,
        }


@dataclass(frozen=True, slots=True)
class NatalSynthesisV2:
    """Side-effect-free synthesis contract built before report outlining."""

    chart_id: uuid.UUID
    source_version: str
    dominant_themes: tuple[SynthesisThemeV2, ...]
    tensions: tuple[SynthesisThemeV2, ...] = field(default_factory=tuple)
    resources: tuple[SynthesisThemeV2, ...] = field(default_factory=tuple)
    growth_vectors: tuple[SynthesisThemeV2, ...] = field(default_factory=tuple)
    input_fact_keys: list[str] = field(default_factory=list)
    contract_version: str = SYNTHESIS_CONTRACT_VERSION

    def to_payload(self) -> dict[str, Any]:
        """Return a stable JSON-serializable representation for persistence/debugging."""

        return {
            "contract_version": self.contract_version,
            "chart_id": str(self.chart_id),
            "source_version": self.source_version,
            "input_fact_keys": list(self.input_fact_keys),
            "dominant_themes": [theme.to_payload() for theme in self.dominant_themes],
            "tensions": [theme.to_payload() for theme in self.tensions],
            "resources": [theme.to_payload() for theme in self.resources],
            "growth_vectors": [theme.to_payload() for theme in self.growth_vectors],
        }


def build_natal_synthesis_v2(
    *,
    chart_id: uuid.UUID,
    facts: list[models.NatalFact] | tuple[models.NatalFact, ...],
    source_version: str = "v2.0",
) -> NatalSynthesisV2:
    """Build a deterministic synthesis from persisted natal facts.

    S01 intentionally keeps this builder side-effect-free: callers can persist
    the returned payload in ``models.NatalSynthesis`` after DB orchestration.
    """

    themes = tuple(_theme_from_fact(fact) for fact in sorted(facts, key=_fact_sort_key))
    dominant_themes = tuple(sorted(themes, key=_theme_sort_key))

    tensions = tuple(theme for theme in dominant_themes if (theme.polarity or "").lower() in _TENSION_POLARITIES)
    resources = tuple(theme for theme in dominant_themes if (theme.polarity or "").lower() in _RESOURCE_POLARITIES)
    growth_vectors = tuple(
        theme
        for theme in dominant_themes
        if (theme.polarity or "").lower() in _GROWTH_POLARITIES or theme.primary_section == "growth_vector"
    )

    return NatalSynthesisV2(
        chart_id=chart_id,
        source_version=source_version,
        dominant_themes=dominant_themes,
        tensions=tensions,
        resources=resources,
        growth_vectors=growth_vectors,
        input_fact_keys=sorted(fact.fact_key for fact in facts),
    )


def build_natal_synthesis_row(
    *,
    chart_id: uuid.UUID,
    facts: list[models.NatalFact] | tuple[models.NatalFact, ...],
    facts_version: str,
    source_version: str = "v2.0",
) -> models.NatalSynthesis:
    """Build an ORM row containing the deterministic synthesis payload."""

    synthesis = build_natal_synthesis_v2(chart_id=chart_id, facts=facts, source_version=source_version)
    return models.NatalSynthesis(
        chart_id=chart_id,
        status="ready",
        facts_version=facts_version,
        payload=synthesis.to_payload(),
        source_version=source_version,
    )


def _theme_from_fact(fact: models.NatalFact) -> SynthesisThemeV2:
    section = _section_for_fact(fact)
    evidence_ids = _evidence_ids_from_fact(fact)
    fact_keys = (fact.fact_key,)
    return SynthesisThemeV2(
        id=f"theme:{fact.section_hint or fact.fact_type}:{fact.fact_key}",
        title=fact.title,
        summary=fact.summary,
        primary_section=section,
        fact_keys=fact_keys,
        evidence_ids=evidence_ids,
        weight=round(float(fact.weight), 6),
        confidence=round(float(fact.confidence), 6),
        polarity=fact.polarity,
        fact_type=fact.fact_type,
    )


def _section_for_fact(fact: models.NatalFact) -> str:
    raw_hint = (fact.section_hint or fact.fact_type or "").strip().lower()
    return _SECTION_BY_HINT.get(raw_hint, "core_pattern")


def _evidence_ids_from_fact(fact: models.NatalFact) -> tuple[str, ...]:
    raw_evidence = fact.payload.get("evidence_ids") if isinstance(fact.payload, dict) else None
    if isinstance(raw_evidence, list):
        return tuple(sorted(str(item) for item in raw_evidence))
    if isinstance(raw_evidence, str):
        return (raw_evidence,)
    return (f"fact:{fact.fact_key}",)


def _fact_sort_key(fact: models.NatalFact) -> tuple[str, str, str]:
    return (fact.fact_type, fact.section_hint or "", fact.fact_key)


def _theme_sort_key(theme: SynthesisThemeV2) -> tuple[float, str]:
    return (-theme.weight, theme.id)
