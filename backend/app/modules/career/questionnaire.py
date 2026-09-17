"""Versioned Career questionnaire contracts and lifecycle helpers."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.modules.career.models import CareerAnswer, CareerQuestionnaireSession

QUESTIONNAIRE_VERSION = "career-q-1"
CONTEXT_VERSION = "career-context-1"
ADAPTIVE_QUESTIONS_ENABLED = False


class RiskPreference(StrEnum):
    STABLE = "stable"
    BALANCED = "balanced"
    HIGH = "high"


class PreferredTrack(StrEnum):
    EXPERT = "expert"
    MANAGER = "manager"
    ENTREPRENEUR = "entrepreneur"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class QuestionDefinition:
    key: str
    domain: str
    answer_type: str
    required: bool = True


QUESTION_BANK: tuple[QuestionDefinition, ...] = (
    QuestionDefinition("leadership_responsibility", "leadership", "scale_1_5"),
    QuestionDefinition("people_management_motivation", "people_management", "scale_1_5"),
    QuestionDefinition("autonomy_importance", "autonomy", "scale_1_5"),
    QuestionDefinition("risk_preference", "risk", "choice"),
    QuestionDefinition("preferred_track", "track", "choice"),
    QuestionDefinition("current_activity", "current_context", "bounded_text"),
    QuestionDefinition("experience_years", "experience", "integer"),
    QuestionDefinition("change_goal", "change_goal", "bounded_text"),
    QuestionDefinition("collaboration_preference", "people_management", "scale_1_5"),
    QuestionDefinition("current_constraints", "current_context", "bounded_text"),
)
_REQUIRED_KEYS = tuple(question.key for question in QUESTION_BANK if question.required)
_TAG_RE = re.compile(r"<[^>]*>")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACE_RE = re.compile(r"\s+")


class CareerQuestionnaireDraft(BaseModel):
    leadership_responsibility: int | None = Field(default=None, ge=1, le=5)
    people_management_motivation: int | None = Field(default=None, ge=1, le=5)
    autonomy_importance: int | None = Field(default=None, ge=1, le=5)
    risk_preference: RiskPreference | None = None
    preferred_track: PreferredTrack | None = None
    current_activity: str | None = Field(default=None, min_length=1, max_length=300)
    experience_years: int | None = Field(default=None, ge=0, le=60)
    change_goal: str | None = Field(default=None, min_length=1, max_length=500)
    collaboration_preference: int | None = Field(default=None, ge=1, le=5)
    current_constraints: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("current_activity", "change_goal", "current_constraints", mode="before")
    @classmethod
    def sanitize_bounded_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        without_tags = _TAG_RE.sub(" ", value)
        without_controls = _CONTROL_RE.sub("", without_tags)
        return _SPACE_RE.sub(" ", without_controls).strip()

    @property
    def missing_required(self) -> tuple[str, ...]:
        return tuple(key for key in _REQUIRED_KEYS if getattr(self, key) is None)


class CareerQuestionnaireCompleted(CareerQuestionnaireDraft):
    leadership_responsibility: int = Field(ge=1, le=5)
    people_management_motivation: int = Field(ge=1, le=5)
    autonomy_importance: int = Field(ge=1, le=5)
    risk_preference: RiskPreference
    preferred_track: PreferredTrack
    current_activity: str = Field(min_length=1, max_length=300)
    experience_years: int = Field(ge=0, le=60)
    change_goal: str = Field(min_length=1, max_length=500)
    collaboration_preference: int = Field(ge=1, le=5)
    current_constraints: str = Field(min_length=1, max_length=500)


def questionnaire_answers_hash(answers: CareerQuestionnaireCompleted) -> str:
    payload = json.dumps(answers.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def complete_questionnaire_session(
    session: CareerQuestionnaireSession,
    *,
    answers: CareerQuestionnaireCompleted,
    idempotency_key: str,
    completed_at: datetime,
) -> CareerQuestionnaireSession:
    """Complete once; identical retries are no-ops and conflicting retries fail closed."""
    answers_hash = questionnaire_answers_hash(answers)
    if session.status == "completed":
        if session.completion_idempotency_key == idempotency_key and session.answers_hash == answers_hash:
            return session
        raise ValueError("conflicting questionnaire retry")

    session.status = "completed"
    session.completion_idempotency_key = idempotency_key
    session.answers_hash = answers_hash
    session.completed_at = completed_at
    return session


def answer_payloads(answers: CareerQuestionnaireDraft) -> dict[str, dict[str, Any]]:
    """Return versioned persisted answer payloads; no prompt or LLM contract is produced."""
    return {
        key: {
            "value": value.value if isinstance(value, StrEnum) else value,
            "questionnaire_version": QUESTIONNAIRE_VERSION,
        }
        for key, value in answers.model_dump(exclude_none=True).items()
    }


def build_answer_rows(
    *,
    questionnaire_session_id: uuid.UUID,
    chart_id: uuid.UUID,
    answers: CareerQuestionnaireDraft,
) -> list[CareerAnswer]:
    """Build independently queryable, versioned answer rows."""
    return [
        CareerAnswer(
            id=uuid.uuid4(),
            questionnaire_session_id=questionnaire_session_id,
            chart_id=chart_id,
            question_key=key,
            answer=payload,
            answer_version=QUESTIONNAIRE_VERSION,
        )
        for key, payload in sorted(answer_payloads(answers).items())
    ]


def build_adaptive_questions() -> tuple[QuestionDefinition, ...]:
    """Reserved post-MVP extension point; intentionally disabled for Career MVP."""
    return ()
