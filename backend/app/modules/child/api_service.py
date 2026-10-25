"""HTTP application adapters over canonical Child repositories.

Ownership projections intentionally contain no birth data, JSON or prose. Route
handlers call the paid policy only after these projections, before payload reads.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Literal, cast
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.child import api_schemas as schemas
from app.modules.child import models
from app.modules.child.age_resolver import AgeStage, resolve_child_age
from app.modules.child.birth_data import child_birth_data_hash
from app.modules.child.chart_adapter import ChildChartInput, build_child_chart
from app.modules.child.context_resolver import _AGE_ACTIONS, RESOLVER_VERSION
from app.modules.child.questionnaire import questions_for_age_stage
from app.modules.child.questionnaire_persistence import QuestionnaireCompletion, QuestionnaireDraft
from app.modules.child.repository import ChildIdempotencyTargetMismatchError, ChildRepository
from app.modules.child.service import (
    ChildGenerationAccepted,
    ChildGenerationDispatcher,
    _dispatch_accepted_generation,
    accept_age_update_generation,
    accept_narrative_retry_generation,
)
from app.modules.profiles.models import PersonProfile

# Own cache identity includes the complete birth-time policy in chart input hash.
CHILD_HTTP_CHART_ENGINE_VERSION = "child-chart-api-1"


def not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Child resource not found")


async def owned_child_id(
    db: AsyncSession,
    owner: UUID,
    *,
    child_id: UUID | None = None,
    resource: Literal["report", "generation", "questionnaire"] | None = None,
    resource_id: UUID | None = None,
    include_archived: bool = False,
) -> UUID:
    statement = select(models.ChildProfile.id).where(models.ChildProfile.owner_user_id == owner)
    if resource == "report":
        statement = statement.join(
            models.ChildReport, models.ChildReport.child_profile_id == models.ChildProfile.id
        ).where(models.ChildReport.id == resource_id)
    elif resource == "generation":
        statement = statement.join(
            models.ChildGeneration, models.ChildGeneration.child_profile_id == models.ChildProfile.id
        ).where(models.ChildGeneration.generation_id == resource_id, models.ChildGeneration.owner_user_id == owner)
    elif resource == "questionnaire":
        statement = statement.join(
            models.ChildQuestionnaireSession,
            models.ChildQuestionnaireSession.child_profile_id == models.ChildProfile.id,
        ).where(
            models.ChildQuestionnaireSession.id == resource_id, models.ChildQuestionnaireSession.owner_user_id == owner
        )
    if child_id is not None:
        statement = statement.where(models.ChildProfile.id == child_id)
    statement = statement.where(
        models.ChildProfile.status.in_(["active", "archived"] if include_archived else ["active"])
    )
    result = await db.scalar(statement)
    if result is None:
        raise not_found()
    return result


async def child_response(db: AsyncSession, child: models.ChildProfile) -> schemas.ChildResponse:
    chart = await ChildRepository(db).get_latest_chart_version(child.id)
    age = resolve_child_age(birth_date=child.birth_date, as_of=datetime.now(UTC), timezone_name=child.timezone)
    return schemas.ChildResponse(
        id=child.id,
        display_name=child.display_name,
        relationship_type=child.relationship_type,
        child_gender=child.child_gender,
        birth_date=child.birth_date,
        birth_time=child.birth_time,
        birth_time_confidence=child.birth_time_confidence,
        birth_place=schemas.BirthPlace(
            label=child.birth_place, latitude=child.latitude, longitude=child.longitude, timezone=child.timezone
        ),
        caregiver_context=schemas.CaregiverContext.model_validate(child.caregiver_context),
        status=child.status,
        version=child.version,
        age=schemas.AgeResponse.model_validate(asdict(age), extra="ignore"),
        current_chart=schemas.ChartResponse(
            chart_version_id=chart.id,
            version=chart.version,
            engine_version=chart.engine_version,
            birth_time_confidence=chart.birth_time_confidence,
            allowed_fact_families=chart.allowed_fact_families,
            excluded_fact_families=chart.excluded_fact_families,
            uncertainty_reason=chart.uncertainty_reason,
        )
        if chart is not None
        else None,
        created_at=child.created_at,
        updated_at=child.updated_at,
    )


def birth_values(payload: schemas.CreateChildRequest) -> dict[str, Any]:
    return {
        "birth_date": payload.birth_date,
        "birth_time": payload.birth_time,
        "birth_time_confidence": payload.birth_time_confidence,
        "birth_place": payload.birth_place.label,
        "latitude": payload.birth_place.latitude,
        "longitude": payload.birth_place.longitude,
        "timezone": payload.birth_place.timezone,
    }


def validated_chart(payload: schemas.CreateChildRequest) -> Any:
    resolve_child_age(
        birth_date=payload.birth_date, as_of=datetime.now(UTC), timezone_name=payload.birth_place.timezone
    )
    return build_child_chart(
        ChildChartInput(
            birth_date=payload.birth_date,
            birth_time=payload.birth_time,
            birth_time_confidence=payload.birth_time_confidence,
            latitude=payload.birth_place.latitude,
            longitude=payload.birth_place.longitude,
            timezone=payload.birth_place.timezone,
        ),
        engine_version=CHILD_HTTP_CHART_ENGINE_VERSION,
    )


async def create_child(
    db: AsyncSession, owner: UUID, payload: schemas.CreateChildRequest, key: str
) -> models.ChildProfile:
    repo = ChildRepository(db)
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"child-api-create:{owner}:{key}"}
    )
    existing = await repo.get_child_by_idempotency_key(owner_user_id=owner, idempotency_key=key)
    values = birth_values(payload)
    context = payload.caregiver_context.model_dump(exclude_none=True)
    if existing is not None:
        if (
            existing.status != "active"
            or any(getattr(existing, k) != v for k, v in values.items())
            or existing.display_name != payload.display_name
            or existing.relationship_type != payload.relationship_type
            or existing.child_gender != payload.child_gender
            or existing.caregiver_context != context
        ):
            raise ChildIdempotencyTargetMismatchError("Child create retry differs")
        return existing
    parent_id = await db.scalar(
        select(PersonProfile.id)
        .where(PersonProfile.user_id == owner)
        .order_by(PersonProfile.created_at.desc(), PersonProfile.id.desc())
        .limit(1)
    )
    if parent_id is None:
        raise HTTPException(status_code=409, detail="Parent profile is required")
    chart = validated_chart(payload)
    result = await repo.create_child_idempotently(
        owner_user_id=owner,
        parent_profile_id=parent_id,
        display_name=payload.display_name,
        relationship_type=payload.relationship_type,
        child_gender=payload.child_gender,
        caregiver_context=context,
        birth_data_hash=child_birth_data_hash(**values),
        idempotency_key=key,
        **values,
    )
    await repo.create_chart_version_idempotently(owner_user_id=owner, child_profile_id=result.child.id, chart=chart)
    await db.commit()
    return result.child


async def patch_child(
    db: AsyncSession, owner: UUID, child_id: UUID, patch: schemas.PatchChildRequest
) -> models.ChildProfile:
    repo = ChildRepository(db)
    await repo._lock_child_lineage(child_id)
    child = await db.scalar(
        select(models.ChildProfile)
        .where(
            models.ChildProfile.id == child_id,
            models.ChildProfile.owner_user_id == owner,
            models.ChildProfile.status == "active",
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if child is None:
        raise not_found()
    current = await child_response(db, child)
    data = current.model_dump(include=set(schemas.CreateChildRequest.model_fields))
    data.update(patch.model_dump(exclude_unset=True))
    proposed = schemas.CreateChildRequest.model_validate(data)
    values = birth_values(proposed)
    chart = validated_chart(proposed)
    await repo.correct_birth_data_and_create_chart(
        owner_user_id=owner,
        child_profile_id=child_id,
        house_system="P",
        birth_data_hash=child_birth_data_hash(**values),
        chart=chart,
        **values,
    )
    child.display_name = proposed.display_name
    child.relationship_type = proposed.relationship_type
    child.child_gender = proposed.child_gender
    child.caregiver_context = proposed.caregiver_context.model_dump(exclude_none=True)
    await db.commit()
    await db.refresh(child)
    return child


async def regenerate(
    db: AsyncSession,
    *,
    owner: UUID,
    child_id: UUID,
    report_id: UUID,
    scope: Literal["failed_sections", "narrative_all", "full_pair"],
    key: str,
    dispatcher: ChildGenerationDispatcher,
) -> ChildGenerationAccepted:
    # Serialize the public idempotency domain before resolving mutable defaults.
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"child-api-regenerate:{owner}:{key}"}
    )
    operation = "full_report" if scope == "full_pair" else "narrative_retry"
    repo = ChildRepository(db)
    if scope == "full_pair":
        # Match POST /reports: owner/operation/key precedes child lineage. A
        # correction takes lineage only, so it cannot invert this lock order.
        await repo._lock_generation_idempotency(owner_user_id=owner, operation=operation, idempotency_key=key)
    existing = await db.scalar(
        select(models.ChildGeneration)
        .where(
            models.ChildGeneration.owner_user_id == owner,
            models.ChildGeneration.operation.in_(["full_report", "narrative_retry"]),
            models.ChildGeneration.idempotency_key == key,
        )
        .execution_options(populate_existing=True)
    )
    if existing is not None:
        if (
            existing.child_profile_id != child_id
            or existing.source_report_id != report_id
            or existing.operation != operation
            or existing.operation_payload.get("scope", "failed_sections") != scope
        ):
            raise ChildIdempotencyTargetMismatchError("Regeneration retry differs")
        return ChildGenerationAccepted(
            existing.generation_id, existing.status, existing.report_id, False, existing.celery_task_id
        )
    if scope != "full_pair":
        return await accept_narrative_retry_generation(
            db,
            owner_user_id=owner,
            child_profile_id=child_id,
            source_report_id=report_id,
            idempotency_key=key,
            dispatcher=dispatcher,
            scope=scope,
        )
    # Accepted replays above never reroute against current DOB/chart inputs.
    # Fresh defaults and acceptance commit share the correction/snapshot fence.
    await repo._lock_child_lineage(child_id)
    questionnaire_id = await db.scalar(
        select(models.ChildQuestionnaireSession.id)
        .where(
            models.ChildQuestionnaireSession.child_profile_id == child_id,
            models.ChildQuestionnaireSession.owner_user_id == owner,
            models.ChildQuestionnaireSession.status == "completed",
        )
        .order_by(models.ChildQuestionnaireSession.completed_at.desc(), models.ChildQuestionnaireSession.id.desc())
        .limit(1)
    )
    if questionnaire_id is None:
        raise HTTPException(status_code=409, detail="Complete the current questionnaire first")
    lineage = await repo.resolve_current_generation_lineage(
        owner_user_id=owner, child_profile_id=child_id, questionnaire_session_id=questionnaire_id
    )
    result = await repo.create_generation_idempotently(
        owner_user_id=owner,
        child_profile_id=child_id,
        parent_chart_id=lineage.parent_chart_id,
        child_chart_version_id=lineage.child_chart_version_id,
        questionnaire_session_id=lineage.questionnaire_session_id,
        operation="full_report",
        idempotency_key=key,
        source_report_id=report_id,
        operation_payload={"scope": scope},
    )
    await db.commit()
    task_id = await _dispatch_accepted_generation(
        db, repository=repo, generation_id=result.generation.generation_id, dispatcher=dispatcher
    )
    return ChildGenerationAccepted(
        result.generation.generation_id, result.generation.status, result.generation.report_id, result.created, task_id
    )


async def accept_age_update(
    db: AsyncSession,
    *,
    owner: UUID,
    child_id: UUID,
    report_id: UUID,
    expected_version: int,
    key: str,
    dispatcher: ChildGenerationDispatcher,
) -> ChildGenerationAccepted:
    version = await db.scalar(
        select(models.ChildReport.version).where(
            models.ChildReport.id == report_id, models.ChildReport.child_profile_id == child_id
        )
    )
    if version is None:
        raise not_found()
    if version != expected_version:
        raise HTTPException(status_code=409, detail="Core report version changed")
    # Resolve a replay before server-date defaults or supporting snapshot writes.
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"child-api-age:{owner}:{key}"}
    )
    existing = await db.scalar(
        select(models.ChildGeneration).where(
            models.ChildGeneration.owner_user_id == owner,
            models.ChildGeneration.operation == "age_update",
            models.ChildGeneration.idempotency_key == key,
        )
    )
    if existing is not None:
        if existing.child_profile_id != child_id or existing.source_report_id != report_id:
            raise ChildIdempotencyTargetMismatchError("Age update retry differs")
        return ChildGenerationAccepted(
            existing.generation_id, existing.status, report_id, False, existing.celery_task_id
        )
    child = await db.get(models.ChildProfile, child_id)
    if child is None:
        raise not_found()
    now = datetime.now(UTC)
    age = resolve_child_age(birth_date=child.birth_date, as_of=now, timezone_name=child.timezone)
    # Only bounded age-appropriate adult actions, never client text/answers/prose.
    payload = {
        "contract_version": "child-age-guidance-http-1",
        "age_stage": age.age_stage,
        "recommended_actions": [
            {
                "action_code": _AGE_ACTIONS[age.age_stage],
                "topic": "age_support",
                "applicability": age.age_stage,
                "reason_code": f"age_stage_{age.age_stage.replace('-', '_')}",
            }
        ],
    }
    return await accept_age_update_generation(
        db,
        owner_user_id=owner,
        child_profile_id=child_id,
        source_report_id=report_id,
        idempotency_key=key,
        guidance_rules_version=RESOLVER_VERSION,
        payload=payload,
        dispatcher=dispatcher,
        now=now,
    )


async def questionnaire_response(
    db: AsyncSession, draft: QuestionnaireDraft | QuestionnaireCompletion
) -> schemas.ChildQuestionnaireResponse:
    row = draft.session
    age = await db.get(models.ChildAgeSnapshot, row.age_snapshot_id)
    if age is None:
        raise not_found()
    questions = questions_for_age_stage(cast(AgeStage, age.age_stage))
    return schemas.ChildQuestionnaireResponse(
        session_id=row.id,
        child_id=row.child_profile_id,
        age_snapshot_id=row.age_snapshot_id,
        age_stage=age.age_stage,
        status=row.status,
        questionnaire_version=row.questionnaire_version,
        answer_version=row.answer_version,
        context_version=row.context_version,
        consent_version=row.consent_version,
        required_question_ids=[q.key for q in questions if q.required],
        missing_required=[
            q.key for q in questions if q.required and q.key not in {a.question_key for a in draft.answers}
        ],
        questions=[
            schemas.QuestionResponse(
                key=q.key,
                prompt=q.prompt_ru,
                required=q.required,
                options=[schemas.QuestionOptionResponse(code=o.code, label=o.label_ru) for o in q.options],
            )
            for q in questions
        ],
        answers=[
            schemas.AnswerRequest(question_key=a.question_key, option=str(a.answer["option"])) for a in draft.answers
        ],
        completed_at=row.completed_at,
    )
