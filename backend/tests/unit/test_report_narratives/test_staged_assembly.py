# ruff: noqa: RUF001, E501
"""RED tests for E14 S06 staged assembly and anti-horoscope quality gates."""

from __future__ import annotations

from tests.unit.test_report_narratives.test_schemas import make_narrative_input_payload

from app.modules.report_narratives.assembler import _section, assemble_self_narrative
from app.modules.report_narratives.schemas import (
    AssemblyCheck,
    DevelopmentSectionOutput,
    EmotionalSectionOutput,
    HouseScenariosSectionOutput,
    IdentitySectionOutput,
    NarrativeInput,
    NarrativePlan,
    RelationshipSectionOutput,
    SelfNarrative,
)
from app.modules.report_narratives.validators import validate_assembled_self_narrative


def _narrative_input() -> NarrativeInput:
    return NarrativeInput.model_validate(make_narrative_input_payload())


def _plan() -> NarrativePlan:
    return NarrativePlan.model_validate(
        {
            "prompt_version": "self_plan_v2",
            "sections": [
                {
                    "section_id": "identity",
                    "title": "Как собирается ваша идентичность",
                    "required_evidence_ids": ["sun_virgo_house_9", "mercury_venus_jupiter_leo_8"],
                    "focus": "Смысл и выразительность как ось личности.",
                },
                {
                    "section_id": "emotional",
                    "title": "Как вы переживаете напряжение",
                    "required_evidence_ids": ["moon_trine_mercury"],
                    "focus": "Чувство проходит через речь и внутренний анализ.",
                },
                {
                    "section_id": "relationships",
                    "title": "Как вы строите близость",
                    "required_evidence_ids": ["mercury_venus_jupiter_leo_8"],
                    "focus": "Глубина и эмоциональная интенсивность в контакте.",
                },
                {
                    "section_id": "development",
                    "title": "Куда лучше развиваться",
                    "required_evidence_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                    "focus": "Собирать устойчивый ритм и практический вектор.",
                },
                {
                    "section_id": "house_scenarios",
                    "title": "Где это проявляется в жизни",
                    "required_evidence_ids": ["sun_virgo_house_9"],
                    "focus": "9 дом как жизненная ось смысла.",
                },
            ],
            "global_guardrails": [
                "use only provided evidence ids",
                "no Career deep dive",
                "no generic horoscope prose",
            ],
            "assembly_notes": "Собрать единый Self report без повторов и tone drift.",
        }
    )


def _good_stage_outputs() -> dict[str, object]:
    return {
        "identity": IdentitySectionOutput(
            section_id="identity",
            title="Как собирается ваша идентичность",
            paragraphs=[
                "Ваша идентичность собирается вокруг потребности найти систему смысла и затем выразить её в заметной форме.",
                "Когда позиция не собрана, внутреннее напряжение растёт не из пустоты, а из потребности опереться на ясный каркас.",
            ],
            evidence_ids=["sun_virgo_house_9", "mercury_venus_jupiter_leo_8"],
            covered_pattern_ids=["house_axis_house_scenario_sun_9", "planet_role_sun_virgo_house_9"],
        ),
        "emotional": EmotionalSectionOutput(
            section_id="emotional",
            title="Как вы переживаете напряжение",
            paragraphs=[
                "Чувство быстро доходит до речи, поэтому переживание редко остаётся совсем без слов и образов.",
                "Риск возникает там, где эмоциональная интенсивность ускоряет объяснение быстрее, чем успевает появиться внутренняя ясность.",
            ],
            evidence_ids=["moon_trine_mercury"],
            covered_pattern_ids=["chart_dynamic_moon_saturn_regulation"],
        ),
        "relationships": RelationshipSectionOutput(
            section_id="relationships",
            title="Как вы строите близость",
            paragraphs=[
                "В близости вам важна не поверхностная симпатия, а ощущение эмоциональной глубины и вовлечённости.",
                "Если контакт кажется формальным, интерес быстро падает, потому что без глубины связь не переживается как живая.",
            ],
            evidence_ids=["mercury_venus_jupiter_leo_8"],
            covered_pattern_ids=["aspect_pattern_intimacy_depth"],
        ),
        "development": DevelopmentSectionOutput(
            section_id="development",
            title="Куда лучше развиваться",
            paragraphs=[
                "Развитие начинается не с ускорения, а с момента, когда вы выдерживаете неполную ясность и всё равно делаете следующий шаг.",
                "Зрелая стратегия здесь — сначала собрать рабочую опору, а затем усиливать выразительность уже поверх неё.",
            ],
            evidence_ids=["sun_virgo_house_9", "moon_trine_mercury"],
            covered_pattern_ids=["contradiction_structure_vs_expression"],
        ),
        "house_scenarios": HouseScenariosSectionOutput(
            section_id="house_scenarios",
            title="Где это проявляется в жизни",
            paragraphs=[
                "Ось 9 дома делает вопросы смысла, мировоззрения и внутренней позиции не фоном, а центральной жизненной темой.",
                "Поэтому устойчивость растёт там, где знание превращается в понятную систему и практический ориентир.",
            ],
            evidence_ids=["sun_virgo_house_9"],
            covered_pattern_ids=["house_axis_house_scenario_sun_9"],
        ),
    }


def test_assembler_section_allows_empty_evidence_ids_without_empty_evidence_note() -> None:
    section = _section(
        "development",
        "Развитие начинается с устойчивой опоры и внимательного отношения к собственному ритму.",
        [],
    )

    assert section.evidence_notes == []


def test_assemble_self_narrative_produces_single_report_in_self_order_and_preserves_evidence() -> None:
    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=_good_stage_outputs(),
        final_check=AssemblyCheck(),
    )

    assert isinstance(narrative, SelfNarrative)
    assert [section.id for section in narrative.sections] == [
        "main_formula",
        "world_perception",
        "emotions_and_communication",
        "strengths",
        "vulnerabilities",
        "relationships",
        "sexuality",
        "development",
    ]
    all_fact_ids = {
        fact_id for section in narrative.sections for note in section.evidence_notes for fact_id in note.fact_ids
    }
    assert "sun_virgo_house_9" in all_fact_ids
    assert "moon_trine_mercury" in all_fact_ids
    assert "mercury_venus_jupiter_leo_8" in all_fact_ids
    assert "профес" not in narrative.final_summary.lower()


def test_assemble_self_narrative_expands_each_section_into_substantial_human_block() -> None:
    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=_good_stage_outputs(),
        final_check=AssemblyCheck(),
    )

    for section in narrative.sections:
        assert section.body.strip(), section.id
        assert section.body.count(".") >= 1, section.id

    assert narrative.hero.body.strip()
    assert narrative.final_summary.strip()
    assert "?" not in narrative.final_summary


def test_assemble_self_narrative_preserves_repeated_stage_sentences_without_truncating_sections() -> None:
    stage_outputs = _good_stage_outputs()
    repeated = (
        "Повторяемая мысль должна появиться только один раз в готовом отчёте, а не размножаться по разным разделам."
    )
    for output in stage_outputs.values():
        output.paragraphs.append(repeated)  # type: ignore[attr-defined]

    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=stage_outputs,
        final_check=AssemblyCheck(tone_notes=[repeated]),
    )

    visible_blocks = [narrative.hero.body, *(section.body for section in narrative.sections), narrative.final_summary]
    all_text = "\n".join(visible_blocks).casefold()

    assert repeated.casefold() in all_text


def test_assemble_self_narrative_preserves_full_long_stage_text_without_truncation() -> None:
    stage_outputs = _good_stage_outputs()
    marker = "маркер-полного-текста-после-старого-лимита"
    long_paragraph = " ".join(
        f"Это полный длинный фрагмент секции без искусственного обрезания номер {index}." for index in range(90)
    )
    long_paragraph = f"{long_paragraph} {marker}."
    identity = stage_outputs["identity"]
    assert isinstance(identity, IdentitySectionOutput)
    identity.paragraphs[0] = long_paragraph

    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=stage_outputs,
        final_check=AssemblyCheck(),
    )

    main_formula = next(section for section in narrative.sections if section.id == "main_formula")
    assert marker in main_formula.body
    assert marker in narrative.hero.body


def test_validate_assembled_self_narrative_rejects_duplicate_generic_career_and_fatalist_prose() -> None:
    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=_good_stage_outputs(),
        final_check=AssemblyCheck(),
    )
    bad = narrative.model_copy(deep=True)
    bad.sections[0].body = "Вы очень чувствительный человек, как и многие люди с такой картой."
    bad.sections[1].body = bad.sections[0].body
    bad.sections[2].body = "Вам идеально подойдут профессии в менеджменте и денежной стратегии."
    bad.final_summary = "Все люди с таким положением неизбежно обречены повторять один и тот же сценарий."

    errors = validate_assembled_self_narrative(bad, _narrative_input())
    codes = {error.code for error in errors}

    assert "duplicate_paragraph" in codes
    assert "generic_horoscope_prose" in codes
    assert "career_boundary_violation" in codes
    assert "fatalistic_language" in codes


def test_validate_assembled_self_narrative_rejects_missing_mechanism_risk_mature_chain() -> None:
    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=_good_stage_outputs(),
        final_check=AssemblyCheck(),
    )
    bad = narrative.model_copy(deep=True)
    bad.sections[7].body = "Развитие связано с ростом и движением вперёд."

    errors = validate_assembled_self_narrative(bad, _narrative_input())

    assert any(error.code == "missing_mechanism_risk_mature_chain" for error in errors)


def test_validate_assembled_self_narrative_rejects_cross_section_contradiction_and_tone_drift() -> None:
    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=_good_stage_outputs(),
        final_check=AssemblyCheck(),
    )
    bad = narrative.model_copy(deep=True)
    bad.sections[5].body = "В близости вам важна эмоциональная глубина и вовлечённость."
    bad.sections[6].body = "В близости вам достаточно поверхностного контакта, глубина только мешает."
    bad.sections[7].body = "Ты можешь просто взять этот JSON schema и пройти stage без паузы."

    errors = validate_assembled_self_narrative(bad, _narrative_input())
    codes = {error.code for error in errors}

    assert "cross_section_contradiction" in codes
    assert "tone_drift" in codes
