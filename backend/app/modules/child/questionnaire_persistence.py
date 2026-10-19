"""Transactional persistence for Child questionnaire drafts and context resolution."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.child import models
from app.modules.child.age_resolver import AgeStage
from app.modules.child.context_resolver import RESOLVER_VERSION, ResolverAgeSnapshot, resolve_context
from app.modules.child.questionnaire import (
    ANSWER_VERSION,
    CONSENT_VERSION,
    CONTEXT_VERSION,
    QUESTIONNAIRE_VERSION,
    AnswerInput,
    canonical_answers_hash,
    questions_for_age_stage,
    validate_answer_set,
)
from app.modules.child.repository import ChildIdempotencyTargetMismatchError, ChildLineageMismatchError
from app.reference_data.child.interaction_v1 import INTERACTION_SCORING_VERSION


@dataclass(frozen=True, slots=True)
class QuestionnaireDraft:
    session: models.ChildQuestionnaireSession
    answers: tuple[models.ChildAnswer, ...]
    created: bool


@dataclass(frozen=True, slots=True)
class QuestionnaireCompletion:
    session: models.ChildQuestionnaireSession
    answers: tuple[models.ChildAnswer, ...]
    completed_now: bool


@dataclass(frozen=True, slots=True)
class ContextResolutionPersistenceResult:
    resolution: models.ChildContextResolution
    created: bool


class ChildQuestionnaireRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _lock(self, child_profile_id: UUID) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"child-questionnaire:{child_profile_id}"},
        )

    async def _lock_completion_key(self, owner_user_id: UUID, completion_idempotency_key: str) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"child-questionnaire-completion:{owner_user_id}:{completion_idempotency_key}"},
        )

    async def _owned_child(self, owner_user_id: UUID, child_profile_id: UUID) -> models.ChildProfile:
        child = await self.session.scalar(
            select(models.ChildProfile)
            .where(
                models.ChildProfile.id == child_profile_id,
                models.ChildProfile.owner_user_id == owner_user_id,
            )
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if child is None:
            raise ChildLineageMismatchError("Questionnaire target is unavailable")
        return child

    async def get_or_create_current_draft(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        age_snapshot_id: UUID,
        questionnaire_version: str = QUESTIONNAIRE_VERSION,
        answer_version: str = ANSWER_VERSION,
        context_version: str = CONTEXT_VERSION,
        consent_version: str = CONSENT_VERSION,
    ) -> QuestionnaireDraft:
        if (
            questionnaire_version != QUESTIONNAIRE_VERSION
            or answer_version != ANSWER_VERSION
            or context_version != CONTEXT_VERSION
            or consent_version != CONSENT_VERSION
        ):
            raise ValueError("Unsupported current questionnaire contract version")
        await self._lock(child_profile_id)
        await self._owned_child(owner_user_id, child_profile_id)
        age = await self.session.scalar(
            select(models.ChildAgeSnapshot)
            .where(
                models.ChildAgeSnapshot.id == age_snapshot_id,
                models.ChildAgeSnapshot.child_profile_id == child_profile_id,
            )
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if age is None:
            raise ChildLineageMismatchError("Questionnaire age snapshot is unavailable")
        selected = [question.key for question in questions_for_age_stage(cast(AgeStage, age.age_stage))]
        existing = await self.session.scalar(
            select(models.ChildQuestionnaireSession)
            .where(
                models.ChildQuestionnaireSession.owner_user_id == owner_user_id,
                models.ChildQuestionnaireSession.child_profile_id == child_profile_id,
                models.ChildQuestionnaireSession.age_snapshot_id == age_snapshot_id,
                models.ChildQuestionnaireSession.questionnaire_version == questionnaire_version,
                models.ChildQuestionnaireSession.status == "draft",
            )
            .execution_options(populate_existing=True)
        )
        if existing is not None:
            if (
                existing.answer_version != answer_version
                or existing.context_version != context_version
                or existing.consent_version != consent_version
                or existing.selected_question_keys != selected
            ):
                raise ChildLineageMismatchError("Persisted draft contract differs from the current catalog")
            return QuestionnaireDraft(existing, await self._answers(existing.id), False)
        draft = models.ChildQuestionnaireSession(
            id=uuid.uuid4(),
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            age_snapshot_id=age_snapshot_id,
            status="draft",
            selected_question_keys=selected,
            questionnaire_version=questionnaire_version,
            answer_version=answer_version,
            context_version=context_version,
            consent_version=consent_version,
        )
        self.session.add(draft)
        await self.session.flush()
        return QuestionnaireDraft(draft, (), True)

    async def save_draft_answers(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        questionnaire_session_id: UUID,
        answers: tuple[AnswerInput, ...],
    ) -> QuestionnaireDraft:
        await self._lock(child_profile_id)
        await self._owned_child(owner_user_id, child_profile_id)
        questionnaire = await self._session_for_update(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            questionnaire_session_id=questionnaire_session_id,
        )
        if questionnaire.status != "draft":
            raise ChildLineageMismatchError("Questionnaire draft is unavailable")
        age = await self.session.scalar(
            select(models.ChildAgeSnapshot)
            .where(
                models.ChildAgeSnapshot.id == questionnaire.age_snapshot_id,
                models.ChildAgeSnapshot.child_profile_id == child_profile_id,
            )
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if age is None or questionnaire.questionnaire_version != QUESTIONNAIRE_VERSION:
            raise ChildLineageMismatchError("Questionnaire pinned catalog is unavailable")
        normalized = validate_answer_set(
            age_stage=cast(AgeStage, age.age_stage), answers=answers, require_complete=False
        )
        if any(item.question_key not in questionnaire.selected_question_keys for item in normalized):
            raise ValueError("Answer is not selected by the pinned backend catalog")
        # All expected domain errors above occur before the first mutation.
        await self.session.execute(
            delete(models.ChildAnswer).where(
                models.ChildAnswer.questionnaire_session_id == questionnaire.id,
                models.ChildAnswer.child_profile_id == child_profile_id,
            )
        )
        rows = tuple(
            models.ChildAnswer(
                id=uuid.uuid4(),
                child_profile_id=child_profile_id,
                questionnaire_session_id=questionnaire.id,
                question_key=item.question_key,
                answer={"option": item.option},
                answer_version=questionnaire.answer_version,
            )
            for item in normalized
        )
        self.session.add_all(list(rows))
        await self.session.flush()
        return QuestionnaireDraft(questionnaire, rows, False)

    async def complete_idempotently(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        questionnaire_session_id: UUID,
        completion_idempotency_key: str,
        now: datetime | None = None,
    ) -> QuestionnaireCompletion:
        if not completion_idempotency_key or len(completion_idempotency_key) > 120:
            raise ValueError("Completion idempotency key is required and bounded")
        effective_now = datetime.now(UTC) if now is None else now
        if effective_now.tzinfo is None or effective_now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        await self._lock_completion_key(owner_user_id, completion_idempotency_key)
        await self._lock(child_profile_id)
        await self._owned_child(owner_user_id, child_profile_id)
        reused = await self.session.scalar(
            select(models.ChildQuestionnaireSession).where(
                models.ChildQuestionnaireSession.owner_user_id == owner_user_id,
                models.ChildQuestionnaireSession.completion_idempotency_key == completion_idempotency_key,
            )
        )
        if reused is not None and reused.id != questionnaire_session_id:
            raise ChildIdempotencyTargetMismatchError("Questionnaire completion key targets another session")
        questionnaire = await self._session_for_update(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            questionnaire_session_id=questionnaire_session_id,
        )
        age = await self.session.scalar(
            select(models.ChildAgeSnapshot)
            .where(
                models.ChildAgeSnapshot.id == questionnaire.age_snapshot_id,
                models.ChildAgeSnapshot.child_profile_id == child_profile_id,
            )
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if age is None or questionnaire.questionnaire_version != QUESTIONNAIRE_VERSION:
            raise ChildLineageMismatchError("Questionnaire pinned catalog is unavailable")
        selected_question_keys = [question.key for question in questions_for_age_stage(cast(AgeStage, age.age_stage))]
        if (
            questionnaire.answer_version != ANSWER_VERSION
            or questionnaire.context_version != CONTEXT_VERSION
            or questionnaire.consent_version != CONSENT_VERSION
            or questionnaire.selected_question_keys != selected_question_keys
        ):
            raise ChildLineageMismatchError("Questionnaire pinned contract is unavailable")
        answer_rows = await self._answers(questionnaire.id, lock=True)
        if any(
            row.child_profile_id != child_profile_id
            or row.questionnaire_session_id != questionnaire.id
            or row.answer_version != questionnaire.answer_version
            for row in answer_rows
        ):
            raise ChildLineageMismatchError("Questionnaire answer lineage is unavailable")
        normalized = validate_answer_set(
            age_stage=cast(AgeStage, age.age_stage),
            answers=tuple(
                AnswerInput(question_key=row.question_key, option=str(row.answer.get("option", "")))
                for row in answer_rows
            ),
            require_complete=True,
        )
        answer_hash = canonical_answers_hash(
            session_id=questionnaire.id,
            child_profile_id=child_profile_id,
            age_snapshot_id=questionnaire.age_snapshot_id,
            questionnaire_version=questionnaire.questionnaire_version,
            answer_version=questionnaire.answer_version,
            answers=normalized,
        )
        if questionnaire.status == "completed":
            if (
                questionnaire.completion_idempotency_key != completion_idempotency_key
                or questionnaire.answers_hash != answer_hash
            ):
                raise ChildIdempotencyTargetMismatchError("Completion retry differs from immutable answer set")
            return QuestionnaireCompletion(questionnaire, answer_rows, False)
        if questionnaire.status != "draft":
            raise ChildLineageMismatchError("Questionnaire cannot be completed")
        await self.session.execute(
            text("SELECT set_config('app.child_questionnaire_completion_id', :session_id, true)"),
            {"session_id": str(questionnaire.id)},
        )
        questionnaire.status = "completed"
        questionnaire.completion_idempotency_key = completion_idempotency_key
        questionnaire.answers_hash = answer_hash
        questionnaire.completed_at = effective_now
        await self.session.flush()
        await self.session.execute(text("SELECT set_config('app.child_questionnaire_completion_id', '', true)"))
        return QuestionnaireCompletion(questionnaire, answer_rows, True)

    async def _session_for_update(
        self, *, owner_user_id: UUID, child_profile_id: UUID, questionnaire_session_id: UUID
    ) -> models.ChildQuestionnaireSession:
        row = await self.session.scalar(
            select(models.ChildQuestionnaireSession)
            .where(
                models.ChildQuestionnaireSession.id == questionnaire_session_id,
                models.ChildQuestionnaireSession.owner_user_id == owner_user_id,
                models.ChildQuestionnaireSession.child_profile_id == child_profile_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if row is None:
            raise ChildLineageMismatchError("Questionnaire target is unavailable")
        return row

    async def _answers(self, questionnaire_session_id: UUID, *, lock: bool = False) -> tuple[models.ChildAnswer, ...]:
        statement = (
            select(models.ChildAnswer)
            .where(models.ChildAnswer.questionnaire_session_id == questionnaire_session_id)
            .order_by(models.ChildAnswer.question_key, models.ChildAnswer.id)
            .execution_options(populate_existing=True)
        )
        if lock:
            statement = statement.with_for_update(read=True)
        return tuple((await self.session.execute(statement)).scalars().all())


class ChildContextResolutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_or_load(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
        questionnaire_session_id: UUID,
    ) -> ContextResolutionPersistenceResult:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"child-context:{generation_id}:{RESOLVER_VERSION}"},
        )
        source = await self._locked_sources(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            questionnaire_session_id=questionnaire_session_id,
        )
        expected = resolve_context(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            questionnaire_session_id=questionnaire_session_id,
            age_snapshot=ResolverAgeSnapshot(
                id=source[1].id,
                age_stage=cast(AgeStage, source[1].age_stage),
                as_of_date=source[1].as_of_date,
                age_rules_version=source[1].age_rules_version,
            ),
            interaction_scores=source[3],
            answers=source[2],
        )
        payload = expected.to_payload()
        values: dict[str, Any] = {
            "id": uuid.uuid4(),
            "child_profile_id": child_profile_id,
            "generation_id": generation_id,
            "questionnaire_session_id": questionnaire_session_id,
            "age_snapshot_id": source[1].id,
            "resolver_version": RESOLVER_VERSION,
            "interaction_scoring_version": INTERACTION_SCORING_VERSION,
            "input_hash": expected.input_hash,
            **{
                key: payload[key]
                for key in (
                    "natural_strengths",
                    "potential_friction",
                    "compensation_areas",
                    "age_relevant_guidance",
                    "confirmations",
                    "contradictions",
                    "unresolved_ambiguities",
                )
            },
        }
        inserted = (
            await self.session.execute(
                pg_insert(models.ChildContextResolution)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["generation_id", "resolver_version"])
                .returning(models.ChildContextResolution)
            )
        ).scalar_one_or_none()
        if inserted is not None:
            return ContextResolutionPersistenceResult(inserted, True)
        existing = await self.session.scalar(
            select(models.ChildContextResolution)
            .where(
                models.ChildContextResolution.generation_id == generation_id,
                models.ChildContextResolution.resolver_version == RESOLVER_VERSION,
            )
            .execution_options(populate_existing=True)
        )
        if existing is None:
            raise ChildLineageMismatchError("Context resolution conflict could not be reloaded")
        self._validate_current(existing, values)
        return ContextResolutionPersistenceResult(existing, False)

    async def load(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
        resolver_version: str = RESOLVER_VERSION,
    ) -> models.ChildContextResolution:
        await self._lock_owned_route(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        row = await self.session.scalar(
            select(models.ChildContextResolution)
            .where(
                models.ChildContextResolution.child_profile_id == child_profile_id,
                models.ChildContextResolution.generation_id == generation_id,
                models.ChildContextResolution.resolver_version == resolver_version,
            )
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if row is None:
            raise ChildLineageMismatchError("Context resolution is unavailable")
        if resolver_version != RESOLVER_VERSION:
            return row
        source = await self._locked_sources(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            questionnaire_session_id=row.questionnaire_session_id,
        )
        expected = resolve_context(
            child_profile_id=child_profile_id,
            generation_id=generation_id,
            questionnaire_session_id=row.questionnaire_session_id,
            age_snapshot=ResolverAgeSnapshot(
                id=source[1].id,
                age_stage=cast(AgeStage, source[1].age_stage),
                as_of_date=source[1].as_of_date,
                age_rules_version=source[1].age_rules_version,
            ),
            interaction_scores=source[3],
            answers=source[2],
        )
        payload = expected.to_payload()
        self._validate_current(
            row,
            {
                "questionnaire_session_id": row.questionnaire_session_id,
                "age_snapshot_id": source[1].id,
                "resolver_version": RESOLVER_VERSION,
                "interaction_scoring_version": INTERACTION_SCORING_VERSION,
                "input_hash": expected.input_hash,
                **payload,
            },
        )
        return row

    async def _lock_owned_route(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
    ) -> tuple[models.ChildProfile, models.ChildGeneration]:
        child = await self.session.scalar(
            select(models.ChildProfile)
            .where(models.ChildProfile.id == child_profile_id, models.ChildProfile.owner_user_id == owner_user_id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        generation = await self.session.scalar(
            select(models.ChildGeneration)
            .where(
                models.ChildGeneration.child_profile_id == child_profile_id,
                models.ChildGeneration.owner_user_id == owner_user_id,
                models.ChildGeneration.generation_id == generation_id,
            )
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if child is None or generation is None:
            raise ChildLineageMismatchError("Context source route is unavailable")
        return child, generation

    async def _locked_sources(
        self,
        *,
        owner_user_id: UUID,
        child_profile_id: UUID,
        generation_id: UUID,
        questionnaire_session_id: UUID,
    ) -> tuple[
        models.ChildQuestionnaireSession,
        models.ChildAgeSnapshot,
        tuple[models.ChildAnswer, ...],
        tuple[models.ChildInteractionScore, ...],
    ]:
        await self._lock_owned_route(
            owner_user_id=owner_user_id,
            child_profile_id=child_profile_id,
            generation_id=generation_id,
        )
        questionnaire = await self.session.scalar(
            select(models.ChildQuestionnaireSession)
            .where(
                models.ChildQuestionnaireSession.id == questionnaire_session_id,
                models.ChildQuestionnaireSession.child_profile_id == child_profile_id,
                models.ChildQuestionnaireSession.owner_user_id == owner_user_id,
            )
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if questionnaire is None or questionnaire.status != "completed":
            raise ChildLineageMismatchError("Context source route is unavailable")
        age = await self.session.scalar(
            select(models.ChildAgeSnapshot)
            .where(
                models.ChildAgeSnapshot.id == questionnaire.age_snapshot_id,
                models.ChildAgeSnapshot.child_profile_id == child_profile_id,
            )
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        answers = tuple(
            (
                await self.session.execute(
                    select(models.ChildAnswer)
                    .where(
                        models.ChildAnswer.child_profile_id == child_profile_id,
                        models.ChildAnswer.questionnaire_session_id == questionnaire_session_id,
                    )
                    .order_by(models.ChildAnswer.question_key, models.ChildAnswer.id)
                    .with_for_update(read=True)
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        scores = tuple(
            (
                await self.session.execute(
                    select(models.ChildInteractionScore)
                    .where(
                        models.ChildInteractionScore.child_profile_id == child_profile_id,
                        models.ChildInteractionScore.generation_id == generation_id,
                        models.ChildInteractionScore.scoring_version == INTERACTION_SCORING_VERSION,
                    )
                    .order_by(models.ChildInteractionScore.dimension, models.ChildInteractionScore.id)
                    .with_for_update(read=True)
                    .execution_options(populate_existing=True)
                )
            )
            .scalars()
            .all()
        )
        if age is None:
            raise ChildLineageMismatchError("Context age source is unavailable")
        selected_question_keys = [question.key for question in questions_for_age_stage(cast(AgeStage, age.age_stage))]
        if (
            questionnaire.questionnaire_version != QUESTIONNAIRE_VERSION
            or questionnaire.answer_version != ANSWER_VERSION
            or questionnaire.context_version != CONTEXT_VERSION
            or questionnaire.consent_version != CONSENT_VERSION
            or questionnaire.selected_question_keys != selected_question_keys
        ):
            raise ChildLineageMismatchError("Completed questionnaire contract is unavailable")
        normalized = validate_answer_set(
            age_stage=cast(AgeStage, age.age_stage),
            answers=tuple(
                AnswerInput(question_key=row.question_key, option=str(row.answer.get("option", ""))) for row in answers
            ),
            require_complete=True,
        )
        if any(
            row.child_profile_id != child_profile_id
            or row.questionnaire_session_id != questionnaire_session_id
            or row.answer_version != ANSWER_VERSION
            for row in answers
        ):
            raise ChildLineageMismatchError("Completed questionnaire answer lineage is unavailable")
        expected_hash = canonical_answers_hash(
            session_id=questionnaire.id,
            child_profile_id=child_profile_id,
            age_snapshot_id=questionnaire.age_snapshot_id,
            questionnaire_version=questionnaire.questionnaire_version,
            answer_version=questionnaire.answer_version,
            answers=normalized,
        )
        if questionnaire.answers_hash != expected_hash:
            raise ChildLineageMismatchError("Completed questionnaire hash is corrupt or stale")
        return questionnaire, age, answers, scores

    @staticmethod
    def _validate_current(row: models.ChildContextResolution, expected: dict[str, Any]) -> None:
        for key in (
            "questionnaire_session_id",
            "age_snapshot_id",
            "resolver_version",
            "interaction_scoring_version",
            "input_hash",
            "natural_strengths",
            "potential_friction",
            "compensation_areas",
            "age_relevant_guidance",
            "confirmations",
            "contradictions",
            "unresolved_ambiguities",
        ):
            if getattr(row, key) != expected[key]:
                raise ChildLineageMismatchError("Persisted current context resolution is corrupt or stale")
