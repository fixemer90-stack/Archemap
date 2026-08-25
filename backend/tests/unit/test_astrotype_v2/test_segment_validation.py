# ruff: noqa: E501,RUF001
"""Narrative depth quality gates for Astrotype v2 segment outputs."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.modules.astrotype_v2.schemas import ReportSegmentOutputV2, SectionRenderInputV2, SectionThemeInputV2
from app.modules.astrotype_v2.segment_validation import SegmentValidationError, validate_segment_output_v2


def _section_input(section_id: str = "core_pattern") -> SectionRenderInputV2:
    return SectionRenderInputV2(
        chart_id=uuid.uuid4(),
        source_version="v2.0",
        section_id=section_id,
        section_title="Ядро личности" if section_id == "core_pattern" else "Восприятие и мышление",
        section_purpose="deep psychological section",
        owned_themes=[
            SectionThemeInputV2(
                id="theme:core:sun",
                title="Sun theme",
                summary="Grounded solar summary",
                fact_keys=["fact:sun"],
                evidence_ids=["ev:sun"],
                weight=0.9,
                confidence=1.0,
                fact_type="placement",
                psychological_mechanism="mechanism from evidence",
                lived_manifestation="lived manifestation from evidence",
                inner_tension="inner tension from evidence",
                protective_strategy="protective pattern from evidence",
                mature_expression="mature expression from evidence",
                integration_question="soft integration question",
                evidence_strength="strong",
            )
        ],
        reference_themes=[],
        forbidden_theme_ids=["theme:forbidden"],
        evidence_ids=["ev:sun"],
        already_explained={},
        style_contract={},
        depth_contract={},
        continuation_policy={"continuation_supported": True},
    )


def _deep_body(paragraphs: int = 6, words_per_paragraph: int = 125) -> str:
    base = (
        "Внутренний психологический механизм раздела показывает, как человек собирает ощущение себя и выбирает направление действия. "
        "В жизни это проявляется как повторяющийся сценарий: сначала возникает чувствительность к контексту, затем желание сохранить контроль, "
        "а после этого появляется готовность открыто действовать и выдерживать реакцию другого человека. "
        "Главное напряжение держится между потребностью защитить уязвимое место и стремлением быть видимым без лишней брони. "
        "Защитная стратегия под давлением может превращаться в резкость, уход в анализ или компенсацию через чрезмерную самостоятельность. "
        "В зрелом интегрированном выражении тот же материал становится ресурсом: человек замечает импульс, выбирает форму контакта и действует осознанно. "
        "Мягкий вопрос для интеграции помогает проверить, какой следующий шаг сохраняет живость, точность и не прячет силу за автоматической защитой. "
    )
    result: list[str] = []
    for index in range(paragraphs):
        words = (f"Абзац {index + 1}. " + base).split()
        while len(words) < words_per_paragraph:
            words.extend(base.split())
        result.append(" ".join(words[:words_per_paragraph]))
    return "\n\n".join(result)


def _output(body: str, **overrides: Any) -> ReportSegmentOutputV2:
    payload: dict[str, Any] = {
        "contract_version": "report_segment_output_v2",
        "section_id": "core_pattern",
        "title": "Ядро личности",
        "body": body,
        "covered_theme_ids": ["theme:core:sun"],
        "evidence_ids": ["ev:sun"],
        "continuation_complete": True,
        "continuation_cursor": None,
        "notes": [],
    }
    payload.update(overrides)
    return ReportSegmentOutputV2.model_validate(payload)


def test_shallow_80_word_complete_section_fails_validation() -> None:
    body = " ".join(
        [
            "Внутренний механизм проявляется в жизни через напряжение, защитную стратегию и зрелое выражение ресурса."
        ]
        * 8
    )

    with pytest.raises(SegmentValidationError, match="underdeveloped"):
        validate_segment_output_v2(output=_output(body), section_input=_section_input())



def test_missing_owned_evidence_ids_fail_validation_before_report_assembly() -> None:
    with pytest.raises(SegmentValidationError, match="missing evidence ids"):
        validate_segment_output_v2(output=_output(_deep_body(), evidence_ids=[]), section_input=_section_input())

def test_raw_english_fact_dump_fails_validation() -> None:
    body = _deep_body().replace(
        "Внутренний психологический механизм",
        "Sun is in Aries with orb 2°. Moon is in house 10. Mars square Saturn aspect with orb 1°. Inner mechanism",
        1,
    )

    with pytest.raises(SegmentValidationError, match="raw fact dump"):
        validate_segment_output_v2(output=_output(body), section_input=_section_input())


def test_generic_horoscope_filler_fails_validation() -> None:
    body = _deep_body() + "\n\nУникальная энергия помогает раскрыть свой потенциал, важно найти баланс и следуйте своему сердцу."

    with pytest.raises(SegmentValidationError, match="generic filler"):
        validate_segment_output_v2(output=_output(body), section_input=_section_input())


def test_sections_missing_lived_or_mature_depth_moves_fail_validation() -> None:
    body_without_lived = _deep_body().replace("В жизни это проявляется", "Эта тема заметна")
    body_without_mature = _deep_body().replace("В зрелом интегрированном выражении", "В хорошем варианте")

    with pytest.raises(SegmentValidationError, match="missing depth moves"):
        validate_segment_output_v2(output=_output(body_without_lived), section_input=_section_input())

    with pytest.raises(SegmentValidationError, match="missing depth moves"):
        validate_segment_output_v2(output=_output(body_without_mature), section_input=_section_input())


def test_long_grounded_core_section_passes_without_artificial_max_length() -> None:
    body = _deep_body(paragraphs=10, words_per_paragraph=140)

    assert validate_segment_output_v2(output=_output(body), section_input=_section_input()).body == body


def test_other_upper_sections_use_450_word_four_paragraph_floor() -> None:
    body = _deep_body(paragraphs=3, words_per_paragraph=105)
    section_input = _section_input(section_id="perception_and_mind")
    output = _output(body, section_id="perception_and_mind", title="Восприятие и мышление")

    assert validate_segment_output_v2(output=output, section_input=section_input).section_id == "perception_and_mind"


def test_continuation_incomplete_state_keeps_cursor_but_is_not_a_complete_section() -> None:
    partial = _output(
        _deep_body(paragraphs=3, words_per_paragraph=40),
        continuation_complete=False,
        continuation_cursor="continue:core:2",
    )

    validated = validate_segment_output_v2(output=partial, section_input=_section_input())

    assert validated.continuation_complete is False
    assert validated.continuation_cursor == "continue:core:2"

    with pytest.raises(SegmentValidationError, match="continuation cursor required"):
        validate_segment_output_v2(
            output=_output(_deep_body(paragraphs=3, words_per_paragraph=40), continuation_complete=False),
            section_input=_section_input(),
        )
