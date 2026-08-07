# ruff: noqa: RUF001, E501
"""E15 S03 regressions for staged assembler narrative rhythm."""

from __future__ import annotations

from tests.unit.test_report_narratives.test_staged_assembly import _good_stage_outputs, _narrative_input, _plan

from app.modules.report_narratives.assembler import assemble_self_narrative
from app.modules.report_narratives.schemas import (
    AssemblyCheck,
    DevelopmentSectionOutput,
    EmotionalSectionOutput,
    IdentitySectionOutput,
    RelationshipSectionOutput,
)


def test_assembler_preserves_useful_second_and_third_stage_paragraphs() -> None:
    stage_outputs = _good_stage_outputs()
    identity_marker = "Третий абзац идентичности показывает живую сцену, где позиция собирается не сразу, а через разговор и внутреннюю проверку."
    relationship_marker = "Третий абзац близости показывает, что контакт становится надёжнее, когда в нём есть место паузе, прямому слову и телесному спокойствию."
    development_marker = "Третий абзац развития показывает, что следующий шаг лучше делать не рывком, а через маленькую устойчивую практику."

    identity = stage_outputs["identity"]
    assert isinstance(identity, IdentitySectionOutput)
    identity.paragraphs.append(identity_marker)

    relationships = stage_outputs["relationships"]
    assert isinstance(relationships, RelationshipSectionOutput)
    relationships.paragraphs.append(relationship_marker)

    development = stage_outputs["development"]
    assert isinstance(development, DevelopmentSectionOutput)
    development.paragraphs.append(development_marker)

    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=stage_outputs,
        final_check=AssemblyCheck(),
    )

    sections = {section.id: section.body for section in narrative.sections}
    assert identity_marker in sections["main_formula"]
    assert relationship_marker in sections["relationships"]
    assert development_marker in sections["development"]


def test_assembler_keeps_full_stage_rhythm_without_length_caps() -> None:
    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=_good_stage_outputs(),
        final_check=AssemblyCheck(),
    )

    hero_paragraphs = [paragraph for paragraph in narrative.hero.body.split("\n\n") if paragraph.strip()]
    assert hero_paragraphs

    paragraph_counts = {
        section.id: len([paragraph for paragraph in section.body.split("\n\n") if paragraph.strip()])
        for section in narrative.sections
    }
    assert paragraph_counts["main_formula"] >= 2
    assert paragraph_counts["relationships"] >= 2
    assert paragraph_counts["development"] >= 2


def test_assembler_preserves_live_like_long_stage_output_in_hero() -> None:
    stage_outputs = _good_stage_outputs()
    identity = stage_outputs["identity"]
    assert isinstance(identity, IdentitySectionOutput)
    stage_outputs["identity"] = identity.model_copy(
        update={
            "paragraphs": [
                "Вы не раз замечали, что в разговоре с другим человеком ваша позиция становится яснее. "
                "Это вход через узнавание, который должен остаться в главном блоке. "
                "Солнце и Луна в Козероге в 7 доме можно раскрыть ниже, но не превращать первый экран в техническую простыню. "
                "Лишний длинный хвост с повтором доминант, механизма, сценариев, рисков, зрелых форм и дополнительных деталей не должен попадать в главный блок."
            ]
        }
    )
    emotional = stage_outputs["emotional"]
    assert isinstance(emotional, EmotionalSectionOutput)
    stage_outputs["emotional"] = emotional.model_copy(
        update={
            "paragraphs": [
                "В эмоциональном контакте вы можете одновременно тянуться к близости и проверять безопасность. "
                "Эта живая сцена должна дать второй абзац. "
                "Лишний эмоциональный хвост с повторными деталями, аспектами и служебными формулировками не должен раздувать главный блок."
            ]
        }
    )

    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=stage_outputs,
        final_check=AssemblyCheck(),
    )

    hero_paragraphs = [paragraph for paragraph in narrative.hero.body.split("\n\n") if paragraph.strip()]
    assert hero_paragraphs
    assert "Это вход через узнавание" in narrative.hero.body
    assert "Эта живая сцена" in narrative.hero.body
    assert "Лишний длинный хвост" in narrative.hero.body
    assert "Лишний эмоциональный хвост" in narrative.hero.body


def test_assembler_does_not_expose_mechanical_prefixes_in_user_prose() -> None:
    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=_good_stage_outputs(),
        final_check=AssemblyCheck(),
    )

    visible_text = "\n".join(
        [narrative.hero.body, narrative.final_summary, *(section.body for section in narrative.sections)]
    )

    assert "Механизм:" not in visible_text
    assert "Риск:" not in visible_text
    assert "Зрелая форма:" not in visible_text


def test_assembler_repairs_final_summary_when_dedupe_strips_it_to_one_question() -> None:
    stage_outputs = _good_stage_outputs()
    development = stage_outputs["development"]
    assert isinstance(development, DevelopmentSectionOutput)
    stage_outputs["development"] = development.model_copy(
        update={
            "paragraphs": [
                *development.paragraphs,
                "Когда напряжение растёт, замечаете ли вы, что сначала сдерживаете реакцию?",
            ]
        }
    )

    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=stage_outputs,
        final_check=AssemblyCheck(),
    )

    assert narrative.final_summary.strip()
    assert "?" not in narrative.final_summary


def test_assembler_replaces_relationship_placeholder_with_substantial_grounded_body() -> None:
    stage_outputs = _good_stage_outputs()
    relationships = stage_outputs["relationships"]
    assert isinstance(relationships, RelationshipSectionOutput)
    stage_outputs["relationships"] = relationships.model_copy(
        update={"paragraphs": ["Отношения требуют дополнительной сборки."]}
    )

    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=stage_outputs,
        final_check=AssemblyCheck(),
    )

    relationships_section = next(section for section in narrative.sections if section.id == "relationships")
    assert "дополнительной сборки" not in relationships_section.body
    assert "довер" in relationships_section.body.lower() or "контакт" in relationships_section.body.lower()
