# ruff: noqa: RUF001, E501
"""Deterministic assembly for staged Self narrative outputs."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Literal

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
    allowed_fact_ids = _allowed_fact_ids(narrative_input)

    sections = [
        _section(
            "main_formula",
            _compose_main_formula_body(identity.paragraphs, narrative_input),
            _select_valid_evidence_ids(
                identity.evidence_ids,
                allowed_fact_ids,
                fallback_ids=_claim_evidence_ids(narrative_input.strengths),
            ),
        ),
        _section(
            "world_perception",
            house_scenarios.paragraphs[0],
            _select_valid_evidence_ids(
                house_scenarios.evidence_ids,
                allowed_fact_ids,
                fallback_ids=_scenario_evidence_ids(narrative_input),
            ),
        ),
        _section(
            "emotions_and_communication",
            _compose_emotional_body(emotional.paragraphs, narrative_input),
            _select_valid_evidence_ids(
                emotional.evidence_ids,
                allowed_fact_ids,
                fallback_ids=_claim_evidence_ids(narrative_input.risks),
            ),
        ),
        _section(
            "strengths",
            _compose_strengths_body(identity.paragraphs, narrative_input),
            _select_valid_evidence_ids(
                identity.evidence_ids,
                allowed_fact_ids,
                fallback_ids=_claim_evidence_ids(narrative_input.strengths),
            ),
        ),
        _section(
            "vulnerabilities",
            _compose_vulnerabilities_body(emotional.paragraphs, narrative_input),
            _select_valid_evidence_ids(
                emotional.evidence_ids,
                allowed_fact_ids,
                fallback_ids=_claim_evidence_ids(narrative_input.risks),
            ),
        ),
        _section(
            "relationships",
            relationships.paragraphs[0],
            _select_valid_evidence_ids(
                relationships.evidence_ids,
                allowed_fact_ids,
                fallback_ids=_claim_evidence_ids(narrative_input.relationship_patterns),
            ),
        ),
        _section(
            "sexuality",
            _compose_sexuality_body(relationships.paragraphs, narrative_input),
            _select_valid_evidence_ids(
                relationships.evidence_ids,
                allowed_fact_ids,
                fallback_ids=_claim_evidence_ids(narrative_input.sexuality_patterns),
            ),
        ),
        _section(
            "development",
            _compose_development_body(development.paragraphs, narrative_input),
            _select_valid_evidence_ids(
                development.evidence_ids,
                allowed_fact_ids,
                fallback_ids=_claim_evidence_ids(narrative_input.development_recommendations),
            ),
        ),
    ]

    title = f"Ваш внутренний портрет — {narrative_input.profile.name}"
    hero_body = " ".join(
        part
        for part in [
            _compose_main_formula_body(identity.paragraphs, narrative_input),
            _compose_emotional_body(emotional.paragraphs, narrative_input),
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
        hero=narrative_input_to_hero(
            narrative_input,
            hero_body,
            _select_valid_evidence_ids(
                identity.evidence_ids,
                allowed_fact_ids,
                fallback_ids=_claim_evidence_ids(narrative_input.strengths),
            ),
        ),
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


def _compose_main_formula_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    primary = paragraphs[0] if paragraphs else ""
    if _is_stage_paragraph_usable(primary):
        return primary
    dominant = narrative_input.dominants[0]
    mechanism = narrative_input.inner_mechanism.summary
    return " ".join(part for part in [dominant.body, mechanism] if part)


def _compose_emotional_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    primary = paragraphs[0] if paragraphs else ""
    if _is_stage_paragraph_usable(primary):
        return primary
    contradiction = narrative_input.contradictions[0].manifestation
    risk = narrative_input.failure_modes[0].manifestation
    return " ".join(part for part in [contradiction, risk] if part)


def _compose_development_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    primary = paragraphs[0] if paragraphs else ""
    mechanism = narrative_input.inner_mechanism.summary
    risk = narrative_input.failure_modes[0].manifestation
    mature = narrative_input.contradictions[0].mature_expression
    if _is_stage_paragraph_usable(primary) and not _contains_career_language(primary):
        return " ".join(part for part in [primary, f"Механизм: {mechanism}", f"Риск: {risk}", f"Зрелая форма: {mature}"] if part)
    recommendation = " ".join(item.claim for item in narrative_input.development_recommendations[:2])
    return " ".join(part for part in [recommendation, f"Механизм: {mechanism}", f"Риск: {risk}", f"Зрелая форма: {mature}"] if part)


def _compose_strengths_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    if len(paragraphs) >= 2 and paragraphs[-1] != paragraphs[0] and _is_stage_paragraph_usable(paragraphs[-1]):
        return paragraphs[-1]
    strengths = "; ".join(item.claim for item in narrative_input.strengths[:2])
    maturity = narrative_input.maturity_levels.high.body
    return " ".join(part for part in [strengths, maturity] if part)


def _compose_vulnerabilities_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    if len(paragraphs) >= 2 and paragraphs[-1] != paragraphs[0] and _is_stage_paragraph_usable(paragraphs[-1]):
        return paragraphs[-1]
    risks = "; ".join(item.claim for item in narrative_input.risks[:2])
    failure = narrative_input.failure_modes[0].manifestation
    return " ".join(part for part in [risks, failure] if part)


def _compose_sexuality_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    if len(paragraphs) >= 2 and paragraphs[-1] != paragraphs[0] and _is_stage_paragraph_usable(paragraphs[-1]):
        return paragraphs[-1]
    contradiction = narrative_input.contradictions[0]
    failure_mode = narrative_input.failure_modes[0]
    return " ".join(
        part
        for part in [
            contradiction.manifestation,
            contradiction.mature_expression,
            failure_mode.manifestation,
        ]
        if part
    )


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


def _is_stage_paragraph_usable(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and re.search(r"[A-Za-z]", stripped) is None


def _contains_career_language(text: str) -> bool:
    normalized = text.casefold()
    return any(
        token in normalized
        for token in (
            "карьер",
            "проф",
            "работ",
            "деньг",
            "доход",
            "заработ",
            "должност",
            "рол",
            "среда",
            "стратег",
            "направлен",
            "реализац",
        )
    )


def _allowed_fact_ids(narrative_input: NarrativeInput) -> set[str]:
    allowed = {fact.id for fact in narrative_input.key_facts}
    allowed.update(fact.id for fact in narrative_input.key_aspects)
    for claim_group in (
        narrative_input.strengths,
        narrative_input.risks,
        narrative_input.relationship_patterns,
        narrative_input.sexuality_patterns,
        narrative_input.development_recommendations,
    ):
        for claim in claim_group:
            allowed.update(claim.evidence_ids)
    for dominant in narrative_input.dominants:
        allowed.update(dominant.evidence_ids)
    for step in narrative_input.inner_mechanism.steps:
        allowed.update(step.evidence_ids)
    for scenario in narrative_input.house_scenarios:
        allowed.update(scenario.evidence_ids)
        for note in scenario.evidence_notes:
            allowed.update(note.fact_ids)
            allowed.update(note.limitation_fact_ids)
    for question in narrative_input.calibration_questions:
        allowed.update(question.evidence_ids)
    for contradiction in narrative_input.contradictions:
        allowed.update(contradiction.evidence_ids)
        for note in contradiction.evidence_notes:
            allowed.update(note.fact_ids)
            allowed.update(note.limitation_fact_ids)
    for failure_mode in narrative_input.failure_modes:
        allowed.update(failure_mode.evidence_ids)
        for note in failure_mode.evidence_notes:
            allowed.update(note.fact_ids)
            allowed.update(note.limitation_fact_ids)
    for band_name in ("low", "medium", "high"):
        band = getattr(narrative_input.maturity_levels, band_name)
        allowed.update(band.evidence_ids)
        for note in band.evidence_notes:
            allowed.update(note.fact_ids)
            allowed.update(note.limitation_fact_ids)
    return allowed


def _claim_evidence_ids(claims: Sequence[Any]) -> list[str]:
    evidence_ids: list[str] = []
    for claim in claims[:2]:
        evidence_ids.extend(getattr(claim, "evidence_ids", []))
    return evidence_ids


def _scenario_evidence_ids(narrative_input: NarrativeInput) -> list[str]:
    evidence_ids: list[str] = []
    for scenario in narrative_input.house_scenarios[:2]:
        evidence_ids.extend(scenario.evidence_ids)
    return evidence_ids


def _select_valid_evidence_ids(
    candidate_ids: list[str],
    allowed_fact_ids: set[str],
    *,
    fallback_ids: list[str],
) -> list[str]:
    filtered = [fact_id for fact_id in candidate_ids if fact_id in allowed_fact_ids]
    if filtered:
        return filtered
    deduped_fallback: list[str] = []
    for fact_id in fallback_ids:
        if fact_id in allowed_fact_ids and fact_id not in deduped_fallback:
            deduped_fallback.append(fact_id)
    return deduped_fallback[:6]
