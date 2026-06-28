# ruff: noqa: RUF001
"""Deterministic validators for structured self narratives."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from app.modules.report_narratives.exceptions import (
    NarrativeRecoveryAction,
    NarrativeValidationError,
)
from app.modules.report_narratives.schemas import (
    EvidenceBackedClaim,
    EvidenceNote,
    NarrativeInput,
    SelfNarrative,
)

_ALLOWED_PLANET_TOKENS = {
    "солнце",
    "луна",
    "меркурий",
    "венера",
    "марс",
    "юпитер",
    "сатурн",
    "уран",
    "нептун",
    "плутон",
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
}
_ALLOWED_SIGN_TOKENS = {
    "овне",
    "тельце",
    "близнецах",
    "раке",
    "льве",
    "деве",
    "весах",
    "скорпионе",
    "стрельце",
    "козероге",
    "водолее",
    "рыбах",
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
}
_ALLOWED_ASPECT_TOKENS = {
    "соединение",
    "оппозиция",
    "тригон",
    "квадрат",
    "секстиль",
    "квинконс",
    "conjunction",
    "opposition",
    "trine",
    "square",
    "sextile",
    "quincunx",
}
_CAREER_MARKERS = (
    "професси",
    "карьерн",
    "деньг",
    "доход",
    "зарплат",
    "финансов",
    "вакан",
    "собесед",
    "управлен",
    "менедж",
    "должност",
)
_FORBIDDEN_LANGUAGE_MARKERS = (
    "диагноз",
    "психопат",
    "шизофр",
    "неизбеж",
    "обреч",
    "сужден",
    "предначертан",
    "гарантир",
    "половому акту",
    "половой акт",
    "проникнов",
    "эякуляц",
    "генитал",
    "оргазм",
)
_SECTION_ID_PATTERN = re.compile(r"\b([1-9]|1[0-2])\s+доме?\b", re.IGNORECASE)
_SOCTYPE_PATTERN = re.compile(r"\b[ЕЛСИ]{3}\b|\b[A-Z]{3}\b")


def validate_self_narrative(
    narrative: SelfNarrative | dict[str, Any],
    narrative_input: NarrativeInput | dict[str, Any],
) -> list[NarrativeValidationError]:
    """Validate structured Self narrative against deterministic input."""
    validated_input = NarrativeInput.model_validate(narrative_input)
    candidate = narrative if isinstance(narrative, SelfNarrative) else SelfNarrative.model_construct(**narrative)

    errors: list[NarrativeValidationError] = []
    errors.extend(_validate_required_sections(candidate, validated_input))
    errors.extend(_validate_dominants(candidate))
    errors.extend(_validate_inner_mechanism(candidate))
    errors.extend(_validate_house_scenarios(candidate))
    errors.extend(_validate_calibration_questions(candidate))
    errors.extend(_validate_contradictions(candidate))
    errors.extend(_validate_failure_modes(candidate))
    errors.extend(_validate_maturity_levels(candidate))
    errors.extend(_validate_career_cta(candidate))
    errors.extend(_validate_evidence_refs(candidate, validated_input))
    errors.extend(_validate_career_boundaries(candidate))
    errors.extend(_validate_forbidden_language(candidate))
    errors.extend(_validate_domain_terms(candidate, validated_input))
    return errors


def choose_narrative_recovery_action(
    errors: list[NarrativeValidationError],
    repair_attempts_used: int,
    llm_available: bool,
) -> NarrativeRecoveryAction:
    """Apply the MVP repair/fallback policy for invalid narrative output."""
    if not llm_available:
        return "fallback"
    if not errors:
        return "repair"
    if any(not error.recoverable for error in errors):
        return "narrative_failed"
    if all(error.recoverable for error in errors) and repair_attempts_used < 1:
        return "repair"
    if all(error.recoverable for error in errors):
        return "fallback"
    return "narrative_failed"


def _validate_required_sections(
    narrative: SelfNarrative,
    narrative_input: NarrativeInput,
) -> list[NarrativeValidationError]:
    actual_ids = [section.id for section in getattr(narrative, "sections", []) or []]
    expected_ids = list(narrative_input.product_boundaries.allowed_sections)
    if actual_ids == expected_ids:
        return []
    return [
        NarrativeValidationError(
            code="invalid_section_order",
            message="Narrative sections must match the required Self section set and order.",
            location="sections",
            recoverable=True,
        )
    ]


def _validate_dominants(narrative: SelfNarrative) -> list[NarrativeValidationError]:
    dominants = getattr(narrative, "dominants", None)
    if not dominants:
        return [
            NarrativeValidationError(
                code="missing_dominants",
                message="Self narrative must include evidence-backed dominants.",
                location="dominants",
                recoverable=True,
            )
        ]

    errors: list[NarrativeValidationError] = []
    for index, dominant in enumerate(dominants):
        if not getattr(dominant, "evidence_ids", None):
            errors.append(
                NarrativeValidationError(
                    code="dominant_missing_evidence",
                    message="Every dominant must reference deterministic evidence ids.",
                    location=f"dominants[{index}].evidence_ids",
                    recoverable=True,
                )
            )
    return errors


def _validate_inner_mechanism(narrative: SelfNarrative) -> list[NarrativeValidationError]:
    inner_mechanism = getattr(narrative, "inner_mechanism", None)
    steps = getattr(inner_mechanism, "steps", None) if inner_mechanism is not None else None
    if steps is None or not 3 <= len(steps) <= 5:
        return [
            NarrativeValidationError(
                code="invalid_inner_mechanism",
                message="Self narrative inner_mechanism must contain 3-5 steps.",
                location="inner_mechanism.steps",
                recoverable=True,
            )
        ]

    errors: list[NarrativeValidationError] = []
    for index, step in enumerate(steps):
        if not getattr(step, "evidence_ids", None):
            errors.append(
                NarrativeValidationError(
                    code="mechanism_step_missing_evidence",
                    message="Every inner mechanism step must reference deterministic evidence ids.",
                    location=f"inner_mechanism.steps[{index}].evidence_ids",
                    recoverable=True,
                )
            )
    return errors


def _validate_house_scenarios(narrative: SelfNarrative) -> list[NarrativeValidationError]:
    scenarios = getattr(narrative, "house_scenarios", None)
    if not scenarios:
        return [
            NarrativeValidationError(
                code="missing_house_scenarios",
                message="Self narrative must include house scenario interpretations.",
                location="house_scenarios",
                recoverable=True,
            )
        ]

    errors: list[NarrativeValidationError] = []
    for index, scenario in enumerate(scenarios):
        if not getattr(scenario, "manifestation", "").strip():
            errors.append(
                NarrativeValidationError(
                    code="invalid_house_scenario",
                    message="Every house scenario must include a manifestation.",
                    location=f"house_scenarios[{index}].manifestation",
                    recoverable=True,
                )
            )
        if not getattr(scenario, "shadow", "").strip():
            errors.append(
                NarrativeValidationError(
                    code="invalid_house_scenario",
                    message="Every house scenario must include a shadow/risk.",
                    location=f"house_scenarios[{index}].shadow",
                    recoverable=True,
                )
            )
        if not getattr(scenario, "evidence_ids", None):
            errors.append(
                NarrativeValidationError(
                    code="invalid_house_scenario",
                    message="Every house scenario must reference deterministic evidence ids.",
                    location=f"house_scenarios[{index}].evidence_ids",
                    recoverable=True,
                )
            )
    return errors


def _validate_calibration_questions(narrative: SelfNarrative) -> list[NarrativeValidationError]:
    calibration_questions = getattr(narrative, "calibration_questions", None)
    if not calibration_questions:
        return [
            NarrativeValidationError(
                code="missing_calibration_questions",
                message="Self narrative must include 5-7 calibration questions.",
                location="calibration_questions",
                recoverable=True,
            )
        ]

    errors: list[NarrativeValidationError] = []
    for index, question in enumerate(calibration_questions):
        if not getattr(question, "question", "").strip().endswith("?"):
            errors.append(
                NarrativeValidationError(
                    code="invalid_calibration_question",
                    message="Every calibration question must be phrased as a question.",
                    location=f"calibration_questions[{index}].question",
                    recoverable=True,
                )
            )
        if not getattr(question, "evidence_ids", None):
            errors.append(
                NarrativeValidationError(
                    code="invalid_calibration_question",
                    message="Every calibration question must reference deterministic evidence ids.",
                    location=f"calibration_questions[{index}].evidence_ids",
                    recoverable=True,
                )
            )
    return errors


def _validate_contradictions(narrative: SelfNarrative) -> list[NarrativeValidationError]:
    contradictions = getattr(narrative, "contradictions", None)
    if contradictions is None or not 3 <= len(contradictions) <= 5:
        return [
            NarrativeValidationError(
                code="invalid_contradictions",
                message="Self narrative must include 3-5 central contradictions.",
                location="contradictions",
                recoverable=True,
            )
        ]

    errors: list[NarrativeValidationError] = []
    for index, contradiction in enumerate(contradictions):
        if not getattr(contradiction, "mature_expression", "").strip():
            errors.append(
                NarrativeValidationError(
                    code="invalid_contradiction",
                    message="Every contradiction must include a mature expression.",
                    location=f"contradictions[{index}].mature_expression",
                    recoverable=True,
                )
            )
        if not getattr(contradiction, "evidence_ids", None):
            errors.append(
                NarrativeValidationError(
                    code="invalid_contradiction",
                    message="Every contradiction must reference deterministic evidence ids.",
                    location=f"contradictions[{index}].evidence_ids",
                    recoverable=True,
                )
            )
    return errors


def _validate_failure_modes(narrative: SelfNarrative) -> list[NarrativeValidationError]:
    failure_modes = getattr(narrative, "failure_modes", None)
    if failure_modes is None or not 3 <= len(failure_modes) <= 5:
        return [
            NarrativeValidationError(
                code="invalid_failure_modes",
                message="Self narrative must include 3-5 concrete failure modes.",
                location="failure_modes",
                recoverable=True,
            )
        ]

    errors: list[NarrativeValidationError] = []
    for index, failure_mode in enumerate(failure_modes):
        if not getattr(failure_mode, "supportive_reframe", "").strip():
            errors.append(
                NarrativeValidationError(
                    code="invalid_failure_mode",
                    message="Every failure mode must include a supportive reframe.",
                    location=f"failure_modes[{index}].supportive_reframe",
                    recoverable=True,
                )
            )
        if not getattr(failure_mode, "evidence_ids", None):
            errors.append(
                NarrativeValidationError(
                    code="invalid_failure_mode",
                    message="Every failure mode must reference deterministic evidence ids.",
                    location=f"failure_modes[{index}].evidence_ids",
                    recoverable=True,
                )
            )
    return errors


def _validate_maturity_levels(narrative: SelfNarrative) -> list[NarrativeValidationError]:
    maturity_levels = getattr(narrative, "maturity_levels", None)
    if maturity_levels is None:
        return [
            NarrativeValidationError(
                code="missing_maturity_levels",
                message="Self narrative must include low / medium / high maturity levels.",
                location="maturity_levels",
                recoverable=True,
            )
        ]

    errors: list[NarrativeValidationError] = []
    for band_name in ("low", "medium", "high"):
        band = getattr(maturity_levels, band_name, None)
        if band is None or not getattr(band, "body", "").strip():
            errors.append(
                NarrativeValidationError(
                    code="invalid_maturity_levels",
                    message="Every maturity band must include explanatory text.",
                    location=f"maturity_levels.{band_name}.body",
                    recoverable=True,
                )
            )
            continue
        if not getattr(band, "evidence_ids", None):
            errors.append(
                NarrativeValidationError(
                    code="invalid_maturity_levels",
                    message="Every maturity band must reference deterministic evidence ids.",
                    location=f"maturity_levels.{band_name}.evidence_ids",
                    recoverable=True,
                )
            )
    return errors


def _validate_career_cta(narrative: SelfNarrative) -> list[NarrativeValidationError]:
    career_cta = getattr(narrative, "career_cta", None)
    if career_cta is not None:
        return []
    return [
        NarrativeValidationError(
            code="missing_career_cta",
            message="Self narrative must include career_cta.",
            location="career_cta",
            recoverable=True,
        )
    ]


def _validate_evidence_refs(
    narrative: SelfNarrative,
    narrative_input: NarrativeInput,
) -> list[NarrativeValidationError]:
    allowed_fact_ids = _allowed_fact_ids(narrative_input)
    errors: list[NarrativeValidationError] = []
    for location, note in _iter_evidence_notes(narrative):
        evidence_groups = [
            ("fact_ids", note.fact_ids),
            ("limitation_fact_ids", note.limitation_fact_ids),
        ]
        for field_name, fact_ids in evidence_groups:
            unknown_fact_ids = [fact_id for fact_id in fact_ids if fact_id not in allowed_fact_ids]
            if unknown_fact_ids:
                errors.append(
                    NarrativeValidationError(
                        code="unknown_evidence_ref",
                        message=f"Narrative references unknown fact ids: {', '.join(unknown_fact_ids)}.",
                        location=f"{location}.{field_name}",
                        recoverable=True,
                    )
                )
    return errors


def _validate_career_boundaries(narrative: SelfNarrative) -> list[NarrativeValidationError]:
    errors: list[NarrativeValidationError] = []
    for location, text in _iter_non_cta_texts(narrative):
        lowered = text.lower()
        if any(marker in lowered for marker in _CAREER_MARKERS):
            errors.append(
                NarrativeValidationError(
                    code="career_boundary_violation",
                    message="Self narrative contains career deep-dive language outside career_cta.",
                    location=location,
                    recoverable=True,
                )
            )
    return errors


def _validate_forbidden_language(narrative: SelfNarrative) -> list[NarrativeValidationError]:
    errors: list[NarrativeValidationError] = []
    for location, text in _iter_all_texts(narrative):
        lowered = text.lower()
        if any(marker in lowered for marker in _FORBIDDEN_LANGUAGE_MARKERS):
            errors.append(
                NarrativeValidationError(
                    code="forbidden_language",
                    message="Narrative contains forbidden fatalistic, medical, diagnostic, or graphic language.",
                    location=location,
                    recoverable=True,
                )
            )
    return errors


def _validate_domain_terms(
    narrative: SelfNarrative,
    narrative_input: NarrativeInput,
) -> list[NarrativeValidationError]:
    allowed_terms = _allowed_domain_terms(narrative_input)
    errors: list[NarrativeValidationError] = []

    for location, text in _iter_non_cta_texts(narrative):
        lowered = text.lower()
        unsupported_tokens = [token for token in _tokens_from_text(lowered) if token not in allowed_terms]
        unsupported_houses = [house for house in _SECTION_ID_PATTERN.findall(lowered) if house not in allowed_terms]
        unsupported_types = [
            soc_type for soc_type in _SOCTYPE_PATTERN.findall(text) if soc_type.lower() not in allowed_terms
        ]
        unknown = unsupported_tokens + unsupported_houses + unsupported_types
        if unknown:
            errors.append(
                NarrativeValidationError(
                    code="unsupported_domain_term",
                    message=f"Narrative introduces unsupported domain terms: {', '.join(sorted(set(unknown)))}.",
                    location=location,
                    recoverable=True,
                )
            )
    return errors


def _allowed_fact_ids(narrative_input: NarrativeInput) -> set[str]:
    allowed = {fact.id for fact in narrative_input.key_facts}
    allowed.update(fact.id for fact in narrative_input.key_aspects)
    for dominant in narrative_input.dominants:
        allowed.update(dominant.evidence_ids)
    for step in narrative_input.inner_mechanism.steps:
        allowed.update(step.evidence_ids)
    for scenario in narrative_input.house_scenarios:
        allowed.update(scenario.evidence_ids)
        for note in getattr(scenario, "evidence_notes", []) or []:
            allowed.update(note.fact_ids)
            allowed.update(note.limitation_fact_ids)
    for question in narrative_input.calibration_questions:
        allowed.update(question.evidence_ids)
    for contradiction in narrative_input.contradictions:
        allowed.update(contradiction.evidence_ids)
        for note in getattr(contradiction, "evidence_notes", []) or []:
            allowed.update(note.fact_ids)
            allowed.update(note.limitation_fact_ids)
    for failure_mode in narrative_input.failure_modes:
        allowed.update(failure_mode.evidence_ids)
        for note in getattr(failure_mode, "evidence_notes", []) or []:
            allowed.update(note.fact_ids)
            allowed.update(note.limitation_fact_ids)
    for band_name in ("low", "medium", "high"):
        band = getattr(narrative_input.maturity_levels, band_name)
        allowed.update(band.evidence_ids)
        for note in getattr(band, "evidence_notes", []) or []:
            allowed.update(note.fact_ids)
            allowed.update(note.limitation_fact_ids)
    for claim in _iter_claim_groups(narrative_input):
        allowed.update(claim.evidence_ids)
    return allowed


def _allowed_domain_terms(narrative_input: NarrativeInput) -> set[str]:
    allowed: set[str] = set()
    for item in narrative_input.key_facts:
        allowed.update(_tokens_from_text(item.label.lower()))
        allowed.update(_extract_house_terms(item.label))
    for aspect in narrative_input.key_aspects:
        allowed.update(_tokens_from_text(aspect.label.lower()))
        allowed.update(_extract_house_terms(aspect.label))
    allowed.add(narrative_input.socionics.type.lower())
    allowed.add(narrative_input.socionics.type_ru.lower())
    return allowed


def _extract_house_terms(item_label: str) -> set[str]:
    return set(_SECTION_ID_PATTERN.findall(item_label.lower()))


def _iter_claim_groups(narrative_input: NarrativeInput) -> Iterable[EvidenceBackedClaim]:
    for group_name in (
        "strengths",
        "risks",
        "relationship_patterns",
        "sexuality_patterns",
        "development_recommendations",
    ):
        yield from getattr(narrative_input, group_name)


def _iter_evidence_notes(narrative: SelfNarrative) -> Iterable[tuple[str, EvidenceNote]]:
    for index, dominant in enumerate(getattr(narrative, "dominants", []) or []):
        fact_ids = list(getattr(dominant, "evidence_ids", []) or [])
        if fact_ids:
            yield (
                f"dominants[{index}]",
                EvidenceNote(claim=getattr(dominant, "body", ""), fact_ids=fact_ids),
            )
    inner_mechanism = getattr(narrative, "inner_mechanism", None)
    for index, step in enumerate(getattr(inner_mechanism, "steps", []) or []):
        fact_ids = list(getattr(step, "evidence_ids", []) or [])
        if fact_ids:
            yield (
                f"inner_mechanism.steps[{index}]",
                EvidenceNote(claim=getattr(step, "body", ""), fact_ids=fact_ids),
            )
    for index, scenario in enumerate(getattr(narrative, "house_scenarios", []) or []):
        fact_ids = list(getattr(scenario, "evidence_ids", []) or [])
        if fact_ids:
            yield (
                f"house_scenarios[{index}]",
                EvidenceNote(claim=getattr(scenario, "manifestation", ""), fact_ids=fact_ids),
            )
        for note_index, note in enumerate(getattr(scenario, "evidence_notes", []) or []):
            yield (f"house_scenarios[{index}].evidence_notes[{note_index}]", note)
    for index, question in enumerate(getattr(narrative, "calibration_questions", []) or []):
        fact_ids = list(getattr(question, "evidence_ids", []) or [])
        if fact_ids:
            yield (
                f"calibration_questions[{index}]",
                EvidenceNote(claim=getattr(question, "question", ""), fact_ids=fact_ids),
            )
    for index, contradiction in enumerate(getattr(narrative, "contradictions", []) or []):
        fact_ids = list(getattr(contradiction, "evidence_ids", []) or [])
        if fact_ids:
            yield (
                f"contradictions[{index}]",
                EvidenceNote(claim=getattr(contradiction, "manifestation", ""), fact_ids=fact_ids),
            )
        for note_index, note in enumerate(getattr(contradiction, "evidence_notes", []) or []):
            yield (f"contradictions[{index}].evidence_notes[{note_index}]", note)
    for index, failure_mode in enumerate(getattr(narrative, "failure_modes", []) or []):
        fact_ids = list(getattr(failure_mode, "evidence_ids", []) or [])
        if fact_ids:
            yield (
                f"failure_modes[{index}]",
                EvidenceNote(claim=getattr(failure_mode, "manifestation", ""), fact_ids=fact_ids),
            )
        for note_index, note in enumerate(getattr(failure_mode, "evidence_notes", []) or []):
            yield (f"failure_modes[{index}].evidence_notes[{note_index}]", note)
    maturity_levels = getattr(narrative, "maturity_levels", None)
    if maturity_levels is not None:
        for band_name in ("low", "medium", "high"):
            band = getattr(maturity_levels, band_name, None)
            fact_ids = list(getattr(band, "evidence_ids", []) or []) if band is not None else []
            if fact_ids:
                yield (
                    f"maturity_levels.{band_name}",
                    EvidenceNote(claim=getattr(band, "body", ""), fact_ids=fact_ids),
                )
            if band is not None:
                for note_index, note in enumerate(getattr(band, "evidence_notes", []) or []):
                    yield (f"maturity_levels.{band_name}.evidence_notes[{note_index}]", note)
    for index, note in enumerate(narrative.hero.evidence_notes):
        yield (f"hero.evidence_notes[{index}]", note)
    for section_index, section in enumerate(narrative.sections):
        for note_index, note in enumerate(section.evidence_notes):
            yield (f"sections[{section_index}].evidence_notes[{note_index}]", note)


def _iter_non_cta_texts(narrative: SelfNarrative) -> Iterable[tuple[str, str]]:
    yield ("title", narrative.title)
    yield ("hero.title", narrative.hero.title)
    yield ("hero.body", narrative.hero.body)
    for dominant_index, dominant in enumerate(getattr(narrative, "dominants", []) or []):
        yield (f"dominants[{dominant_index}].title", dominant.title)
        yield (f"dominants[{dominant_index}].body", dominant.body)
    inner_mechanism = getattr(narrative, "inner_mechanism", None)
    if inner_mechanism is not None:
        yield ("inner_mechanism.title", inner_mechanism.title)
        yield ("inner_mechanism.summary", inner_mechanism.summary)
        for step_index, step in enumerate(inner_mechanism.steps):
            yield (f"inner_mechanism.steps[{step_index}].title", step.title)
            yield (f"inner_mechanism.steps[{step_index}].body", step.body)
    for scenario_index, scenario in enumerate(getattr(narrative, "house_scenarios", []) or []):
        yield (f"house_scenarios[{scenario_index}].title", scenario.title)
        yield (f"house_scenarios[{scenario_index}].placement", scenario.placement)
        yield (f"house_scenarios[{scenario_index}].need", scenario.need)
        yield (f"house_scenarios[{scenario_index}].manifestation", scenario.manifestation)
        yield (f"house_scenarios[{scenario_index}].shadow", scenario.shadow)
        yield (f"house_scenarios[{scenario_index}].mature_expression", scenario.mature_expression)
    for question_index, question in enumerate(getattr(narrative, "calibration_questions", []) or []):
        yield (f"calibration_questions[{question_index}].question", question.question)
    for contradiction_index, contradiction in enumerate(getattr(narrative, "contradictions", []) or []):
        yield (f"contradictions[{contradiction_index}].title", contradiction.title)
        yield (f"contradictions[{contradiction_index}].tension", contradiction.tension)
        yield (f"contradictions[{contradiction_index}].manifestation", contradiction.manifestation)
        yield (
            f"contradictions[{contradiction_index}].mature_expression",
            contradiction.mature_expression,
        )
    for failure_index, failure_mode in enumerate(getattr(narrative, "failure_modes", []) or []):
        yield (f"failure_modes[{failure_index}].title", failure_mode.title)
        yield (f"failure_modes[{failure_index}].trigger", failure_mode.trigger)
        yield (
            f"failure_modes[{failure_index}].manifestation",
            failure_mode.manifestation,
        )
        yield (
            f"failure_modes[{failure_index}].supportive_reframe",
            failure_mode.supportive_reframe,
        )
    maturity_levels = getattr(narrative, "maturity_levels", None)
    if maturity_levels is not None:
        for band_name in ("low", "medium", "high"):
            band = getattr(maturity_levels, band_name, None)
            if band is None:
                continue
            yield (f"maturity_levels.{band_name}.title", band.title)
            yield (f"maturity_levels.{band_name}.body", band.body)
    yield ("final_summary", narrative.final_summary)
    for section_index, section in enumerate(narrative.sections):
        yield (f"sections[{section_index}].title", section.title)
        yield (f"sections[{section_index}].body", section.body)
        for bullet_index, bullet in enumerate(section.bullets):
            yield (f"sections[{section_index}].bullets[{bullet_index}]", bullet)
        for note_index, note in enumerate(section.evidence_notes):
            yield (f"sections[{section_index}].evidence_notes[{note_index}].claim", note.claim)


def _iter_all_texts(narrative: SelfNarrative) -> Iterable[tuple[str, str]]:
    yield from _iter_non_cta_texts(narrative)
    for bullet_index, bullet in enumerate(narrative.hero.bullets):
        yield (f"hero.bullets[{bullet_index}]", bullet)
    for note_index, note in enumerate(narrative.hero.evidence_notes):
        yield (f"hero.evidence_notes[{note_index}].claim", note.claim)
    career_cta = getattr(narrative, "career_cta", None)
    if career_cta is None:
        return
    yield ("career_cta.title", career_cta.title)
    yield ("career_cta.body", career_cta.body)
    yield ("career_cta.button_label", career_cta.button_label)
    for bullet_index, bullet in enumerate(career_cta.bullets):
        yield (f"career_cta.bullets[{bullet_index}]", bullet)


def _tokens_from_text(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-zA-Zа-яА-ЯёЁ]+", text.lower()))
    return {
        token
        for token in tokens
        if token in _ALLOWED_PLANET_TOKENS or token in _ALLOWED_SIGN_TOKENS or token in _ALLOWED_ASPECT_TOKENS
    }
