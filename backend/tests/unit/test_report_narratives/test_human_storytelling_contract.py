# ruff: noqa: RUF001
"""RED tests for E15 S01 human storytelling contract."""

from __future__ import annotations

from app.modules.report_narratives.human_storytelling import (
    HUMAN_STORYTELLING_CHAIN,
    HUMAN_STORYTELLING_CONTRACT_VERSION,
    HUMAN_TONE_BANNED_PATTERNS,
    HUMAN_TONE_BEFORE_AFTER_EXAMPLES,
    HUMAN_TONE_GUIDE,
    validate_human_storytelling_text,
)


def test_human_storytelling_contract_is_versioned_and_recognition_first() -> None:
    assert HUMAN_STORYTELLING_CONTRACT_VERSION == "self_human_storytelling_v1"
    assert HUMAN_STORYTELLING_CHAIN == (
        "recognition",
        "personal_formula",
        "lived_scene",
        "inner_tension",
        "protective_strategy",
        "mature_expression",
        "soft_question",
    )
    assert "recognition-first" in HUMAN_TONE_GUIDE.hero_rule
    assert "raw placements" in HUMAN_TONE_GUIDE.hero_rule
    assert "evidence remains source of truth" in HUMAN_TONE_GUIDE.evidence_rule
    assert "progressively disclosed" in HUMAN_TONE_GUIDE.evidence_rule


def test_human_tone_guide_names_banned_dry_and_generic_patterns() -> None:
    banned_codes = {pattern.code for pattern in HUMAN_TONE_BANNED_PATTERNS}

    assert {
        "bureaucratic_abstraction",
        "generic_astrology_prose",
        "unsupported_therapy_language",
        "technical_first_hero",
    } <= banned_codes

    bureaucratic = next(pattern for pattern in HUMAN_TONE_BANNED_PATTERNS if pattern.code == "bureaucratic_abstraction")
    assert "формирует паттерн" in bureaucratic.markers
    assert "эмоциональная обработка" in bureaucratic.markers
    assert "конкретное жизненное проявление" in bureaucratic.rewrite_hint


def test_human_tone_guide_has_before_after_examples_for_key_sections() -> None:
    assert len(HUMAN_TONE_BEFORE_AFTER_EXAMPLES) >= 5
    section_ids = {example.section_id for example in HUMAN_TONE_BEFORE_AFTER_EXAMPLES}
    assert {"hero", "main_formula", "emotions_and_communication", "relationships", "development"} <= section_ids

    for example in HUMAN_TONE_BEFORE_AFTER_EXAMPLES:
        assert example.before
        assert example.after
        assert example.evidence_handling == "secondary_progressive_disclosure"
        assert len(example.after) > len(example.before)


def test_validate_human_storytelling_text_flags_dry_service_language_without_lived_manifestation() -> None:
    errors = validate_human_storytelling_text(
        "Солнце и Луна в Козероге формируют паттерн эмоциональной обработки и внутренней динамики.",
        location="hero.body",
    )

    assert any(error.code == "bureaucratic_abstraction" for error in errors)
    assert any(error.code == "missing_lived_manifestation" for error in errors)
    assert all(error.recoverable for error in errors)


def test_validate_human_storytelling_text_accepts_humanized_evidence_backed_prose() -> None:
    errors = validate_human_storytelling_text(
        "Вам важно не просто быть собой в вакууме: рядом с другим человеком быстрее становится понятно, "
        "где ваша позиция и за что вы готовы отвечать. В напряжении защита может выглядеть как сдержанность, "
        "а зрелая форма — назвать переживание и выбрать спокойный следующий шаг. Что меняется, если не спешить "
        "объяснять себя сразу?",
        location="hero.body",
    )

    assert errors == []
