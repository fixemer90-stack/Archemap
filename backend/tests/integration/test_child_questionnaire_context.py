from __future__ import annotations

import asyncio
import runpy
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.modules.astrotype_v2.models import NatalChart
from app.modules.child import models
from app.modules.child.age_resolver import AgeStage
from app.modules.child.questionnaire import AnswerInput, questions_for_age_stage
from app.modules.child.questionnaire_persistence import (
    ChildContextResolutionRepository,
    ChildQuestionnaireRepository,
)
from app.modules.child.repository import (
    ChildIdempotencyTargetMismatchError,
    ChildLineageMismatchError,
    ChildRepository,
)
from app.modules.child.scoring.types import InteractionDimension
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User
from app.reference_data.child.interaction_v1 import INTERACTION_SCORING_VERSION

pytestmark = pytest.mark.usefixtures("_setup_database")
_MIGRATION = runpy.run_path(
    str(
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "f7a8b9c0d1e2_add_child_questionnaire_context_resolver.py"
    )
)


@pytest.fixture(autouse=True)
async def _install_questionnaire_guards(_setup_database: None, db_session: AsyncSession) -> None:
    await db_session.execute(text("DROP TRIGGER IF EXISTS trg_child_answers_immutable ON child_answers"))
    await db_session.execute(text("DROP TRIGGER IF EXISTS trg_child_answers_questionnaire_guard ON child_answers"))
    await db_session.execute(
        text("DROP TRIGGER IF EXISTS trg_child_questionnaire_sessions_guard ON child_questionnaire_sessions")
    )
    await db_session.execute(text(str(_MIGRATION["ANSWER_GUARD_FUNCTION_SQL"])))
    await db_session.execute(text(str(_MIGRATION["ANSWER_GUARD_TRIGGER_SQL"])))
    await db_session.execute(text(str(_MIGRATION["SESSION_GUARD_FUNCTION_SQL"])))
    await db_session.execute(text(str(_MIGRATION["SESSION_GUARD_TRIGGER_SQL"])))
    await db_session.commit()


async def _seed(db: AsyncSession) -> tuple[User, models.ChildProfile, models.ChildAgeSnapshot, models.ChildGeneration]:
    owner = User(
        email=f"s08-{uuid4()}@example.com",
        name="Owner",
        hashed_password="test-only-hash",  # noqa: S106
        is_active=True,
        is_verified=True,
    )
    db.add(owner)
    await db.flush()
    profile = PersonProfile(
        user_id=owner.id,
        name="Owner",
        birth_date=date(1990, 1, 1),
        birth_time=None,
        birth_time_accuracy="unknown",
        birth_place="Москва",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
    )
    db.add(profile)
    await db.flush()
    chart = NatalChart(
        user_id=owner.id,
        profile_id=profile.id,
        engine_version="test-v1",
        input_hash="p" * 64,
        birth_datetime_utc=datetime(1990, 1, 1, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.7558,
        longitude=37.6173,
        house_system="P",
        calculation_payload={},
    )
    db.add(chart)
    await db.flush()
    child = (
        await ChildRepository(db).create_child_idempotently(
            owner_user_id=owner.id,
            parent_profile_id=profile.id,
            display_name="Ребёнок",
            relationship_type="child",
            child_gender=None,
            birth_date=date(2022, 1, 1),
            birth_time=None,
            birth_time_confidence="unknown",
            birth_place="Москва",
            latitude=55.7558,
            longitude=37.6173,
            timezone="Europe/Moscow",
            caregiver_context={},
            birth_data_hash="b" * 64,
            idempotency_key="s08-child",
        )
    ).child
    child_chart = models.ChildChartVersion(
        child_profile_id=child.id,
        version=1,
        engine_version="child-chart-test",
        input_hash="c" * 64,
        birth_time_confidence="unknown",
        allowed_fact_families=["planets"],
        excluded_fact_families=["houses"],
        uncertainty_reason="unknown_time",
        calculation_payload={},
    )
    age = models.ChildAgeSnapshot(
        child_profile_id=child.id,
        as_of_date=date(2026, 10, 18),
        age_years=4,
        age_months=9,
        age_days=17,
        age_stage="3-6",
        age_rules_version="child-age-mvp-1",
        input_hash="a" * 64,
    )
    db.add_all([child_chart, age])
    await db.flush()
    generation = models.ChildGeneration(
        child_profile_id=child.id,
        owner_user_id=owner.id,
        parent_chart_id=chart.id,
        child_chart_version_id=child_chart.id,
        generation_id=uuid4(),
        operation="generate",
        idempotency_key="s08-generation",
        status="deterministic_ready",
        diagnostics={},
    )
    db.add(generation)
    await db.flush()
    for index, dimension in enumerate(InteractionDimension):
        score = 75.0 if index % 2 == 0 else 25.0
        db.add(
            models.ChildInteractionScore(
                child_profile_id=child.id,
                parent_chart_id=chart.id,
                child_chart_version_id=child_chart.id,
                generation_id=generation.generation_id,
                dimension=dimension.value,
                score=score,
                confidence=0.8,
                pattern="natural_match" if score > 50 else "high_attention",
                scoring_version=INTERACTION_SCORING_VERSION,
                evidence_refs=[],
                breakdown={},
            )
        )
    await db.commit()
    return owner, child, age, generation


@pytest.mark.asyncio
async def test_questionnaire_draft_edit_complete_and_context_are_idempotent(db_session: AsyncSession) -> None:
    owner, child, age, generation = await _seed(db_session)
    owner_id = owner.id
    child_id = child.id
    age_id = age.id
    generation_id = generation.generation_id
    repository = ChildQuestionnaireRepository(db_session)
    draft = await repository.get_or_create_current_draft(
        owner_user_id=owner.id, child_profile_id=child.id, age_snapshot_id=age.id
    )
    resumed = await repository.get_or_create_current_draft(
        owner_user_id=owner.id, child_profile_id=child.id, age_snapshot_id=age.id
    )
    assert draft.created is True
    assert resumed.created is False
    assert resumed.session.id == draft.session.id
    questionnaire_session_id = draft.session.id

    questions = questions_for_age_stage("3-6")
    first_answers = tuple(AnswerInput(question_key=q.key, option=q.options[0].code) for q in questions)
    edited_answers = tuple(
        AnswerInput(question_key=q.key, option=q.options[min(1, len(q.options) - 1)].code) for q in questions
    )
    await repository.save_draft_answers(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        questionnaire_session_id=draft.session.id,
        answers=first_answers,
    )
    edited = await repository.save_draft_answers(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        questionnaire_session_id=draft.session.id,
        answers=edited_answers,
    )
    assert {row.answer["option"] for row in edited.answers} == {answer.option for answer in edited_answers}
    await db_session.commit()

    unauthorized_completion = await db_session.get(models.ChildQuestionnaireSession, questionnaire_session_id)
    assert unauthorized_completion is not None
    unauthorized_completion.status = "completed"
    unauthorized_completion.completion_idempotency_key = "orm-bypass"
    unauthorized_completion.answers_hash = "5" * 64
    unauthorized_completion.completed_at = datetime.now(UTC)
    with pytest.raises(models.ImmutableChildArtifactError):
        await db_session.flush()
    await db_session.rollback()

    trigger_count = await db_session.scalar(
        text("SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_child_questionnaire_sessions_guard'")
    )
    assert trigger_count == 1
    if trigger_count == 1:
        with pytest.raises(DBAPIError):
            await db_session.execute(
                text(
                    "UPDATE child_questionnaire_sessions SET status = 'completed', "
                    "completion_idempotency_key = 'raw-bypass', answers_hash = :hash, completed_at = now() "
                    "WHERE id = :id"
                ),
                {"hash": "6" * 64, "id": questionnaire_session_id},
            )
        await db_session.rollback()
        still_draft = await db_session.get(models.ChildQuestionnaireSession, questionnaire_session_id)
        assert still_draft is not None
        assert still_draft.status == "draft"

    completed = await repository.complete_idempotently(
        owner_user_id=owner_id,
        child_profile_id=child_id,
        questionnaire_session_id=questionnaire_session_id,
        completion_idempotency_key="s08-complete",
        now=datetime(2026, 10, 18, 18, tzinfo=UTC),
    )
    retry = await repository.complete_idempotently(
        owner_user_id=owner_id,
        child_profile_id=child_id,
        questionnaire_session_id=questionnaire_session_id,
        completion_idempotency_key="s08-complete",
        now=datetime(2026, 10, 18, 19, tzinfo=UTC),
    )
    assert completed.completed_now is True
    assert retry.completed_now is False
    assert retry.session.answers_hash == completed.session.answers_hash
    await db_session.commit()

    db_session.add(
        models.ChildAnswer(
            child_profile_id=child_id,
            questionnaire_session_id=questionnaire_session_id,
            question_key="post_completion_insert",
            answer={"option": "depends"},
            answer_version="child-answer-mvp-1",
        )
    )
    with pytest.raises(models.ImmutableChildArtifactError):
        await db_session.flush()
    await db_session.rollback()

    trigger_count = await db_session.scalar(
        text(
            "SELECT count(*) FROM pg_trigger WHERE tgname IN "
            "('trg_child_answers_questionnaire_guard', 'trg_child_questionnaire_sessions_guard')"
        )
    )
    assert trigger_count == 2
    if trigger_count == 2:
        with pytest.raises(DBAPIError):
            await db_session.execute(
                text(
                    "INSERT INTO child_answers "
                    "(id, child_profile_id, questionnaire_session_id, question_key, answer, answer_version) "
                    "VALUES (:id, :child_id, :session_id, 'raw_post_completion_insert', "
                    "CAST(:answer AS jsonb), 'child-answer-mvp-1')"
                ),
                {
                    "id": uuid4(),
                    "child_id": child_id,
                    "session_id": questionnaire_session_id,
                    "answer": '{"option":"depends"}',
                },
            )
        await db_session.rollback()

    with pytest.raises(ChildLineageMismatchError):
        await repository.save_draft_answers(
            owner_user_id=owner_id,
            child_profile_id=child_id,
            questionnaire_session_id=questionnaire_session_id,
            answers=first_answers,
        )
    await db_session.rollback()

    context_repository = ChildContextResolutionRepository(db_session)
    created = await context_repository.create_or_load(
        owner_user_id=owner_id,
        child_profile_id=child_id,
        generation_id=generation_id,
        questionnaire_session_id=questionnaire_session_id,
    )
    await db_session.commit()
    loaded = await context_repository.load(
        owner_user_id=owner_id,
        child_profile_id=child_id,
        generation_id=generation_id,
    )
    assert created.created is True
    assert loaded.id == created.resolution.id
    assert loaded.questionnaire_session_id == questionnaire_session_id
    assert loaded.age_snapshot_id == age_id
    await db_session.commit()

    foreign_owner = User(
        email=f"s08-foreign-{uuid4()}@example.com",
        name="Foreign",
        hashed_password="test-only-hash",  # noqa: S106
        is_active=True,
        is_verified=True,
    )
    legacy = models.ChildContextResolution(
        child_profile_id=child_id,
        generation_id=generation_id,
        questionnaire_session_id=questionnaire_session_id,
        age_snapshot_id=age_id,
        resolver_version="legacy-resolver-v1",
        interaction_scoring_version=INTERACTION_SCORING_VERSION,
        input_hash="f" * 64,
        natural_strengths=[],
        potential_friction=[],
        compensation_areas=[],
        age_relevant_guidance=[],
        confirmations=[],
        contradictions=[],
        unresolved_ambiguities=[],
    )
    db_session.add_all([foreign_owner, legacy])
    await db_session.commit()
    foreign_owner_id = foreign_owner.id
    assert (
        await context_repository.load(
            owner_user_id=owner_id,
            child_profile_id=child_id,
            generation_id=generation_id,
            resolver_version="legacy-resolver-v1",
        )
    ).id == legacy.id
    await db_session.commit()
    for resolver_version in ("legacy-resolver-v1", "child-context-resolver-mvp-1"):
        with pytest.raises(ChildLineageMismatchError):
            await context_repository.load(
                owner_user_id=foreign_owner_id,
                child_profile_id=child_id,
                generation_id=generation_id,
                resolver_version=resolver_version,
            )
        await db_session.rollback()

    trigger_count = await db_session.scalar(
        text(
            "SELECT count(*) FROM pg_trigger WHERE tgname IN "
            "('trg_child_answers_questionnaire_guard', 'trg_child_questionnaire_sessions_guard')"
        )
    )
    assert trigger_count == 2
    if trigger_count == 2:
        answer_id = await db_session.scalar(
            select(models.ChildAnswer.id)
            .where(models.ChildAnswer.questionnaire_session_id == questionnaire_session_id)
            .limit(1)
        )
        with pytest.raises(DBAPIError):
            await db_session.execute(
                text('UPDATE child_answers SET answer = \'{"option": "tampered"}\'::jsonb WHERE id = :id'),
                {"id": answer_id},
            )
        await db_session.rollback()
        with pytest.raises(DBAPIError):
            await db_session.execute(
                text("UPDATE child_questionnaire_sessions SET status = 'draft' WHERE id = :id"),
                {"id": questionnaire_session_id},
            )
        await db_session.rollback()
        persisted = await db_session.get(models.ChildQuestionnaireSession, questionnaire_session_id)
        assert persisted is not None
        assert persisted.status == "completed"

    preloaded = await context_repository.load(
        owner_user_id=owner_id,
        child_profile_id=child_id,
        generation_id=generation_id,
    )
    assert preloaded.input_hash == created.resolution.input_hash
    await db_session.commit()
    assert isinstance(db_session.bind, AsyncEngine)
    sessions = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)
    async with sessions() as writer:
        immutable_trigger = await writer.scalar(
            text("SELECT count(*) FROM pg_trigger WHERE tgname = 'trg_child_context_resolutions_immutable'")
        )
        if immutable_trigger == 1:
            await writer.execute(
                text("ALTER TABLE child_context_resolutions DISABLE TRIGGER trg_child_context_resolutions_immutable")
            )
        await writer.execute(
            text("UPDATE child_context_resolutions SET interaction_scoring_version = 'legacy-corrupt' WHERE id = :id"),
            {"id": created.resolution.id},
        )
        if immutable_trigger == 1:
            await writer.execute(
                text("ALTER TABLE child_context_resolutions ENABLE TRIGGER trg_child_context_resolutions_immutable")
            )
        await writer.commit()
        with pytest.raises(ChildLineageMismatchError, match="corrupt or stale"):
            await context_repository.load(
                owner_user_id=owner_id,
                child_profile_id=child_id,
                generation_id=generation_id,
            )
        await db_session.rollback()


@pytest.mark.asyncio
async def test_concurrent_draft_creation_returns_one_session(db_session: AsyncSession) -> None:
    owner, child, age, _ = await _seed(db_session)
    assert isinstance(db_session.bind, AsyncEngine)
    sessions = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)

    async def create() -> tuple[bool, object]:
        async with sessions() as session:
            result = await ChildQuestionnaireRepository(session).get_or_create_current_draft(
                owner_user_id=owner.id,
                child_profile_id=child.id,
                age_snapshot_id=age.id,
            )
            await session.commit()
            return result.created, result.session.id

    first, second = await asyncio.gather(create(), create())
    assert sorted([first[0], second[0]]) == [False, True]
    assert first[1] == second[1]
    count = len(
        (
            await db_session.execute(
                select(models.ChildQuestionnaireSession).where(
                    models.ChildQuestionnaireSession.child_profile_id == child.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert count == 1


@pytest.mark.asyncio
async def test_completion_authorization_is_bound_to_one_questionnaire(db_session: AsyncSession) -> None:
    owner, child, age, _ = await _seed(db_session)
    repository = ChildQuestionnaireRepository(db_session)
    first = await repository.get_or_create_current_draft(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        age_snapshot_id=age.id,
    )
    questions = questions_for_age_stage("3-6")
    await repository.save_draft_answers(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        questionnaire_session_id=first.session.id,
        answers=tuple(AnswerInput(question_key=q.key, option=q.options[0].code) for q in questions),
    )
    second_age = models.ChildAgeSnapshot(
        child_profile_id=child.id,
        as_of_date=date(2026, 10, 19),
        age_years=4,
        age_months=9,
        age_days=18,
        age_stage="3-6",
        age_rules_version="child-age-mvp-1",
        input_hash="d" * 64,
    )
    db_session.add(second_age)
    await db_session.flush()
    second = models.ChildQuestionnaireSession(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        age_snapshot_id=second_age.id,
        selected_question_keys=[q.key for q in questions],
        questionnaire_version="child-questionnaire-mvp-1",
        answer_version="child-answer-mvp-1",
        context_version="child-context-mvp-1",
        consent_version="child-consent-mvp-1",
        status="draft",
    )
    db_session.add(second)
    await db_session.flush()

    await repository.complete_idempotently(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        questionnaire_session_id=first.session.id,
        completion_idempotency_key="target-bound-first",
    )
    await db_session.execute(
        text("SELECT set_config('app.child_questionnaire_completion_id', :session_id, true)"),
        {"session_id": str(first.session.id)},
    )
    with pytest.raises(DBAPIError):
        await db_session.execute(
            text(
                "UPDATE child_questionnaire_sessions SET status = 'completed', "
                "completion_idempotency_key = 'unauthorized-second', answers_hash = :hash, "
                "completed_at = now() WHERE id = :id"
            ),
            {"hash": "f" * 64, "id": second.id},
        )
    await db_session.rollback()


@pytest.mark.asyncio
async def test_answer_guard_does_not_lock_parent_after_answer_row(db_session: AsyncSession) -> None:
    owner, child, age, _ = await _seed(db_session)
    repository = ChildQuestionnaireRepository(db_session)
    draft = await repository.get_or_create_current_draft(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        age_snapshot_id=age.id,
    )
    question = questions_for_age_stage("3-6")[0]
    saved = await repository.save_draft_answers(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        questionnaire_session_id=draft.session.id,
        answers=(AnswerInput(question_key=question.key, option=question.options[0].code),),
    )
    answer_id = saved.answers[0].id
    await db_session.commit()
    assert isinstance(db_session.bind, AsyncEngine)
    sessions = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)

    async with sessions() as parent_locker, sessions() as answer_writer:
        await parent_locker.execute(
            select(models.ChildQuestionnaireSession)
            .where(models.ChildQuestionnaireSession.id == draft.session.id)
            .with_for_update()
        )
        await asyncio.wait_for(
            answer_writer.execute(
                text("UPDATE child_answers SET answer = CAST(:answer AS jsonb) WHERE id = :id"),
                {"answer": f'{{"option":"{question.options[-1].code}"}}', "id": answer_id},
            ),
            timeout=2,
        )
        await answer_writer.commit()
        await parent_locker.rollback()


@pytest.mark.asyncio
async def test_completion_key_serializes_across_owner_children(db_session: AsyncSession) -> None:
    owner, first_child, first_age, _ = await _seed(db_session)
    second_child = (
        await ChildRepository(db_session).create_child_idempotently(
            owner_user_id=owner.id,
            parent_profile_id=first_child.parent_profile_id,
            display_name="Второй ребёнок",
            relationship_type="child",
            child_gender=None,
            birth_date=date(2020, 1, 1),
            birth_time=None,
            birth_time_confidence="unknown",
            birth_place="Москва",
            latitude=55.7558,
            longitude=37.6173,
            timezone="Europe/Moscow",
            caregiver_context={},
            birth_data_hash="e" * 64,
            idempotency_key="s08-second-child",
        )
    ).child
    second_age = models.ChildAgeSnapshot(
        child_profile_id=second_child.id,
        as_of_date=date(2026, 10, 18),
        age_years=6,
        age_months=9,
        age_days=17,
        age_stage="6-9",
        age_rules_version="child-age-mvp-1",
        input_hash="g" * 64,
    )
    db_session.add(second_age)
    await db_session.flush()
    repository = ChildQuestionnaireRepository(db_session)
    targets: list[tuple[UUID, UUID]] = []
    for child, age in ((first_child, first_age), (second_child, second_age)):
        draft = await repository.get_or_create_current_draft(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            age_snapshot_id=age.id,
        )
        questions = questions_for_age_stage(cast(AgeStage, age.age_stage))
        await repository.save_draft_answers(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            questionnaire_session_id=draft.session.id,
            answers=tuple(AnswerInput(question_key=q.key, option=q.options[0].code) for q in questions),
        )
        targets.append((child.id, draft.session.id))
    await db_session.commit()
    assert isinstance(db_session.bind, AsyncEngine)
    sessions = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)

    async def complete(child_id: UUID, questionnaire_id: UUID) -> object:
        async with sessions() as session:
            result = await ChildQuestionnaireRepository(session).complete_idempotently(
                owner_user_id=owner.id,
                child_profile_id=child_id,
                questionnaire_session_id=questionnaire_id,
                completion_idempotency_key="owner-wide-key",
            )
            await session.commit()
            return result

    results = await asyncio.gather(
        *(complete(child_id, session_id) for child_id, session_id in targets),
        return_exceptions=True,
    )
    assert sum(isinstance(result, ChildIdempotencyTargetMismatchError) for result in results) == 1
    assert sum(not isinstance(result, Exception) for result in results) == 1


@pytest.mark.asyncio
async def test_concurrent_completion_and_context_creation_return_one_artifact(
    db_session: AsyncSession,
) -> None:
    owner, child, age, generation = await _seed(db_session)
    owner_id = owner.id
    child_id = child.id
    age_id = age.id
    generation_id = generation.generation_id
    repository = ChildQuestionnaireRepository(db_session)
    draft = await repository.get_or_create_current_draft(
        owner_user_id=owner_id,
        child_profile_id=child_id,
        age_snapshot_id=age_id,
    )
    answers = tuple(
        AnswerInput(question_key=question.key, option=question.options[0].code)
        for question in questions_for_age_stage("3-6")
    )
    await repository.save_draft_answers(
        owner_user_id=owner_id,
        child_profile_id=child_id,
        questionnaire_session_id=draft.session.id,
        answers=answers,
    )
    questionnaire_id = draft.session.id
    await db_session.commit()
    assert isinstance(db_session.bind, AsyncEngine)
    sessions = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)

    async def complete() -> tuple[bool, object]:
        async with sessions() as session:
            result = await ChildQuestionnaireRepository(session).complete_idempotently(
                owner_user_id=owner_id,
                child_profile_id=child_id,
                questionnaire_session_id=questionnaire_id,
                completion_idempotency_key="concurrent-completion",
            )
            await session.commit()
            return result.completed_now, result.session.id

    first_completion, second_completion = await asyncio.gather(complete(), complete())
    assert sorted([first_completion[0], second_completion[0]]) == [False, True]
    assert first_completion[1] == second_completion[1]

    async def create_context() -> tuple[bool, object]:
        async with sessions() as session:
            result = await ChildContextResolutionRepository(session).create_or_load(
                owner_user_id=owner_id,
                child_profile_id=child_id,
                generation_id=generation_id,
                questionnaire_session_id=questionnaire_id,
            )
            await session.commit()
            return result.created, result.resolution.id

    first_context, second_context = await asyncio.gather(create_context(), create_context())
    assert sorted([first_context[0], second_context[0]]) == [False, True]
    assert first_context[1] == second_context[1]


@pytest.mark.asyncio
async def test_completion_key_reuse_across_sessions_fails_before_write(db_session: AsyncSession) -> None:
    owner, child, age, _ = await _seed(db_session)
    repository = ChildQuestionnaireRepository(db_session)
    first = await repository.get_or_create_current_draft(
        owner_user_id=owner.id, child_profile_id=child.id, age_snapshot_id=age.id
    )
    answers = tuple(AnswerInput(q.key, q.options[0].code) for q in questions_for_age_stage("3-6"))
    await repository.save_draft_answers(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        questionnaire_session_id=first.session.id,
        answers=answers,
    )
    await repository.complete_idempotently(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        questionnaire_session_id=first.session.id,
        completion_idempotency_key="shared-key",
    )
    later_age = models.ChildAgeSnapshot(
        child_profile_id=child.id,
        as_of_date=date(2027, 10, 18),
        age_years=5,
        age_months=9,
        age_days=17,
        age_stage="3-6",
        age_rules_version="child-age-mvp-1",
        input_hash="d" * 64,
    )
    db_session.add(later_age)
    await db_session.flush()
    second = await repository.get_or_create_current_draft(
        owner_user_id=owner.id, child_profile_id=child.id, age_snapshot_id=later_age.id
    )
    await repository.save_draft_answers(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        questionnaire_session_id=second.session.id,
        answers=answers,
    )
    with pytest.raises(ChildIdempotencyTargetMismatchError):
        await repository.complete_idempotently(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            questionnaire_session_id=second.session.id,
            completion_idempotency_key="shared-key",
        )
    await db_session.commit()
    assert second.session.status == "draft"


@pytest.mark.asyncio
async def test_completion_rejects_invalid_pinned_contract_before_mutation(db_session: AsyncSession) -> None:
    owner, child, age, _ = await _seed(db_session)
    invalid = models.ChildQuestionnaireSession(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        age_snapshot_id=age.id,
        status="draft",
        selected_question_keys=["caregiver_daily_contact"],
        questionnaire_version="child-questionnaire-mvp-1",
        answer_version="legacy-answer-version",
        context_version="legacy-context-version",
        consent_version="legacy-consent-version",
    )
    db_session.add(invalid)
    await db_session.flush()
    db_session.add(
        models.ChildAnswer(
            child_profile_id=child.id,
            questionnaire_session_id=invalid.id,
            question_key="caregiver_daily_contact",
            answer={"option": "high"},
            answer_version="row-version-does-not-match-session",
        )
    )
    await db_session.flush()

    with pytest.raises(ChildLineageMismatchError, match="contract"):
        await ChildQuestionnaireRepository(db_session).complete_idempotently(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            questionnaire_session_id=invalid.id,
            completion_idempotency_key="invalid-contract",
        )
    await db_session.commit()
    persisted = await db_session.get(models.ChildQuestionnaireSession, invalid.id)
    assert persisted is not None
    assert persisted.status == "draft"
    assert persisted.answers_hash is None


@pytest.mark.asyncio
async def test_completed_answer_cannot_move_to_another_draft(db_session: AsyncSession) -> None:
    owner, child, age, _ = await _seed(db_session)
    owner_id = owner.id
    child_id = child.id
    repository = ChildQuestionnaireRepository(db_session)
    completed_draft = await repository.get_or_create_current_draft(
        owner_user_id=owner_id,
        child_profile_id=child_id,
        age_snapshot_id=age.id,
    )
    answers = tuple(
        AnswerInput(question_key=question.key, option=question.options[0].code)
        for question in questions_for_age_stage("3-6")
    )
    saved = await repository.save_draft_answers(
        owner_user_id=owner_id,
        child_profile_id=child_id,
        questionnaire_session_id=completed_draft.session.id,
        answers=answers,
    )
    await repository.complete_idempotently(
        owner_user_id=owner_id,
        child_profile_id=child_id,
        questionnaire_session_id=completed_draft.session.id,
        completion_idempotency_key="completed-before-move",
    )
    later_age = models.ChildAgeSnapshot(
        child_profile_id=child_id,
        as_of_date=date(2027, 10, 18),
        age_years=5,
        age_months=9,
        age_days=17,
        age_stage="3-6",
        age_rules_version="child-age-mvp-1",
        input_hash="e" * 64,
    )
    db_session.add(later_age)
    await db_session.flush()
    target_draft = await repository.get_or_create_current_draft(
        owner_user_id=owner_id,
        child_profile_id=child_id,
        age_snapshot_id=later_age.id,
    )
    answer_id = saved.answers[0].id
    completed_session_id = completed_draft.session.id
    target_draft_id = target_draft.session.id
    await db_session.commit()

    answer = await db_session.get(models.ChildAnswer, answer_id)
    assert answer is not None
    answer.questionnaire_session_id = target_draft_id
    answer.answer = {"option": "depends"}
    with pytest.raises(models.ImmutableChildArtifactError):
        await db_session.flush()
    await db_session.rollback()
    persisted = await db_session.get(models.ChildAnswer, answer_id)
    assert persisted is not None
    assert persisted.questionnaire_session_id == completed_session_id
