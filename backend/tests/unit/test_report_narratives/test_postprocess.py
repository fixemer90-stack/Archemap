# ruff: noqa: RUF001
"""Unit tests for deterministic self narrative hardening."""

from __future__ import annotations

from tests.unit.test_report_narratives.test_schemas import make_narrative_input_payload

from app.modules.report_narratives.fallback import build_deterministic_self_fallback
from app.modules.report_narratives.postprocess import harden_self_narrative
from app.modules.report_narratives.schemas import NarrativeInput
from app.modules.report_narratives.validators import validate_self_narrative


def make_narrative_input() -> NarrativeInput:
    return NarrativeInput.model_validate(make_narrative_input_payload())


def test_hardening_restores_missing_sections_and_valid_order() -> None:
    narrative_input = make_narrative_input()
    candidate = build_deterministic_self_fallback(narrative_input)
    candidate.sections = candidate.sections[:6]

    hardened = harden_self_narrative(candidate, narrative_input)

    assert [section.id for section in hardened.sections] == list(narrative_input.product_boundaries.allowed_sections)
    assert hardened.sections[-2].id == "sexuality"
    assert hardened.sections[-2].body
    assert hardened.sections[-1].id == "development"
    assert hardened.sections[-1].body
    assert validate_self_narrative(hardened, narrative_input) == []


def test_hardening_replaces_unknown_evidence_refs_with_allowed_ids() -> None:
    narrative_input = make_narrative_input()
    candidate = build_deterministic_self_fallback(narrative_input)
    candidate.calibration_questions[0].evidence_ids = ["unknown_fact"]
    candidate.contradictions[0].evidence_ids = ["unknown_contradiction"]
    candidate.hero.evidence_notes[0].fact_ids = ["unknown_note"]

    hardened = harden_self_narrative(candidate, narrative_input)

    allowed = {fact.id for fact in narrative_input.key_facts} | {fact.id for fact in narrative_input.key_aspects}
    assert set(hardened.calibration_questions[0].evidence_ids) <= allowed | set(
        narrative_input.calibration_questions[0].evidence_ids
    )
    assert set(hardened.contradictions[0].evidence_ids) <= allowed | set(narrative_input.contradictions[0].evidence_ids)
    fallback_fact_ids = {fact.id for fact in narrative_input.key_facts[:2]} | {
        fact.id for fact in narrative_input.key_aspects[:2]
    }
    assert set(hardened.hero.evidence_notes[0].fact_ids) <= allowed | fallback_fact_ids
    assert validate_self_narrative(hardened, narrative_input) == []


def test_hardening_sanitizes_forbidden_language() -> None:
    narrative_input = make_narrative_input()
    candidate = build_deterministic_self_fallback(narrative_input)
    candidate.sections[0].body = "Этот текст звучит как диагноз и обречённость."
    candidate.sections[1].bullets = ["Такой сценарий кажется неизбежным."]

    hardened = harden_self_narrative(candidate, narrative_input)

    assert "диагноз" not in hardened.sections[0].body.lower()
    assert "обреч" not in hardened.sections[0].body.lower()
    assert "неизбеж" not in hardened.sections[1].bullets[0].lower()
    assert validate_self_narrative(hardened, narrative_input) == []


def test_hardening_converts_informal_second_person_without_truncating_text() -> None:
    narrative_input = make_narrative_input()
    candidate = build_deterministic_self_fallback(narrative_input)
    marker = "маркер-сохранённого-длинного-текста"
    long_text = " ".join(["ты видишь свой ритм и тебе важно не терять себя"] * 140)
    candidate.sections[0].body = f"{long_text} {marker}."

    hardened = harden_self_narrative(candidate, narrative_input)

    lowered = hardened.sections[0].body.lower()
    assert marker in lowered
    assert len(hardened.sections[0].body) > 4000
    assert " ты " not in f" {lowered} "
    assert " тебе " not in f" {lowered} "
    assert " свой " not in f" {lowered} "
    assert validate_self_narrative(hardened, narrative_input) == []


def test_hardening_preserves_paragraph_breaks_in_visible_prose() -> None:
    narrative_input = make_narrative_input()
    candidate = build_deterministic_self_fallback(narrative_input)
    candidate.hero.body = "Первый абзац с обращением к вам.\n\nВторой абзац сохраняет ритм чтения."
    candidate.sections[0].body = "Первый смысловой блок.\n\nВторой смысловой блок."

    hardened = harden_self_narrative(candidate, narrative_input)

    assert "Первый абзац с обращением" in hardened.hero.body
    assert "\n\nВторой абзац сохраняет" in hardened.hero.body
    assert "Первый смысловой блок.\n\nВторой смысловой блок." in hardened.sections[0].body
