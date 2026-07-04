# ruff: noqa: RUF001, E501
"""E15 S03 regressions for staged assembler narrative rhythm."""

from __future__ import annotations

from tests.unit.test_report_narratives.test_staged_assembly import _good_stage_outputs, _narrative_input, _plan

from app.modules.report_narratives.assembler import assemble_self_narrative
from app.modules.report_narratives.schemas import (
    AssemblyCheck,
    DevelopmentSectionOutput,
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


def test_assembler_keeps_hero_compact_while_sections_keep_rhythm() -> None:
    narrative = assemble_self_narrative(
        narrative_input=_narrative_input(),
        plan=_plan(),
        stage_outputs=_good_stage_outputs(),
        final_check=AssemblyCheck(),
    )

    hero_paragraphs = [paragraph for paragraph in narrative.hero.body.split("\n\n") if paragraph.strip()]
    assert 1 <= len(hero_paragraphs) <= 2
    assert 900 <= len(narrative.hero.body) <= 2200

    paragraph_counts = {
        section.id: len([paragraph for paragraph in section.body.split("\n\n") if paragraph.strip()])
        for section in narrative.sections
    }
    assert paragraph_counts["main_formula"] in {2, 3}
    assert paragraph_counts["relationships"] in {2, 3}
    assert paragraph_counts["development"] in {2, 3}


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
