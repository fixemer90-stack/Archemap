"""Unit tests for deterministic narrative fallback."""

from __future__ import annotations

from tests.unit.test_report_narratives.test_schemas import make_narrative_input_payload

from app.modules.report_narratives.fallback import build_deterministic_self_fallback
from app.modules.report_narratives.schemas import NarrativeInput


def test_builds_deterministic_fallback_with_explicit_degraded_message() -> None:
    narrative_input = NarrativeInput.model_validate(make_narrative_input_payload())

    fallback = build_deterministic_self_fallback(
        narrative_input,
        reason="LLM narrative temporarily unavailable.",
    )

    assert fallback.title == "Ваш внутренний портрет"
    assert "текстовая версия" in fallback.hero.body.lower()
    assert "недоступ" in fallback.hero.body.lower()
    assert fallback.sections[0].id == "main_formula"
    assert fallback.dominants
    assert fallback.dominants[0].evidence_ids
    assert len(fallback.inner_mechanism.steps) == 3
    assert [section.id for section in fallback.sections] == narrative_input.product_boundaries.allowed_sections
    assert fallback.career_cta.button_label == "Открыть Career"
    assert fallback.final_summary


def test_fallback_reuses_known_evidence_ids_only() -> None:
    narrative_input = NarrativeInput.model_validate(make_narrative_input_payload())

    fallback = build_deterministic_self_fallback(narrative_input)
    known_fact_ids = {
        *[fact.id for fact in narrative_input.key_facts],
        *[fact.id for fact in narrative_input.key_aspects],
    }

    used_fact_ids = {fact_id for note in fallback.hero.evidence_notes for fact_id in note.fact_ids}
    for section in fallback.sections:
        for note in section.evidence_notes:
            used_fact_ids.update(note.fact_ids)

    assert used_fact_ids <= known_fact_ids


def test_fallback_handles_empty_section_sources_without_index_error() -> None:
    payload = make_narrative_input_payload()
    payload["relationship_patterns"] = []
    payload["sexuality_patterns"] = []
    payload["development_recommendations"] = []
    payload["risks"] = []
    narrative_input = NarrativeInput.model_validate(payload)

    fallback = build_deterministic_self_fallback(narrative_input, reason="provider disabled")

    assert fallback.sections
    assert all(isinstance(section.evidence_notes, list) for section in fallback.sections)
