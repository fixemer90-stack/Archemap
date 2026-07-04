# ruff: noqa: RUF001, E501
"""Deterministic assembly for staged Self narrative outputs."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
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
            _compose_world_perception_body(house_scenarios.paragraphs, narrative_input),
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
            _compose_relationships_body(relationships.paragraphs, narrative_input),
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
    hero_body = _compose_hero_body(
        identity.paragraphs,
        emotional.paragraphs,
        relationships.paragraphs,
        narrative_input,
    )
    summary_parts = [
        _compose_development_body(development.paragraphs, narrative_input),
        _compose_relationships_body(relationships.paragraphs, narrative_input),
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
        final_summary=_join_body(part for part in summary_parts if part),
    )


def narrative_input_to_hero(
    narrative_input: NarrativeInput,
    body: str,
    evidence_ids: list[str],
) -> HeroSection:
    evidence_notes = [EvidenceNote(claim=_evidence_claim(body), fact_ids=list(evidence_ids))] if evidence_ids else []
    return HeroSection(
        id="hero",
        title="Главное о вас",
        body=body,
        bullets=[
            narrative_input.calculation_quality.quality_label,
            f"Соционика: {narrative_input.socionics.type_ru}",
            f"Архетип: {narrative_input.archetype.primary}",
        ],
        evidence_notes=evidence_notes,
    )


def _compose_main_formula_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    dominant = narrative_input.dominants[0]
    steps = [step.body for step in narrative_input.inner_mechanism.steps[:3]]
    contradiction = narrative_input.contradictions[0]
    return _section_body(
        _usable_stage_paragraphs(paragraphs, limit=3),
        [
            [dominant.body, narrative_input.inner_mechanism.summary, *steps],
            [contradiction.tension, contradiction.mature_expression, *_shared_depth_parts(narrative_input)],
        ],
        max_paragraphs=3,
    )


def _compose_emotional_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    contradiction = narrative_input.contradictions[0].manifestation
    risk = narrative_input.failure_modes[0]
    return _section_body(
        _usable_stage_paragraphs(paragraphs, limit=2),
        [
            [narrative_input.key_aspects[0].meaning if narrative_input.key_aspects else "", contradiction],
            [risk.trigger, risk.manifestation, risk.supportive_reframe, *_shared_depth_parts(narrative_input)],
        ],
        max_paragraphs=3,
    )


def _compose_world_perception_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    scenario = narrative_input.house_scenarios[0]
    facts = [fact.meaning for fact in narrative_input.key_facts[:2]]
    return _section_body(
        _usable_stage_paragraphs(paragraphs, limit=2),
        [
            [scenario.need, scenario.manifestation, scenario.shadow, scenario.mature_expression],
            [*facts, narrative_input.inner_mechanism.summary, *_maturity_parts(narrative_input)],
        ],
        max_paragraphs=3,
    )


def _compose_relationships_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    claims = [item.claim for item in narrative_input.relationship_patterns[:2]]
    contradiction = narrative_input.contradictions[1]
    failure = narrative_input.failure_modes[2]
    return _section_body(
        _usable_stage_paragraphs(paragraphs, limit=3),
        [
            [*claims, contradiction.tension, contradiction.manifestation, contradiction.mature_expression],
            [failure.trigger, failure.supportive_reframe, *_shared_depth_parts(narrative_input)],
        ],
        max_paragraphs=3,
    )


def _compose_development_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    recommendation = " ".join(item.claim for item in narrative_input.development_recommendations[:2])
    failure = narrative_input.failure_modes[0]
    contradiction = narrative_input.contradictions[0]
    return _section_body(
        _usable_stage_paragraphs(paragraphs, limit=3, reject_career=True),
        [
            [recommendation, narrative_input.inner_mechanism.summary],
            [
                failure.manifestation,
                failure.trigger,
                failure.supportive_reframe,
                contradiction.mature_expression,
                narrative_input.maturity_levels.medium.body,
                *_maturity_parts(narrative_input),
            ],
        ],
        max_paragraphs=3,
    )


def _compose_strengths_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    strengths = "; ".join(item.claim for item in narrative_input.strengths[:2])
    maturity = narrative_input.maturity_levels.high.body
    return _section_body(
        _usable_stage_paragraphs(paragraphs, limit=3),
        [
            [strengths, narrative_input.dominants[0].body, maturity],
            [
                narrative_input.inner_mechanism.steps[1].body,
                narrative_input.contradictions[0].mature_expression,
                *_shared_depth_parts(narrative_input),
            ],
        ],
        max_paragraphs=3,
    )


def _compose_vulnerabilities_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    risks = "; ".join(item.claim for item in narrative_input.risks[:2])
    failure = narrative_input.failure_modes[0]
    contradiction = narrative_input.contradictions[0]
    return _section_body(
        _usable_stage_paragraphs(paragraphs, limit=2, prefer_tail=True),
        [
            [risks, contradiction.manifestation, failure.trigger],
            [
                failure.manifestation,
                failure.supportive_reframe,
                narrative_input.maturity_levels.low.body,
                *_maturity_parts(narrative_input),
                narrative_input.inner_mechanism.summary,
            ],
        ],
        max_paragraphs=3,
    )


def _compose_sexuality_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    contradiction = narrative_input.contradictions[0]
    failure_mode = narrative_input.failure_modes[0]
    intimacy_claims = [item.claim for item in narrative_input.sexuality_patterns[:2]]
    return _section_body(
        _usable_stage_paragraphs(paragraphs, limit=2, prefer_tail=True),
        [
            [*intimacy_claims, contradiction.manifestation, contradiction.mature_expression],
            [
                failure_mode.manifestation,
                failure_mode.supportive_reframe,
                narrative_input.relationship_patterns[0].claim if narrative_input.relationship_patterns else "",
                narrative_input.maturity_levels.medium.body,
                narrative_input.inner_mechanism.summary,
                *_maturity_parts(narrative_input),
            ],
        ],
        max_paragraphs=3,
    )


def _compose_hero_body(
    identity_paragraphs: list[str],
    emotional_paragraphs: list[str],
    relationship_paragraphs: list[str],
    narrative_input: NarrativeInput,
) -> str:
    identity = _join_inline(_usable_stage_paragraphs(identity_paragraphs, limit=2))
    emotional = _join_inline(_usable_stage_paragraphs(emotional_paragraphs, limit=2))
    relationships = _join_inline(_usable_stage_paragraphs(relationship_paragraphs, limit=2))
    dominant = narrative_input.dominants[0].body
    mechanism = narrative_input.inner_mechanism.summary
    scenario = narrative_input.house_scenarios[0].manifestation
    mature = narrative_input.contradictions[0].mature_expression
    maturity = narrative_input.maturity_levels.medium.body
    return _body_from_paragraphs(
        [
            _join_inline([identity, dominant, mechanism]),
            _join_inline([emotional, relationships, scenario, mature, maturity]),
        ]
    )


def _usable_stage_paragraphs(
    paragraphs: Sequence[str],
    *,
    limit: int,
    reject_career: bool = False,
    prefer_tail: bool = False,
) -> list[str]:
    selected = [
        paragraph
        for paragraph in paragraphs
        if _is_stage_paragraph_usable(paragraph) and not (reject_career and _contains_career_language(paragraph))
    ]
    selected = selected[-limit:] if prefer_tail else selected[:limit]
    return [_strip_mechanical_prefixes(paragraph) for paragraph in selected]


def _section_body(
    stage_paragraphs: Sequence[str],
    support_groups: Sequence[Sequence[str]],
    *,
    max_paragraphs: int,
) -> str:
    paragraphs = [_join_inline(stage_paragraphs)] if stage_paragraphs else []
    paragraphs.extend(_join_inline(group) for group in support_groups)
    return _body_from_paragraphs(paragraphs[:max_paragraphs])


def _join_inline(parts: Iterable[str]) -> str:
    return " ".join(_dedupe_parts(_strip_mechanical_prefixes(part) for part in parts))


def _body_from_paragraphs(paragraphs: Iterable[str]) -> str:
    return "\n\n".join(_dedupe_parts(paragraphs))


def _strip_mechanical_prefixes(text: str) -> str:
    return re.sub(r"(?m)(^|(?<=[.!?])\s+)(?:Механизм|Риск|Зрелая форма):\s*", r"\1", text.strip())


def _shared_depth_parts(narrative_input: NarrativeInput) -> list[str]:
    return [
        narrative_input.house_scenarios[0].manifestation,
        narrative_input.house_scenarios[0].shadow,
        narrative_input.house_scenarios[0].mature_expression,
        narrative_input.maturity_levels.low.body,
        narrative_input.maturity_levels.medium.body,
        narrative_input.maturity_levels.high.body,
    ]


def _maturity_parts(narrative_input: NarrativeInput) -> list[str]:
    return [
        narrative_input.maturity_levels.low.body,
        narrative_input.maturity_levels.medium.body,
        narrative_input.maturity_levels.high.body,
    ]


def _join_body(parts: Iterable[str]) -> str:
    return " ".join(_dedupe_parts(parts))


def _substantial_body(parts: Sequence[str]) -> str:
    return _join_body(parts)


def _dedupe_parts(parts: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for part in parts:
        text = part.strip()
        if not text:
            continue
        key = re.sub(r"\s+", " ", text.casefold())
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def _evidence_claim(body: str) -> str:
    return body


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
    evidence_notes = [EvidenceNote(claim=_evidence_claim(body), fact_ids=list(evidence_ids))] if evidence_ids else []
    return NarrativeSection(
        id=section_id,
        title=_SECTION_TITLES[section_id],
        body=body,
        bullets=[],
        evidence_notes=evidence_notes,
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
