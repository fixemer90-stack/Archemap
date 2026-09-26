"""Async, ownership-protected Career questionnaire and report API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.modules.authorization.service import EntitlementsService
from app.modules.career import models
from app.modules.career.access import CareerAccessPolicy
from app.modules.career.api_runtime import (
    build_generation_status_payload,
    build_locked_career_payload,
    build_progressive_report_payload,
    build_report_history_payload,
    build_sections_payload,
)
from app.modules.career.api_schemas import (
    CareerErrorResponse,
    CareerGenerationAcceptedResponse,
    CareerGenerationStatusResponse,
    CareerLockedErrorResponse,
    CareerReportHistoryResponse,
    CareerReportResponse,
    CareerSectionsResponse,
    CreateCareerReportRequest,
    QuestionnaireAnswersRequest,
    QuestionnaireCurrentResponse,
    QuestionnaireResponse,
    RegenerateCareerReportRequest,
)
from app.modules.career.contracts import career_access_operation
from app.modules.career.observability import career_telemetry
from app.modules.career.questionnaire import (
    CONTEXT_VERSION,
    QUESTION_BANK,
    QUESTIONNAIRE_VERSION,
    CareerQuestionnaireCompleted,
    CareerQuestionnaireDraft,
    build_answer_rows,
    complete_questionnaire_session,
)
from app.modules.career.repository import CareerGenerationTargetMismatchError, CareerRepository
from app.modules.payments.service import PaymentsService
from app.modules.profiles.models import PersonProfile

router = APIRouter(prefix="/career", tags=["career"])
_ERRORS: dict[int | str, dict[str, Any]] = {
    402: {"model": CareerLockedErrorResponse},
    404: {"model": CareerErrorResponse},
    409: {"model": CareerErrorResponse},
    422: {"model": CareerErrorResponse},
    503: {"model": CareerErrorResponse},
}
_PDF_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "Career report PDF rendered from the persisted owned report",
        "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        "headers": {
            "Content-Disposition": {
                "description": "Attachment filename",
                "schema": {"type": "string"},
            }
        },
    },
    **_ERRORS,
}
_IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=120)]


@router.get(
    "/questionnaires/current",
    response_model=QuestionnaireCurrentResponse,
    responses=_ERRORS,
)
@career_access_operation("questionnaire")
async def get_current_questionnaire(
    profile_id: Annotated[UUID, Query()],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> dict[str, Any]:
    _require_feature_enabled()
    await _require_career_access(db=db, user_id=current_user)
    repository = CareerRepository(db)
    profile = await repository.get_profile_for_person(profile_id=profile_id, user_id=current_user)
    if profile is None:
        chart = await repository.get_latest_chart_for_person(profile_id=profile_id, user_id=current_user)
        if chart is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile or v2 chart not found")
        profile = models.CareerProfile(
            user_id=current_user,
            profile_id=profile_id,
            chart_id=chart.id,
            generation_id=uuid4(),
            idempotency_key=f"questionnaire:{profile_id}",
            status="questionnaire_draft",
            version=1,
            scoring_version="career-mvp-1",
            reference_version="career-ref-1",
            questionnaire_version=QUESTIONNAIRE_VERSION,
        )
        await repository.add(profile)
        await repository.flush()
    questionnaire = await repository.get_questionnaire_session(
        career_profile_id=profile.id,
        questionnaire_version=QUESTIONNAIRE_VERSION,
    )
    if questionnaire is None:
        questionnaire = models.CareerQuestionnaireSession(
            career_profile_id=profile.id,
            chart_id=profile.chart_id,
            status="draft",
            questionnaire_version=QUESTIONNAIRE_VERSION,
            context_version=CONTEXT_VERSION,
            consent_version="career-consent-1",
        )
        await repository.add(questionnaire)
        await repository.flush()
    await db.commit()
    answers = await repository.list_questionnaire_answers(questionnaire.id)
    return _questionnaire_payload(profile=profile, questionnaire=questionnaire, answer_rows=answers)


@router.put(
    "/questionnaires/{session_id}/answers",
    response_model=QuestionnaireResponse,
    responses=_ERRORS,
)
@career_access_operation("questionnaire")
async def put_questionnaire_answers(
    session_id: UUID,
    body: QuestionnaireAnswersRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> dict[str, Any]:
    _require_feature_enabled()
    await _require_career_access(db=db, user_id=current_user)
    repository = CareerRepository(db)
    questionnaire = await _load_owned_questionnaire(repository, session_id=session_id, user_id=current_user)
    if questionnaire.status == "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Questionnaire is already completed")
    rows = build_answer_rows(
        questionnaire_session_id=questionnaire.id,
        chart_id=questionnaire.chart_id,
        answers=body.answers,
    )
    await repository.replace_questionnaire_answers(questionnaire_session_id=questionnaire.id, answers=rows)
    await db.commit()
    career_telemetry.record(stage="questionnaire", outcome="draft_saved", operation="save")
    return _questionnaire_update_payload(questionnaire=questionnaire, answers=body.answers)


@router.post(
    "/questionnaires/{session_id}/complete",
    response_model=QuestionnaireResponse,
    responses=_ERRORS,
)
@career_access_operation("questionnaire")
async def complete_questionnaire(
    session_id: UUID,
    idempotency_key: _IdempotencyKey,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> dict[str, Any]:
    _require_feature_enabled()
    await _require_career_access(db=db, user_id=current_user)
    repository = CareerRepository(db)
    questionnaire = await _load_owned_questionnaire(repository, session_id=session_id, user_id=current_user)
    answer_rows = await repository.list_questionnaire_answers(questionnaire.id)
    draft = _draft_from_rows(answer_rows)
    try:
        completed = CareerQuestionnaireCompleted.model_validate(draft.model_dump())
        complete_questionnaire_session(
            questionnaire,
            answers=completed,
            idempotency_key=idempotency_key,
            completed_at=datetime.now(UTC),
        )
    except ValueError as exc:
        code = status.HTTP_409_CONFLICT if "conflicting" in str(exc) else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    await db.commit()
    career_telemetry.record(stage="questionnaire", outcome="completed", operation="complete")
    return _questionnaire_update_payload(questionnaire=questionnaire, answers=completed)


@router.post(
    "/reports",
    response_model=CareerGenerationAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_ERRORS,
)
@career_access_operation("create")
async def create_career_report(
    body: CreateCareerReportRequest,
    idempotency_key: _IdempotencyKey,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> JSONResponse:
    _require_feature_enabled()
    await _require_career_access(db=db, user_id=current_user)
    repository = CareerRepository(db)
    profile = await repository.get_profile_for_person(profile_id=body.profile_id, user_id=current_user)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career profile not found")
    questionnaire = await repository.get_questionnaire_session(
        career_profile_id=profile.id,
        questionnaire_version=QUESTIONNAIRE_VERSION,
    )
    if questionnaire is None or questionnaire.status != "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Questionnaire is not completed")
    try:
        result = await repository.create_generation_idempotently(
            generation_id=uuid4(),
            user_id=current_user,
            career_profile_id=profile.id,
            chart_id=profile.chart_id,
            operation="create",
            idempotency_key=idempotency_key,
            source_report_id=None,
            diagnostics={},
        )
    except CareerGenerationTargetMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await db.commit()
    if result.created:
        await _enqueue_generation(db=db, generation=result.generation, section_keys=[])
    return _accepted_response(result.generation)


@router.get(
    "/generations/{generation_id}",
    response_model=CareerGenerationStatusResponse,
    responses=_ERRORS,
)
@career_access_operation("generate")
async def get_career_generation(
    generation_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> dict[str, Any]:
    repository = CareerRepository(db)
    generation = await repository.get_generation_for_user(generation_id=generation_id, user_id=current_user)
    if generation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found")
    await _require_career_access(db=db, user_id=current_user)
    report = await repository.get_report_by_generation_id(generation.generation_id)
    segments = await repository.list_segments_for_generation(generation.generation_id)
    return build_generation_status_payload(generation=generation, report=report, segments=segments)


@router.get("/reports/{report_id}", response_model=CareerReportResponse, responses=_ERRORS)
@career_access_operation("read")
async def get_career_report(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> dict[str, Any]:
    repository = CareerRepository(db)
    report = await _load_owned_report(repository, report_id=report_id, user_id=current_user)
    await _require_career_access(db=db, user_id=current_user)
    segments = await repository.list_segments_for_generation(report.generation_id)
    return build_progressive_report_payload(report=report, segments=segments)


@router.get("/reports/{report_id}/sections", response_model=CareerSectionsResponse, responses=_ERRORS)
@career_access_operation("read")
async def get_career_report_sections(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> dict[str, Any]:
    repository = CareerRepository(db)
    report = await _load_owned_report(repository, report_id=report_id, user_id=current_user)
    await _require_career_access(db=db, user_id=current_user)
    segments = await repository.list_segments_for_generation(report.generation_id)
    return build_sections_payload(segments=segments)


@router.get(
    "/reports/{report_id}/versions",
    response_model=CareerReportHistoryResponse,
    responses=_ERRORS,
)
@career_access_operation("versions")
async def get_career_report_versions(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> dict[str, Any]:
    repository = CareerRepository(db)
    report = await _load_owned_report(repository, report_id=report_id, user_id=current_user)
    await _require_career_access(db=db, user_id=current_user)
    reports = await repository.list_report_history_for_user(report.career_profile_id, current_user)
    return build_report_history_payload(requested_report=report, reports=reports)


@router.post(
    "/reports/{report_id}/regenerate",
    response_model=CareerGenerationAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_ERRORS,
)
@career_access_operation("regenerate")
async def regenerate_career_report(
    report_id: UUID,
    body: RegenerateCareerReportRequest,
    idempotency_key: _IdempotencyKey,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> JSONResponse:
    _require_feature_enabled()
    repository = CareerRepository(db)
    report = await _load_owned_report(repository, report_id=report_id, user_id=current_user)
    await _require_career_access(db=db, user_id=current_user)
    try:
        result = await repository.create_generation_idempotently(
            generation_id=uuid4(),
            user_id=current_user,
            career_profile_id=report.career_profile_id,
            chart_id=report.chart_id,
            source_report_id=report.id,
            operation="regenerate",
            idempotency_key=idempotency_key,
            diagnostics={"section_keys": body.section_keys},
        )
    except CareerGenerationTargetMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await db.commit()
    if result.created:
        await _enqueue_generation(db=db, generation=result.generation, section_keys=body.section_keys)
    return _accepted_response(result.generation)


@router.get("/reports/{report_id}/pdf", response_class=Response, responses=_PDF_RESPONSES)
@career_access_operation("pdf")
async def get_career_report_pdf(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> Response:
    repository = CareerRepository(db)
    report = await _load_owned_report(repository, report_id=report_id, user_id=current_user)
    await _require_career_access(db=db, user_id=current_user)
    segments = await repository.list_segments_for_generation(report.generation_id)
    payload = build_progressive_report_payload(report=report, segments=segments)
    career_profile = await repository.get_profile_for_user(report.career_profile_id, current_user)
    profile_name = ""
    if career_profile is not None:
        result = await db.execute(
            select(PersonProfile.name).where(
                PersonProfile.id == career_profile.profile_id,
                PersonProfile.user_id == current_user,
            )
        )
        profile_name = result.scalar_one_or_none() or ""
    from app.modules.career.pdf import generate_career_report_pdf

    pdf = generate_career_report_pdf(report_payload=payload, profile_name=profile_name)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="astrotype-career-{report.id}.pdf"'},
    )


def _require_feature_enabled() -> None:
    if not settings.CAREER_REPORT_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career report is not enabled")


async def _require_career_access(*, db: AsyncSession, user_id: UUID) -> None:
    await PaymentsService(db).reconcile_latest_pending_provider_payment(user_id)
    decision = await CareerAccessPolicy(EntitlementsService(db)).check(user_id)
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=build_locked_career_payload(reason=decision.reason or "missing_career_access"),
        )


async def _load_owned_questionnaire(
    repository: CareerRepository,
    *,
    session_id: UUID,
    user_id: UUID,
) -> models.CareerQuestionnaireSession:
    questionnaire = await repository.get_questionnaire_session_for_user(session_id=session_id, user_id=user_id)
    if questionnaire is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Questionnaire not found")
    return questionnaire


async def _load_owned_report(
    repository: CareerRepository,
    *,
    report_id: UUID,
    user_id: UUID,
) -> models.CareerReport:
    report = await repository.get_report_for_user(report_id, user_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


def _draft_from_rows(rows: list[models.CareerAnswer]) -> CareerQuestionnaireDraft:
    return CareerQuestionnaireDraft.model_validate({row.question_key: row.answer.get("value") for row in rows})


def _questionnaire_payload(
    *,
    profile: models.CareerProfile,
    questionnaire: models.CareerQuestionnaireSession,
    answer_rows: list[models.CareerAnswer],
) -> dict[str, Any]:
    draft = _draft_from_rows(answer_rows)
    return {
        "contract_version": "career_questionnaire_v1",
        "session_id": questionnaire.id,
        "career_profile_id": profile.id,
        "profile_id": profile.profile_id,
        "chart_id": profile.chart_id,
        "status": questionnaire.status,
        "questionnaire_version": questionnaire.questionnaire_version,
        "questions": [question.__dict__ for question in QUESTION_BANK],
        "answers": draft.model_dump(mode="json", exclude_none=True),
        "missing_required": list(draft.missing_required),
    }


def _questionnaire_update_payload(
    *,
    questionnaire: models.CareerQuestionnaireSession,
    answers: CareerQuestionnaireDraft,
) -> dict[str, Any]:
    return {
        "contract_version": "career_questionnaire_v1",
        "session_id": questionnaire.id,
        "status": questionnaire.status,
        "answers": answers.model_dump(mode="json", exclude_none=True),
        "missing_required": list(answers.missing_required),
    }


def _accepted_response(generation: models.CareerGeneration) -> JSONResponse:
    payload = CareerGenerationAcceptedResponse(
        status=generation.status,
        generation_id=generation.generation_id,
        report_id=generation.report_id,
        links={
            "generation": f"/api/v1/career/generations/{generation.generation_id}",
            **(
                {"report": f"/api/v1/career/reports/{generation.report_id}"} if generation.report_id is not None else {}
            ),
        },
    )
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=payload.model_dump(mode="json"))


async def _enqueue_generation(
    *,
    db: AsyncSession,
    generation: models.CareerGeneration,
    section_keys: list[str],
) -> None:
    from workers.tasks.career import generate_career_report

    try:
        task = generate_career_report.delay(
            generation_id=str(generation.generation_id),
            section_keys=section_keys,
        )
        generation.celery_task_id = str(getattr(task, "id", "")) or None
        await db.commit()
    except Exception as exc:
        generation.status = "failed"
        generation.diagnostics = {"error": "career_queue_unavailable"}
        await db.commit()
        career_telemetry.record(
            stage="deterministic",
            outcome="failed",
            operation=generation.operation,
            error_code="career_queue_unavailable",
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Career queue unavailable") from exc
