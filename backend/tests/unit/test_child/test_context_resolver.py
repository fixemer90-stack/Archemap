from __future__ import annotations

# ruff: noqa: RUF001
from copy import deepcopy
from datetime import date
from typing import cast
from uuid import uuid4

import pytest

from app.modules.child.age_resolver import AgeStage
from app.modules.child.context_resolver import (
    RESOLVER_VERSION,
    ResolverAgeSnapshot,
    resolve_context,
)
from app.modules.child.questionnaire import (
    ADAPTIVE_POLICY,
    ANSWER_VERSION,
    CONTEXT_VERSION,
    QUESTIONNAIRE_VERSION,
    AnswerInput,
    CatalogValidationError,
    Question,
    QuestionCategory,
    canonical_answers_hash,
    questions_for_age_stage,
    validate_answer_set,
    validate_catalog,
)
from app.modules.child.scoring.types import InteractionDimension


def test_s08_migration_is_additive_versioned_and_fail_safe() -> None:
    from pathlib import Path

    migration = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "f7a8b9c0d1e2_add_child_questionnaire_context_resolver.py"
    )
    source = migration.read_text(encoding="utf-8")
    assert 'down_revision: str | None = "e6f7a8b9c0d1"' in source
    upgrade = source.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]
    downgrade = source.split("def downgrade()", 1)[1]
    assert "uq_child_questionnaire_current_draft" in upgrade
    assert "fk_child_context_questionnaire_lineage" in upgrade
    assert "guard_child_questionnaire_answer_mutation" in source
    assert "OLD.questionnaire_session_id" in source
    assert "NEW.questionnaire_session_id" in source
    assert "BEFORE INSERT OR UPDATE OR DELETE ON child_answers" in source
    assert "child_questionnaire_completion_id" in source
    assert "NEW.id::text" in source
    assert "FOR SHARE" not in source
    assert "drop_table" not in upgrade
    assert "Refusing lossy downgrade" in downgrade
    assert downgrade.index("duplicate_profile_versions") < downgrade.index("op.drop_index")


def test_s08_orm_and_repository_contract_pin_full_lineage() -> None:
    from sqlalchemy import Index, Table, UniqueConstraint

    from app.modules.child import models
    from app.modules.child.questionnaire_persistence import (
        ChildContextResolutionRepository,
        ChildQuestionnaireRepository,
    )

    session = cast(Table, models.ChildQuestionnaireSession.__table__)
    assert {
        "owner_user_id",
        "age_snapshot_id",
        "selected_question_keys",
        "answer_version",
        "questionnaire_version",
        "context_version",
        "consent_version",
    } <= set(session.columns.keys())
    assert any(
        index.name == "uq_child_questionnaire_current_draft" for index in session.indexes if isinstance(index, Index)
    )
    assert not any(
        {column.name for column in constraint.columns} == {"child_profile_id", "questionnaire_version"}
        for constraint in session.constraints
        if isinstance(constraint, UniqueConstraint)
    )

    resolution = cast(Table, models.ChildContextResolution.__table__)
    assert {
        "questionnaire_session_id",
        "age_snapshot_id",
        "interaction_scoring_version",
        "input_hash",
    } <= set(resolution.columns.keys())
    assert ChildQuestionnaireRepository is not None
    assert ChildContextResolutionRepository is not None


ALL_STAGES: tuple[AgeStage, ...] = ("0-1", "1-3", "3-6", "6-9", "9-12", "12-15", "15-18")


def test_catalog_is_backend_owned_versioned_age_filtered_and_safe() -> None:
    selected = {stage: questions_for_age_stage(stage) for stage in ALL_STAGES}

    assert QUESTIONNAIRE_VERSION == "child-questionnaire-mvp-1"
    assert ANSWER_VERSION == "child-answer-mvp-1"
    assert CONTEXT_VERSION == "child-context-mvp-1"
    assert RESOLVER_VERSION == "child-context-resolver-mvp-1"
    assert ADAPTIVE_POLICY.enabled is False
    assert ADAPTIVE_POLICY.mode == "disabled_deterministic"
    assert all(8 <= len(questions) <= 12 for questions in selected.values())
    assert len({question.key for questions in selected.values() for question in questions}) == 10
    assert {question.category for questions in selected.values() for question in questions} == set(QuestionCategory)
    assert tuple(question.key for question in selected["0-1"]) != tuple(question.key for question in selected["15-18"])
    for questions in selected.values():
        assert {question.category for question in questions} == set(QuestionCategory)
        assert all(question.prompt_ru and len(question.prompt_ru) <= 240 for question in questions)


def test_invalid_catalog_is_rejected() -> None:
    valid = questions_for_age_stage("3-6")[0]
    duplicate = Question(
        key=valid.key,
        prompt_ru="Безопасный повтор ключа",
        category=QuestionCategory.OBSERVATION,
        answer_kind=valid.answer_kind,
        options=valid.options,
        required=True,
        age_stages=("3-6",),
    )
    with pytest.raises(CatalogValidationError):
        validate_catalog((valid, duplicate))

    unsafe = Question(
        key="unsafe_trait",
        prompt_ru="Какой диагноз или характер у ребёнка?",
        category=QuestionCategory.OBSERVATION,
        answer_kind=valid.answer_kind,
        options=valid.options,
        required=True,
        age_stages=("3-6",),
    )
    with pytest.raises(CatalogValidationError):
        validate_catalog((unsafe,))


def test_answers_validate_only_selected_catalog_options_and_hash_is_order_independent() -> None:
    selected = questions_for_age_stage("3-6")
    answers = tuple(AnswerInput(question_key=q.key, option=q.options[0].code) for q in selected)
    normalized = validate_answer_set(age_stage="3-6", answers=answers, require_complete=True)
    session_id = uuid4()
    child_id = uuid4()
    age_id = uuid4()
    first = canonical_answers_hash(
        session_id=session_id,
        child_profile_id=child_id,
        age_snapshot_id=age_id,
        questionnaire_version=QUESTIONNAIRE_VERSION,
        answer_version=ANSWER_VERSION,
        answers=normalized,
    )
    second = canonical_answers_hash(
        session_id=session_id,
        child_profile_id=child_id,
        age_snapshot_id=age_id,
        questionnaire_version=QUESTIONNAIRE_VERSION,
        answer_version=ANSWER_VERSION,
        answers=tuple(reversed(normalized)),
    )
    assert first == second

    with pytest.raises(ValueError):
        validate_answer_set(
            age_stage="3-6",
            answers=(*answers, AnswerInput(question_key="client_added", option="yes")),
            require_complete=False,
        )
    with pytest.raises(ValueError):
        validate_answer_set(
            age_stage="3-6",
            answers=(AnswerInput(question_key=selected[0].key, option="raw free text"),),
            require_complete=False,
        )


def _scores() -> list[dict[str, object]]:
    values = {
        InteractionDimension.EMOTIONAL_ATTUNEMENT: (82.0, 0.8, "natural_match"),
        InteractionDimension.BOUNDARY_FIT: (25.0, 0.8, "high_attention"),
        InteractionDimension.AUTONOMY_BALANCE: (50.0, 0.6, "moderate_tension"),
        InteractionDimension.COMMUNICATION_FIT: (78.0, 0.75, "natural_match"),
        InteractionDimension.TEMPO_FIT: (50.0, 0.5, "moderate_tension"),
        InteractionDimension.CONFLICT_PATTERN: (30.0, 0.7, "high_attention"),
        InteractionDimension.SOOTHING_COMPATIBILITY: (80.0, 0.9, "natural_match"),
        InteractionDimension.LEARNING_INTERACTION: (70.0, 0.7, "natural_match"),
    }
    return [
        {
            "id": uuid4(),
            "dimension": dimension.value,
            "score": score,
            "confidence": confidence,
            "pattern": pattern,
            "scoring_version": "child-interaction-mvp-1",
        }
        for dimension, (score, confidence, pattern) in values.items()
    ]


def _answers() -> list[dict[str, object]]:
    option_by_key = {
        "caregiver_daily_contact": "high",
        "caregiver_boundary_role": "mostly_me",
        "observation_soothing": "space",
        "observation_boundary_reaction": "accepts_calmly",
        "parent_preference_explanation": "detailed",
        "family_constraint_routine": "depends",
        "observation_transition": "depends",
        "observation_autonomy": "often",
        "parent_preference_choice": "two_choices",
    }
    return [
        {
            "id": uuid4(),
            "question_key": key,
            "option": option,
            "answer_version": ANSWER_VERSION,
        }
        for key, option in option_by_key.items()
    ]


def test_resolver_preserves_score_values_and_emits_all_safe_bounded_outputs() -> None:
    scores = _scores()
    before = deepcopy(scores)
    answers = _answers()
    age = ResolverAgeSnapshot(
        id=uuid4(),
        age_stage="3-6",
        as_of_date=date(2026, 10, 18),
        age_rules_version="child-age-mvp-1",
    )
    resolved = resolve_context(
        child_profile_id=uuid4(),
        generation_id=uuid4(),
        questionnaire_session_id=uuid4(),
        age_snapshot=age,
        interaction_scores=scores,
        answers=answers,
    )

    assert scores == before
    assert resolved.natural_strengths
    assert resolved.potential_friction
    assert resolved.compensation_areas
    assert resolved.age_relevant_guidance
    assert resolved.confirmations
    assert resolved.contradictions
    assert resolved.unresolved_ambiguities
    all_entries = resolved.all_entries()
    assert len({entry.id for entry in all_entries}) == len(all_entries)
    assert all(0 <= entry.confidence <= 1 for entry in all_entries)
    serialized = repr(resolved.to_payload())
    assert "space" not in serialized
    assert "depends" not in serialized

    assert any(entry.dimension == "soothing_compatibility" for entry in resolved.contradictions)
    assert any(entry.dimension == "communication_fit" for entry in resolved.confirmations)


def test_resolver_is_answer_order_deterministic_and_rejects_wrong_score_set_or_versions() -> None:
    scores = _scores()
    answers = _answers()
    child_profile_id = uuid4()
    generation_id = uuid4()
    questionnaire_session_id = uuid4()
    age_snapshot = ResolverAgeSnapshot(
        id=uuid4(),
        age_stage="3-6",
        as_of_date=date(2026, 10, 18),
        age_rules_version="child-age-mvp-1",
    )
    assert (
        resolve_context(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            questionnaire_session_id=questionnaire_session_id,
            age_snapshot=age_snapshot,
            interaction_scores=scores,
            answers=answers,
        ).to_payload()
        == resolve_context(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            questionnaire_session_id=questionnaire_session_id,
            age_snapshot=age_snapshot,
            interaction_scores=scores,
            answers=list(reversed(answers)),
        ).to_payload()
    )

    with pytest.raises(ValueError):
        resolve_context(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            questionnaire_session_id=questionnaire_session_id,
            age_snapshot=age_snapshot,
            interaction_scores=scores[:-1],
            answers=answers,
        )
    wrong = deepcopy(scores)
    wrong[0]["scoring_version"] = "legacy"
    with pytest.raises(ValueError):
        resolve_context(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            questionnaire_session_id=questionnaire_session_id,
            age_snapshot=age_snapshot,
            interaction_scores=wrong,
            answers=answers,
        )


def test_resolver_revalidates_catalog_options_and_complete_required_answers() -> None:
    child_profile_id = uuid4()
    generation_id = uuid4()
    questionnaire_session_id = uuid4()
    age_snapshot = ResolverAgeSnapshot(
        id=uuid4(),
        age_stage="3-6",
        as_of_date=date(2026, 10, 18),
        age_rules_version="child-age-mvp-1",
    )
    interaction_scores = _scores()
    invalid_option = deepcopy(_answers())
    invalid_option[0]["option"] = "not_in_catalog"
    with pytest.raises(ValueError, match="option"):
        resolve_context(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            questionnaire_session_id=questionnaire_session_id,
            age_snapshot=age_snapshot,
            interaction_scores=interaction_scores,
            answers=invalid_option,
        )

    incomplete = _answers()[1:]
    with pytest.raises(ValueError, match="Required"):
        resolve_context(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            questionnaire_session_id=questionnaire_session_id,
            age_snapshot=age_snapshot,
            interaction_scores=interaction_scores,
            answers=incomplete,
        )
