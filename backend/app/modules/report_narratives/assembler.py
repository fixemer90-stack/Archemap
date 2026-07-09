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
                allowed_fact_ids=_allowed_fact_ids(narrative_input),
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
    hero = narrative_input_to_hero(
        narrative_input,
        hero_body,
        _select_valid_evidence_ids(
            identity.evidence_ids,
            allowed_fact_ids,
            fallback_ids=_claim_evidence_ids(narrative_input.strengths),
        ),
    )
    sections = _dedupe_visible_sections(hero, sections, narrative_input)
    final_summary = _dedupe_final_summary(
        _compose_final_summary_body(development.paragraphs, house_scenarios.paragraphs, final_check, narrative_input),
        hero,
        sections,
        fallback=narrative_input.maturity_levels.high.body,
        narrative_input=narrative_input,
    )

    return SelfNarrative(
        title=title,
        hero=hero,
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
        final_summary=final_summary,
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
    steps = [step.body for step in narrative_input.inner_mechanism.steps]
    contradiction = narrative_input.contradictions[0]
    return _section_body(
        _usable_stage_paragraphs(paragraphs),
        [
            [dominant.body, narrative_input.inner_mechanism.summary, *steps],
            [contradiction.tension, contradiction.mature_expression],
        ]
    )


def _compose_emotional_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    contradiction = narrative_input.contradictions[0].manifestation
    risk = narrative_input.failure_modes[0]
    return _section_body(
        _usable_stage_paragraphs(paragraphs),
        [
            [narrative_input.key_aspects[0].meaning if narrative_input.key_aspects else "", contradiction],
            [risk.trigger, risk.manifestation, risk.supportive_reframe],
        ]
    )


def _compose_world_perception_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    scenario = narrative_input.house_scenarios[0]
    facts = [fact.meaning for fact in narrative_input.key_facts]
    return _section_body(
        _usable_stage_paragraphs(paragraphs),
        [
            [scenario.need, scenario.manifestation, scenario.shadow, scenario.mature_expression],
            [*facts, narrative_input.inner_mechanism.summary],
        ]
    )


def _compose_relationships_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    claims = [item.claim for item in narrative_input.relationship_patterns]
    contradiction = narrative_input.contradictions[1]
    failure = narrative_input.failure_modes[2]
    return _section_body(
        _usable_stage_paragraphs(paragraphs),
        [
            [*claims, contradiction.tension, contradiction.manifestation, contradiction.mature_expression],
            [failure.trigger, failure.manifestation, failure.supportive_reframe],
        ]
    )


def _compose_development_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    recommendation = " ".join(item.claim for item in narrative_input.development_recommendations)
    failure = narrative_input.failure_modes[0]
    contradiction = narrative_input.contradictions[0]
    return _section_body(
        _usable_stage_paragraphs(paragraphs, reject_career=True),
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
        ]
    )


def _compose_strengths_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    strengths = "; ".join(item.claim for item in narrative_input.strengths)
    maturity = narrative_input.maturity_levels.high.body
    high_note = " ".join(
        part
        for note in narrative_input.maturity_levels.high.evidence_notes
        for part in (note.claim, note.interpretation or "")
        if part
    )
    return _section_body(
        _usable_stage_paragraphs(paragraphs),
        [
            [strengths, maturity, high_note],
            [
                narrative_input.inner_mechanism.steps[1].body,
                narrative_input.contradictions[0].mature_expression,
            ],
        ]
    )


def _compose_vulnerabilities_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    risks = "; ".join(item.claim for item in narrative_input.risks)
    failure = narrative_input.failure_modes[0]
    contradiction = narrative_input.contradictions[0]
    return _section_body(
        _usable_stage_paragraphs(paragraphs, prefer_tail=True),
        [
            [risks, contradiction.manifestation, failure.trigger],
            [
                failure.manifestation,
                failure.supportive_reframe,
                narrative_input.maturity_levels.low.body,
                *_maturity_parts(narrative_input),
                narrative_input.inner_mechanism.summary,
            ],
        ]
    )


def _compose_sexuality_body(paragraphs: list[str], narrative_input: NarrativeInput) -> str:
    intimacy_claims = [item.claim for item in narrative_input.sexuality_patterns]
    return _section_body(
        [],
        [
            [*intimacy_claims],
            [
                "Близость здесь лучше раскрывается через прямое проговаривание желания, темпа и границ, а не через повторение общей динамики отношений.",
                "Так сексуальность остаётся отдельной темой телесного доверия и выбранного ритма, не дублируя раздел о партнёрстве.",
            ],
        ]
    )


def _compose_hero_body(
    identity_paragraphs: list[str],
    emotional_paragraphs: list[str],
    relationship_paragraphs: list[str],
    narrative_input: NarrativeInput,
) -> str:
    identity = _compact_stage_summary(_usable_stage_paragraphs(identity_paragraphs))
    emotional = _compact_stage_summary(_usable_stage_paragraphs(emotional_paragraphs))
    relationships = _compact_stage_summary(_usable_stage_paragraphs(relationship_paragraphs))

    first_paragraph = _join_inline(
        [
            identity,
            _compact_stage_summary([narrative_input.dominants[0].body]),
        ]
    )
    second_paragraph = _join_inline(
        [
            emotional,
            relationships,
            _compact_stage_summary([narrative_input.contradictions[0].mature_expression]),
        ]
    )

    return _body_from_paragraphs([first_paragraph, second_paragraph])


def _usable_stage_paragraphs(
    paragraphs: Sequence[str],
    *,
    reject_career: bool = False,
    prefer_tail: bool = False,
) -> list[str]:
    selected = [
        paragraph
        for paragraph in paragraphs
        if _is_stage_paragraph_usable(paragraph) and not (reject_career and _contains_career_language(paragraph))
    ]
    if prefer_tail:
        selected = list(reversed(selected))
    return [_strip_mechanical_prefixes(paragraph) for paragraph in selected]


def _section_body(
    stage_paragraphs: Sequence[str],
    support_groups: Sequence[Sequence[str]],
) -> str:
    paragraphs = [_join_inline(stage_paragraphs)] if stage_paragraphs else []
    paragraphs.extend(_join_inline(group) for group in support_groups)
    return _body_from_paragraphs(paragraphs)


def _join_inline(parts: Iterable[str]) -> str:
    return " ".join(_dedupe_parts(_strip_mechanical_prefixes(part) for part in parts))


def _compact_stage_summary(parts: Sequence[str]) -> str:
    """Preserve provider text without sentence-count truncation."""
    return _join_inline(parts)


def _non_question_text(text: str) -> str:
    return "" if text.strip().endswith("?") else text


def _body_from_paragraphs(paragraphs: Iterable[str]) -> str:
    return "\n\n".join(_dedupe_parts(paragraphs))


def _compose_final_summary_body(
    development_paragraphs: list[str],
    house_scenario_paragraphs: list[str],
    final_check: AssemblyCheck,
    narrative_input: NarrativeInput,
) -> str:
    """Build a substantial closing synthesis without reusing full section bodies."""
    dominant = narrative_input.dominants[0]
    mechanism_steps = narrative_input.inner_mechanism.steps
    primary_relationship = next(iter(narrative_input.relationship_patterns), None)
    primary_development = next(iter(narrative_input.development_recommendations), None)
    primary_scenario = narrative_input.house_scenarios[0]
    primary_failure = narrative_input.failure_modes[0]
    primary_contradiction = narrative_input.contradictions[0]

    stage_tail = _non_question_text(
        _compact_stage_summary(
            _usable_stage_paragraphs(development_paragraphs, prefer_tail=True)
        )
    )
    house_tail = _non_question_text(
        _compact_stage_summary(
            _usable_stage_paragraphs(house_scenario_paragraphs, prefer_tail=True)
        )
    )
    tone_note = _non_question_text(_compact_stage_summary(final_check.tone_notes))

    paragraphs = [
        _join_inline(
            [
                f"Финальный вывод здесь не в одном ярлыке, а в повторяющемся способе сборки: «{dominant.title}» задаёт главный фильтр, через который вы сначала ищете смысловую опору, затем проверяете её в живом контакте и только после этого переводите внутренний импульс в действие.",
                f"Поэтому сильная сторона отчёта — не отдельная черта, а связка шагов: {mechanism_steps[0].title.lower()}, {mechanism_steps[1].title.lower()} и {mechanism_steps[2].title.lower()}.",
            ]
        ),
        _join_inline(
            [
                f"В жизненных сценариях особенно важна тема «{primary_scenario.title}»: она показывает, где этот механизм становится не теорией, а повторяющимся выбором, реакцией и способом держать направление.",
                stage_tail,
                house_tail,
                primary_relationship.claim if primary_relationship else "В отношениях это требует не формальной совместимости, а ясного ритма контакта, доверия и права не терять собственную позицию рядом с другим человеком.",
            ]
        ),
        _join_inline(
            [
                f"Практический смысл отчёта — замечать момент, когда включается старый риск: {primary_failure.trigger.lower()}",
                f"В этот момент важно не усиливать давление на себя, а выбрать зрелую форму: {primary_failure.supportive_reframe.lower()}",
                f"Так напряжение «{primary_contradiction.title.lower()}» превращается не в стопор, а в навык саморегуляции.",
                primary_development.claim if primary_development else "Следующий шаг лучше делать не рывком, а через маленькое устойчивое действие, которое возвращает ясность и контакт с реальностью.",
                tone_note,
            ]
        ),
    ]
    return _body_from_paragraphs(paragraphs)


def _dedupe_visible_sections(
    hero: HeroSection,
    sections: Sequence[NarrativeSection],
    narrative_input: NarrativeInput,
) -> list[NarrativeSection]:
    """Remove exact repeated sentences across visible narrative blocks.

    The staged assembler intentionally reuses deterministic insights across sections, but repeating the same full
    sentence in many blocks makes the final report feel padded. Keep the first visible occurrence, then remove later
    exact sentence repeats while preserving paragraph rhythm and evidence notes.
    """
    deduped: list[NarrativeSection] = []
    seen: set[str] = set()
    for section in sections:
        body = _ensure_section_quality(section.id, section.body, narrative_input, seen)
        seen.update(_sentence_keys(body))
        deduped.append(section.model_copy(update={"body": body or section.body}))
    return deduped


def _ensure_section_quality(
    section_id: str,
    body: str,
    narrative_input: NarrativeInput,
    seen: set[str],
) -> str:
    """Restore key quality markers when sentence de-duplication removes shared support prose."""
    additions: list[str] = []
    lowered = body.casefold()
    if section_id == "main_formula":
        if not (_has_lived_marker(lowered) and _has_risk_marker(lowered) and _has_mature_marker(lowered)):
            additions.append(
                "В ситуации выбора это проявляется так: сначала вы ищете понятную опору, потом замечаете риск внутреннего напряжения и переводите его в более зрелую, устойчивую форму действия."
            )
        if not _has_lived_marker(lowered):
            additions.append(
                "В ситуации выбора это проявляется очень конкретно: сначала вы ищете понятную опору, потом проверяете, как она выдерживает контакт с другим человеком."
            )
        if not _has_risk_marker(lowered):
            additions.append(
                "Риск здесь — застрять в напряжении между внутренней точностью и необходимостью действовать до полной уверенности."
            )
        if not _has_mature_marker(lowered):
            additions.append(narrative_input.contradictions[0].mature_expression)
    elif section_id == "development":
        if not (
            _has_mechanism_marker(lowered)
            and _has_lived_marker(lowered)
            and _has_risk_marker(lowered)
            and _has_mature_marker(lowered)
        ):
            additions.append(
                "Практически это означает: сначала заметить механизм напряжения, затем назвать риск старого цикла и выбрать более зрелую, устойчивую форму действия."
            )
        if not _has_risk_marker(lowered):
            additions.append(narrative_input.failure_modes[0].trigger)
        if not _has_mature_marker(lowered):
            additions.append(narrative_input.failure_modes[0].supportive_reframe)
    elif section_id == "relationships":
        if not (_has_lived_marker(lowered) and _has_risk_marker(lowered)):
            additions.extend(item.claim for item in narrative_input.relationship_patterns)
            additions.extend(
                [
                    narrative_input.contradictions[1].tension,
                    narrative_input.contradictions[1].manifestation,
                    narrative_input.contradictions[1].mature_expression,
                    narrative_input.failure_modes[2].trigger,
                    narrative_input.failure_modes[2].manifestation,
                    narrative_input.failure_modes[2].supportive_reframe,
                ]
            )
    elif section_id == "sexuality":
        if not body.strip():
            additions.extend(item.claim for item in narrative_input.sexuality_patterns)
    if not additions:
        return body
    addition_text = _dedupe_text_against(_join_inline(additions), seen)
    return _append_to_last_paragraph(body, addition_text) if addition_text else body


def _append_to_last_paragraph(body: str, addition: str) -> str:
    if not body:
        return addition
    paragraphs = body.split("\n\n")
    paragraphs[-1] = _join_inline([paragraphs[-1], addition])
    return "\n\n".join(paragraphs)


def _has_lived_marker(text: str) -> bool:
    return any(marker in text for marker in ("когда ", "в ситуации", "сначала", "потом", "замечаете", "выбираете"))


def _has_mechanism_marker(text: str) -> bool:
    return any(marker in text for marker in ("механизм", "паттерн", "разворач", "сначала", "затем"))


def _has_risk_marker(text: str) -> bool:
    return any(marker in text for marker in ("риск", "напряж", "давлен", "слишком", "уязв", "цикл"))


def _has_mature_marker(text: str) -> bool:
    return any(marker in text for marker in ("зрел", "устойчив", "полезно", "способность"))


def _dedupe_final_summary(
    summary: str,
    hero: HeroSection,
    sections: Sequence[NarrativeSection],
    *,
    fallback: str,
    narrative_input: NarrativeInput,
) -> str:
    seen = _sentence_keys(hero.body)
    for section in sections:
        seen.update(_sentence_keys(section.body))
    deduped = _dedupe_text_against(summary, seen)
    if _is_usable_final_summary(deduped):
        return deduped

    expansion = _final_summary_repair(deduped, narrative_input)
    repaired = _dedupe_text_against(expansion, seen)
    if _is_usable_final_summary(repaired):
        return repaired

    fallback_seen = _sentence_keys(hero.body)
    for section in sections:
        fallback_seen.update(_sentence_keys(section.body))
    repaired_fallback = _dedupe_text_against(_join_inline([deduped, fallback, expansion]), fallback_seen)
    return (
        repaired_fallback
        if _is_usable_final_summary(repaired_fallback)
        else expansion
    )


def _is_usable_final_summary(summary: str) -> bool:
    return bool(summary.strip()) and not summary.strip().endswith("?")


def _final_summary_repair(prefix: str, narrative_input: NarrativeInput) -> str:
    dominant = narrative_input.dominants[0]
    scenario = narrative_input.house_scenarios[0]
    relationship = next(iter(narrative_input.relationship_patterns), None)
    development = next(iter(narrative_input.development_recommendations), None)
    failure = narrative_input.failure_modes[0]
    maturity = narrative_input.maturity_levels.high
    paragraphs = [prefix] if prefix and not prefix.strip().endswith("?") else []
    paragraphs.extend(
        [
            _join_inline(
                [
                    f"Если собрать отчёт в практический итог, главная опора — «{dominant.title}»: она показывает, как вы превращаете разрозненные впечатления в личную систему координат.",
                    "Это не короткая характеристика, а рабочий маршрут: заметить внутренний фильтр, проверить его в ситуации и выбрать действие, которое не разрушает вашу устойчивость.",
                ]
            ),
            _join_inline(
                [
                    f"Тема «{scenario.title}» показывает, где этот маршрут чаще всего становится видимым в жизни.",
                    relationship.claim if relationship else "В отношениях важны доверие, ясный темп сближения и способность не терять собственную позицию рядом с другим человеком.",
                    "Поэтому финальный смысл Self-разбора — не только понять себя, но и увидеть, в каких местах контакт, выбор и внутренняя опора требуют особенно внимательного обращения.",
                ]
            ),
            _join_inline(
                [
                    f"Главный риск включается там, где появляется {failure.trigger.lower()}",
                    f"Зрелая стратегия — {failure.supportive_reframe.lower()}",
                    development.claim if development else "Следующий шаг лучше делать через небольшой устойчивый эксперимент, а не через попытку сразу идеально пересобрать весь сценарий.",
                    maturity.body,
                ]
            ),
        ]
    )
    return _body_from_paragraphs(paragraphs)


def _dedupe_text_against(text: str, seen: set[str]) -> str:
    paragraphs: list[str] = []
    accepted_keys: set[str] = set()
    for paragraph in re.split(r"\n\s*\n", text):
        kept: list[str] = []
        for sentence in _split_sentences(paragraph):
            key = _sentence_key(sentence)
            if key and key in seen:
                continue
            if key:
                accepted_keys.add(key)
            kept.append(sentence.strip())
        joined = " ".join(part for part in kept if part)
        if joined:
            paragraphs.append(joined)
    seen.update(accepted_keys)
    return _body_from_paragraphs(paragraphs)


def _sentence_keys(text: str) -> set[str]:
    return {key for sentence in _split_sentences(text) if (key := _sentence_key(sentence))}


def _sentence_key(sentence: str) -> str | None:
    key = re.sub(r"\s+", " ", sentence.strip().casefold())
    return key or None


def _split_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


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
    lowered = stripped.casefold()
    if any(
        marker in lowered
        for marker in (
            "требуют дополнительной сборки",
            "требует дополнительной сборки",
            "дополнительной сборки",
        )
    ):
        return False
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
    for claim in claims:
        evidence_ids.extend(getattr(claim, "evidence_ids", []))
    return evidence_ids


def _scenario_evidence_ids(narrative_input: NarrativeInput) -> list[str]:
    evidence_ids: list[str] = []
    for scenario in narrative_input.house_scenarios:
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
    return deduped_fallback
