"""Pure versioned questionnaire selection, validation, and hashing."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Literal, cast
from uuid import UUID

from app.modules.child.age_resolver import AgeStage

QUESTIONNAIRE_VERSION: Final = "child-questionnaire-mvp-1"
ANSWER_VERSION: Final = "child-answer-mvp-1"
CONTEXT_VERSION: Final = "child-context-mvp-1"
CONSENT_VERSION: Final = "child-consent-mvp-1"


class CatalogValidationError(ValueError):
    """The backend questionnaire catalog is not safe or internally coherent."""


class QuestionCategory(StrEnum):
    CAREGIVER_CONTEXT = "caregiver_context"
    OBSERVATION = "observation"
    PARENT_PREFERENCE = "parent_preference"
    FAMILY_CONSTRAINT = "family_constraint"


class AnswerKind(StrEnum):
    SINGLE_CHOICE = "single_choice"


@dataclass(frozen=True, slots=True)
class QuestionOption:
    code: str
    label_ru: str


@dataclass(frozen=True, slots=True)
class Question:
    key: str
    prompt_ru: str
    category: QuestionCategory
    answer_kind: AnswerKind
    options: tuple[QuestionOption, ...]
    required: bool
    age_stages: tuple[AgeStage, ...]


@dataclass(frozen=True, slots=True)
class AnswerInput:
    question_key: str
    option: str


@dataclass(frozen=True, slots=True)
class ValidatedAnswer:
    question_key: str
    option: str
    category: QuestionCategory


@dataclass(frozen=True, slots=True)
class AdaptiveQuestionPolicy:
    enabled: Literal[False]
    mode: Literal["disabled_deterministic"]
    score_driven: Literal[False]


ADAPTIVE_POLICY = AdaptiveQuestionPolicy(enabled=False, mode="disabled_deterministic", score_driven=False)
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{2,99}$")
_FORBIDDEN = (
    "диагноз",
    "характер",
    "личност",
    "обреч",
    "судьб",
    "агрессив",
    "депресс",
    "пол ребёнка",
    "мальчик",
    "девочка",
)
_KNOWN_STAGES = frozenset(("0-1", "1-3", "3-6", "6-9", "9-12", "12-15", "15-18"))


def _catalog() -> tuple[Question, ...]:
    from app.reference_data.child.questionnaire_v1 import QUESTION_CATALOG

    return QUESTION_CATALOG


def validate_catalog(catalog: tuple[Question, ...]) -> None:
    if not 1 <= len(catalog) <= 12:
        raise CatalogValidationError("Questionnaire catalog must contain 1-12 bounded questions")
    keys: set[str] = set()
    for question in catalog:
        if question.key in keys or not _KEY_RE.fullmatch(question.key):
            raise CatalogValidationError("Question keys must be unique stable identifiers")
        keys.add(question.key)
        if not isinstance(question.category, QuestionCategory):
            raise CatalogValidationError("Question category is unknown")
        if not isinstance(question.answer_kind, AnswerKind):
            raise CatalogValidationError("Answer kind is unknown")
        if not question.prompt_ru or len(question.prompt_ru) > 240:
            raise CatalogValidationError("Question prompt is empty or too long")
        lowered = question.prompt_ru.casefold()
        if any(token in lowered for token in _FORBIDDEN):
            raise CatalogValidationError("Question prompt contains prohibited diagnostic or trait framing")
        stages = tuple(cast(str, value) for value in question.age_stages)
        if not stages or len(stages) != len(set(stages)) or not set(stages) <= _KNOWN_STAGES:
            raise CatalogValidationError("Question contains unknown or duplicate age stages")
        if not 2 <= len(question.options) <= 8:
            raise CatalogValidationError("Choice question must have 2-8 bounded options")
        codes = [option.code for option in question.options]
        if len(codes) != len(set(codes)) or any(not _KEY_RE.fullmatch(code) for code in codes):
            raise CatalogValidationError("Option codes must be unique safe identifiers")
        if any(not option.label_ru or len(option.label_ru) > 120 for option in question.options):
            raise CatalogValidationError("Option labels must be non-empty and bounded")
        option_text = " ".join(option.label_ru.casefold() for option in question.options)
        if any(token in option_text for token in _FORBIDDEN):
            raise CatalogValidationError("Option contains prohibited diagnostic or trait framing")


def questions_for_age_stage(age_stage: AgeStage) -> tuple[Question, ...]:
    catalog = _catalog()
    validate_catalog(catalog)
    selected = tuple(question for question in catalog if age_stage in question.age_stages)
    if not 8 <= len(selected) <= 12:
        raise CatalogValidationError("Every age stage must select 8-12 questions")
    if {question.category for question in selected} != set(QuestionCategory):
        raise CatalogValidationError("Every age stage must include all context families")
    return selected


def validate_answer_set(
    *,
    age_stage: AgeStage,
    answers: tuple[AnswerInput, ...],
    require_complete: bool,
) -> tuple[ValidatedAnswer, ...]:
    selected = questions_for_age_stage(age_stage)
    by_key = {question.key: question for question in selected}
    seen: set[str] = set()
    normalized: list[ValidatedAnswer] = []
    for answer in answers:
        question = by_key.get(answer.question_key)
        if question is None or answer.question_key in seen:
            raise ValueError("Answer references an unknown, unselected, or duplicate question")
        if answer.option not in {option.code for option in question.options}:
            raise ValueError("Answer option is not allowed by the pinned catalog")
        seen.add(answer.question_key)
        normalized.append(
            ValidatedAnswer(question_key=answer.question_key, option=answer.option, category=question.category)
        )
    if require_complete:
        missing = {question.key for question in selected if question.required} - seen
        if missing:
            raise ValueError("Required selected questionnaire answers are missing")
    return tuple(sorted(normalized, key=lambda item: item.question_key))


def canonical_answers_hash(
    *,
    session_id: UUID,
    child_profile_id: UUID,
    age_snapshot_id: UUID,
    questionnaire_version: str,
    answer_version: str,
    answers: tuple[ValidatedAnswer, ...],
) -> str:
    payload = {
        "age_snapshot_id": str(age_snapshot_id),
        "answer_version": answer_version,
        "answers": [
            {"question_key": item.question_key, "option": item.option}
            for item in sorted(answers, key=lambda value: value.question_key)
        ],
        "child_profile_id": str(child_profile_id),
        "questionnaire_session_id": str(session_id),
        "questionnaire_version": questionnaire_version,
    }
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()
