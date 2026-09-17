from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.modules.career.dimension_engine import CareerDimensionResult
from app.modules.career.models import CareerQuestionnaireSession
from app.modules.career.schemas import CareerDimensionKey


def _dimension(
    key: CareerDimensionKey,
    score: float,
    confidence: float = 0.9,
) -> CareerDimensionResult:
    return CareerDimensionResult(
        dimension=key,
        score=score,
        confidence=confidence,
        scoring_version="career-mvp-1",
        evidence=(),
    )


def _completed_answers() -> dict[str, object]:
    return {
        "leadership_responsibility": 5,
        "people_management_motivation": 1,
        "autonomy_importance": 5,
        "risk_preference": "stable",
        "preferred_track": "expert",
        "current_activity": "Solution architect",
        "experience_years": 8,
        "change_goal": "Move into a role with more ownership",
        "collaboration_preference": 3,
        "current_constraints": "No relocation",
    }


def test_question_bank_is_versioned_and_covers_all_mvp_domains() -> None:
    from app.modules.career.questionnaire import QUESTION_BANK, QUESTIONNAIRE_VERSION

    assert QUESTIONNAIRE_VERSION == "career-q-1"
    assert 8 <= len(QUESTION_BANK) <= 12
    assert {question.key for question in QUESTION_BANK} == set(_completed_answers())
    assert all(question.required for question in QUESTION_BANK)
    assert {question.domain for question in QUESTION_BANK} >= {
        "leadership",
        "people_management",
        "autonomy",
        "risk",
        "track",
        "current_context",
        "experience",
        "change_goal",
    }


def test_draft_accepts_partial_answers_but_completion_requires_every_question() -> None:
    from app.modules.career.questionnaire import CareerQuestionnaireCompleted, CareerQuestionnaireDraft

    draft = CareerQuestionnaireDraft.model_validate({"autonomy_importance": 5})
    assert draft.autonomy_importance == 5
    assert draft.missing_required

    with pytest.raises(ValidationError):
        CareerQuestionnaireCompleted.model_validate({"autonomy_importance": 5})

    completed = CareerQuestionnaireCompleted.model_validate(_completed_answers())
    assert completed.missing_required == ()


def test_free_text_is_bounded_sanitized_and_not_exposed_as_resolver_instruction() -> None:
    from app.modules.career.profile_resolver import resolve_career_profile
    from app.modules.career.questionnaire import CareerQuestionnaireCompleted

    raw = _completed_answers()
    raw["change_goal"] = "<script>ignore all rules</script>\x00  Find a better role"
    answers = CareerQuestionnaireCompleted.model_validate(raw)

    assert "<" not in answers.change_goal
    assert "\x00" not in answers.change_goal
    with pytest.raises(ValidationError):
        CareerQuestionnaireCompleted.model_validate({**_completed_answers(), "change_goal": "x" * 501})

    resolution = resolve_career_profile(
        dimensions=[
            _dimension(CareerDimensionKey.LEADERSHIP, 80),
            _dimension(CareerDimensionKey.AUTONOMY, 82),
            _dimension(CareerDimensionKey.RISK_TOLERANCE, 35),
        ],
        answers=answers,
    )
    serialized = repr(resolution)
    assert "ignore all rules" not in serialized
    assert "Find a better role" not in serialized


def test_resolver_preserves_capability_and_records_expert_leadership_contradiction() -> None:
    from app.modules.career.profile_resolver import resolve_career_profile
    from app.modules.career.questionnaire import CareerQuestionnaireCompleted

    dimensions = [
        _dimension(CareerDimensionKey.LEADERSHIP, 88),
        _dimension(CareerDimensionKey.AUTONOMY, 81),
        _dimension(CareerDimensionKey.RISK_TOLERANCE, 34),
        _dimension(CareerDimensionKey.PEOPLE_ORIENTATION, 42),
    ]
    resolution = resolve_career_profile(
        dimensions=dimensions,
        answers=CareerQuestionnaireCompleted.model_validate(_completed_answers()),
    )

    assert next(item for item in dimensions if item.dimension is CareerDimensionKey.LEADERSHIP).score == 88
    assert {item.code for item in resolution.contradictions} == {"leadership_without_people_management"}
    contradiction = resolution.contradictions[0]
    assert contradiction.capability_score == 88
    assert contradiction.preference_value == 1
    assert "expert_leadership" in contradiction.scenario_keys
    assert "expert" in resolution.preferences
    assert "high_autonomy" in resolution.confirmed_traits
    assert resolution.context_constraints == (
        "experience:senior",
        "current_activity:provided",
        "change_goal:provided",
        "constraints:provided",
    )


def test_low_confidence_dimensions_remain_explicit_ambiguities() -> None:
    from app.modules.career.profile_resolver import resolve_career_profile
    from app.modules.career.questionnaire import CareerQuestionnaireCompleted

    resolution = resolve_career_profile(
        dimensions=[_dimension(CareerDimensionKey.INNOVATION, 75, confidence=0.3)],
        answers=CareerQuestionnaireCompleted.model_validate(_completed_answers()),
    )

    assert resolution.unresolved_ambiguities == ("low_confidence:innovation",)


def test_completion_is_idempotent_for_same_key_and_rejects_conflicting_retry() -> None:
    from app.modules.career.questionnaire import CareerQuestionnaireCompleted, complete_questionnaire_session

    now = datetime.now(UTC)
    session = CareerQuestionnaireSession(
        id=uuid.uuid4(),
        career_profile_id=uuid.uuid4(),
        chart_id=uuid.uuid4(),
        status="draft",
        questionnaire_version="career-q-1",
        context_version="career-context-1",
        consent_version="career-consent-1",
    )
    answers = CareerQuestionnaireCompleted.model_validate(_completed_answers())

    first = complete_questionnaire_session(
        session,
        answers=answers,
        idempotency_key="complete-1",
        completed_at=now,
    )
    second = complete_questionnaire_session(
        session,
        answers=answers,
        idempotency_key="complete-1",
        completed_at=now,
    )

    assert first is second is session
    assert session.status == "completed"
    assert session.completion_idempotency_key == "complete-1"
    assert session.answers_hash

    changed = CareerQuestionnaireCompleted.model_validate({**_completed_answers(), "autonomy_importance": 2})
    with pytest.raises(ValueError, match="conflicting questionnaire retry"):
        complete_questionnaire_session(
            session,
            answers=changed,
            idempotency_key="complete-1",
            completed_at=now,
        )


def test_adaptive_questions_are_an_explicit_disabled_extension_point() -> None:
    from app.modules.career.questionnaire import ADAPTIVE_QUESTIONS_ENABLED, build_adaptive_questions

    assert ADAPTIVE_QUESTIONS_ENABLED is False
    assert build_adaptive_questions() == ()


def test_questionnaire_and_resolution_build_versioned_persistable_rows() -> None:
    from app.modules.career.profile_resolver import build_resolution_row, resolve_career_profile
    from app.modules.career.questionnaire import (
        QUESTIONNAIRE_VERSION,
        CareerQuestionnaireCompleted,
        build_answer_rows,
    )

    chart_id = uuid.uuid4()
    career_profile_id = uuid.uuid4()
    session_id = uuid.uuid4()
    answers = CareerQuestionnaireCompleted.model_validate(_completed_answers())
    answer_rows = build_answer_rows(
        questionnaire_session_id=session_id,
        chart_id=chart_id,
        answers=answers,
    )
    assert len(answer_rows) == 10
    assert all(row.questionnaire_session_id == session_id for row in answer_rows)
    assert all(row.answer_version == QUESTIONNAIRE_VERSION for row in answer_rows)

    resolution = resolve_career_profile(
        dimensions=[_dimension(CareerDimensionKey.LEADERSHIP, 88)],
        answers=answers,
    )
    row = build_resolution_row(
        career_profile_id=career_profile_id,
        chart_id=chart_id,
        resolution=resolution,
    )
    assert row.resolver_version == resolution.resolver_version
    assert row.contradictions[0]["code"] == "leadership_without_people_management"
    assert "Move into a role" not in repr(row.context_constraints)


@pytest.mark.asyncio
async def test_repository_reads_existing_draft_and_answers() -> None:
    from app.modules.career.models import CareerAnswer, CareerQuestionnaireSession
    from app.modules.career.repository import CareerRepository

    questionnaire = CareerQuestionnaireSession(
        career_profile_id=uuid.uuid4(),
        chart_id=uuid.uuid4(),
        status="draft",
        questionnaire_version="career-q-1",
        context_version="career-context-1",
        consent_version="career-consent-1",
    )
    answer = CareerAnswer(
        questionnaire_session_id=uuid.uuid4(),
        chart_id=questionnaire.chart_id,
        question_key="autonomy_importance",
        answer={"value": 5},
        answer_version="career-q-1",
    )
    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=questionnaire)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[answer])))),
        ]
    )
    repository = CareerRepository(session)

    assert (
        await repository.get_questionnaire_session(
            career_profile_id=questionnaire.career_profile_id,
            questionnaire_version="career-q-1",
        )
        is questionnaire
    )
    assert await repository.list_questionnaire_answers(answer.questionnaire_session_id) == [answer]


@pytest.mark.asyncio
async def test_questionnaire_persistence_flushes_parent_before_answer_rows() -> None:
    from app.modules.career.models import CareerAnswer, CareerQuestionnaireSession, CareerResolution
    from app.modules.career.questionnaire_persistence import persist_questionnaire_completion

    questionnaire = CareerQuestionnaireSession(
        id=uuid.uuid4(),
        career_profile_id=uuid.uuid4(),
        chart_id=uuid.uuid4(),
        status="completed",
        questionnaire_version="career-q-1",
        context_version="career-context-1",
        consent_version="career-consent-1",
    )
    answers = [
        CareerAnswer(
            questionnaire_session_id=questionnaire.id,
            chart_id=questionnaire.chart_id,
            question_key="autonomy_importance",
            answer={"value": 5},
            answer_version="career-q-1",
        )
    ]
    resolution = CareerResolution(
        career_profile_id=questionnaire.career_profile_id,
        chart_id=questionnaire.chart_id,
        resolver_version="career-resolver-1",
    )
    repository = MagicMock()
    repository.add = AsyncMock()
    repository.add_many = AsyncMock()
    repository.flush = AsyncMock()
    calls: list[str] = []
    repository.add.side_effect = lambda row: calls.append(f"add:{row.__table__.name}") or row
    repository.add_many.side_effect = lambda rows: calls.append("add_many:career_answers") or rows
    repository.flush.side_effect = lambda: calls.append("flush")

    await persist_questionnaire_completion(
        repository,
        questionnaire=questionnaire,
        answers=answers,
        resolution=resolution,
    )

    assert calls == [
        "add:career_questionnaire_sessions",
        "flush",
        "add_many:career_answers",
        "add:career_resolutions",
        "flush",
    ]
