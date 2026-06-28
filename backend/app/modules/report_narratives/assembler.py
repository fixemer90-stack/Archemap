# ruff: noqa: RUF001, E501
"""Deterministic assembly for staged Self narrative outputs."""

from __future__ import annotations

from typing import Literal

from app.modules.report_narratives.schemas import (
    AssemblyCheck,
    CareerCTA,
    EvidenceNote,
    HeroSection,
    NarrativeInput,
    NarrativePlan,
    NarrativeSection,
    SelfNarrative,
    StagedSectionOutput,
)

_SECTION_TITLES: dict[str, str] = {
    "main_formula": "Главная формула личности",
    "world_perception": "Как вы воспринимаете мир",
    "emotions_and_communication": "Эмоции и коммуникация",
    "strengths": "Сильные стороны",
    "vulnerabilities": "Уязвимости",
    "relationships": "Отношения",
    "sexuality": "Близость и сексуальность",
    "development": "Вектор развития",
}


def assemble_self_narrative(
    *,
    narrative_input: NarrativeInput,
    plan: NarrativePlan,
    stage_outputs: dict[str, object],
    final_check: AssemblyCheck,
) -> SelfNarrative:
    """Assemble a single Self narrative from ready staged outputs."""
    staged = {key: StagedSectionOutput.model_validate(value) for key, value in stage_outputs.items()}
    identity = staged["identity"]
    emotional = staged["emotional"]
    relationships = staged["relationships"]
    development = staged["development"]
    house_scenarios = staged["house_scenarios"]

    sections = [
        _section(
            "main_formula",
            identity.paragraphs[0],
            identity.evidence_ids,
        ),
        _section(
            "world_perception",
            house_scenarios.paragraphs[0],
            house_scenarios.evidence_ids,
        ),
        _section(
            "emotions_and_communication",
            emotional.paragraphs[0],
            emotional.evidence_ids,
        ),
        _section(
            "strengths",
            identity.paragraphs[-1],
            identity.evidence_ids,
        ),
        _section(
            "vulnerabilities",
            emotional.paragraphs[-1],
            emotional.evidence_ids,
        ),
        _section(
            "relationships",
            relationships.paragraphs[0],
            relationships.evidence_ids,
        ),
        _section(
            "sexuality",
            relationships.paragraphs[-1],
            relationships.evidence_ids,
        ),
        _section(
            "development",
            _compose_development_body(development.paragraphs, narrative_input),
            development.evidence_ids,
        ),
    ]

    title = f"Ваш внутренний портрет — {narrative_input.profile.name}"
    hero_body = " ".join(
        part
        for part in [
            identity.paragraphs[0],
            emotional.paragraphs[0],
            f"Сборка выполнена по staged plan {plan.prompt_version}.",
        ]
        if part
    )
    summary_parts = [
        development.paragraphs[-1],
        house_scenarios.paragraphs[-1],
        *final_check.tone_notes[:1],
    ]

    return SelfNarrative(
        title=title,
        hero=narrative_input_to_hero(narrative_input, hero_body, identity.evidence_ids),
        dominants=narrative_input.dominants,
        inner_mechanism=narrative_input.inner_mechanism,
        house_scenarios=narrative_input.house_scenarios,
        calibration_questions=narrative_input.calibration_questions,
        contradictions=narrative_input.contradictions,
        failure_modes=narrative_input.failure_modes,
        maturity_levels=narrative_input.maturity_levels,
        sections=sections,
        career_cta=CareerCTA(
            title="Отдельный отчёт Career",
            body="Если захотите отдельно разобрать профессиональную роль, деньги, среду и стратегию роста, лучше открыть специальный Career-отчёт.",
            bullets=["Профроли", "среда", "стратегия роста"],
            button_label="Открыть Career",
        ),
        final_summary=" ".join(part for part in summary_parts if part),
    )


def narrative_input_to_hero(
    narrative_input: NarrativeInput,
    body: str,
    evidence_ids: list[str],
) -> HeroSection:
    return HeroSection(
        id="hero",
        title="Главное о вас",
        body=body,
        bullets=[
            narrative_input.calculation_quality.quality_label,
            f"Соционика: {narrative_input.socionics.type_ru}",
            f"Архетип: {narrative_input.archetype.primary}",
        ],
        evidence_notes=[EvidenceNote(claim=body, fact_ids=list(evidence_ids))],
    )


def _compose_development_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    mechanism = narrative_input.inner_mechanism.summary
    risk = narrative_input.failure_modes[0].manifestation
    mature = narrative_input.contradictions[0].mature_expression
    return " ".join([paragraphs[0], f"Механизм: {mechanism}", f"Риск: {risk}", f"Зрелая форма: {mature}"])


def _section(
    section_id: Literal[
        "main_formula",
        "world_perception",
        "emotions_and_communication",
        "strengths",
        "vulnerabilities",
        "relationships",
        "sexuality",
        "development",
    ],
    body: str,
    evidence_ids: list[str],
) -> NarrativeSection:
    return NarrativeSection(
        id=section_id,
        title=_SECTION_TITLES[section_id],
        body=body,
        bullets=[],
        evidence_notes=[EvidenceNote(claim=body, fact_ids=list(evidence_ids))],
    )
