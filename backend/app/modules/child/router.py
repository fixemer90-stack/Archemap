"""Authenticated owner-only Child API; paid gates precede protected reads."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.security import APIKeyCookie
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.modules.authorization.service import EntitlementsService
from app.modules.child import api_schemas as schemas
from app.modules.child import api_service as api
from app.modules.child import models
from app.modules.child.access import ChildAccessPolicy
from app.modules.child.api_schemas import ChildGenerationAcceptedResponse, CreateChildReportRequest
from app.modules.child.contracts import child_access_operation
from app.modules.child.dispatch import dispatch_child_generation
from app.modules.child.questionnaire import QUESTIONNAIRE_VERSION, AnswerInput
from app.modules.child.questionnaire_persistence import ChildQuestionnaireRepository, QuestionnaireDraft
from app.modules.child.repository import ChildIdempotencyTargetMismatchError, ChildLineageMismatchError, ChildRepository
from app.modules.child.service import accept_full_generation

DB = Annotated[AsyncSession, Depends(get_db)]
_cookie_scheme = APIKeyCookie(name="access_token", scheme_name="ChildCookieAuth", auto_error=False)


async def authenticated_owner(
    user: Annotated[UUID, Depends(get_current_user)],
    cookie: Annotated[str | None, Depends(_cookie_scheme)],
) -> UUID:
    """Document cookie OR Bearer while delegating verification to canonical auth."""
    del cookie
    return user


Owner = Annotated[UUID, Depends(authenticated_owner)]
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=120)]


class ChildAPIRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def handle(request: Request) -> Response:
            try:
                response = await original(request)
            except RequestValidationError as exc:
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": [
                            {
                                "loc": [*error["loc"][:-1], "unknown_field"]
                                if error["type"] == "extra_forbidden"
                                else list(error["loc"]),
                                "type": error["type"],
                                "msg": "Invalid Child request",
                            }
                            for error in exc.errors()
                        ]
                    },
                    headers={"Cache-Control": "private, no-store"},
                )
            except ChildIdempotencyTargetMismatchError:
                response = JSONResponse(
                    status_code=409, content={"detail": "Idempotency key was already used for another target"}
                )
            except ChildLineageMismatchError:
                response = JSONResponse(status_code=404, content={"detail": "Child resource not found"})
            except ValueError:
                response = JSONResponse(status_code=422, content={"detail": "Invalid Child request or source data"})
            except HTTPException as exc:
                response = JSONResponse(
                    status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers
                )
            response.headers["Cache-Control"] = "private, no-store"
            return response

        return handle


router = APIRouter(
    prefix="/child",
    tags=["child"],
    route_class=ChildAPIRoute,
    responses={code: {"model": schemas.ChildErrorResponse} for code in (401, 402, 404, 409, 422, 503)},
)


async def paid(db: AsyncSession, owner: UUID, *, mutation: bool = False) -> None:
    access = await ChildAccessPolicy(EntitlementsService(db)).check(owner)
    if not access.allowed:
        raise HTTPException(status_code=402, detail=access.to_payload())
    if mutation and not settings.CHILD_REPORT_ENABLED:
        raise HTTPException(status_code=503, detail="Child Report is not enabled")


async def guard(
    db: AsyncSession,
    owner: UUID,
    *,
    child_id: UUID | None = None,
    resource: Literal["report", "generation", "questionnaire"] | None = None,
    resource_id: UUID | None = None,
    mutation: bool = False,
    include_archived: bool = False,
) -> UUID:
    child = await api.owned_child_id(
        db, owner, child_id=child_id, resource=resource, resource_id=resource_id, include_archived=include_archived
    )
    await paid(db, owner, mutation=mutation)
    return child


@router.get("/children", response_model=schemas.ChildrenResponse)
@child_access_operation("child_read")
async def list_children(db: DB, current_user: Owner, include_archived: bool = False) -> schemas.ChildrenResponse:
    await paid(db, current_user)
    rows = await db.scalars(
        select(models.ChildProfile)
        .where(
            models.ChildProfile.owner_user_id == current_user,
            models.ChildProfile.status.in_(["active", "archived"] if include_archived else ["active"]),
        )
        .order_by(models.ChildProfile.created_at, models.ChildProfile.id)
    )
    return schemas.ChildrenResponse(children=[await api.child_response(db, child) for child in rows])


@router.post("/children", response_model=schemas.ChildResponse, status_code=201)
@child_access_operation("child_create")
async def create_child(
    payload: schemas.CreateChildRequest, idempotency_key: IdempotencyKey, db: DB, current_user: Owner
) -> schemas.ChildResponse:
    await paid(db, current_user, mutation=True)
    child = await api.create_child(db, current_user, payload, idempotency_key)
    return await api.child_response(db, child)


@router.get("/children/{child_id}", response_model=schemas.ChildResponse)
@child_access_operation("child_read")
async def read_child(
    child_id: UUID, db: DB, current_user: Owner, include_archived: bool = False
) -> schemas.ChildResponse:
    await guard(db, current_user, child_id=child_id, include_archived=include_archived)
    child = await db.get(models.ChildProfile, child_id)
    if child is None:
        raise api.not_found()
    return await api.child_response(db, child)


@router.get(
    "/children/{child_id}/export",
    response_model=schemas.ChildExportResponse,
    responses={403: {"model": schemas.ChildErrorResponse}},
)
@child_access_operation("child_read")
async def export_child(child_id: UUID, request: Request, db: DB, current_user: Owner) -> JSONResponse:
    await guard(db, current_user, child_id=child_id, include_archived=True)
    if settings.APP_ENV == "production" and request.url.scheme != "https":
        raise HTTPException(status_code=403, detail="Secure transport is required")
    from app.modules.child.privacy_export import export_child_domain

    archive = await export_child_domain(db, owner_user_id=current_user, child_profile_id=child_id)
    return JSONResponse(
        content=archive,
        headers={"Content-Disposition": 'attachment; filename="astrotype-child-export.json"'},
    )


@router.patch("/children/{child_id}", response_model=schemas.ChildResponse)
@child_access_operation("child_update")
async def patch_child(
    child_id: UUID, payload: schemas.PatchChildRequest, db: DB, current_user: Owner
) -> schemas.ChildResponse:
    await guard(db, current_user, child_id=child_id, mutation=True)
    child = await api.patch_child(db, current_user, child_id, payload)
    return await api.child_response(db, child)


@router.delete("/children/{child_id}", status_code=204)
@child_access_operation("child_delete")
async def delete_child(
    child_id: UUID, db: DB, current_user: Owner, mode: Literal["archive", "purge"] = "archive"
) -> Response:
    await guard(db, current_user, child_id=child_id, mutation=True, include_archived=True)
    repository = ChildRepository(db)
    if mode == "purge":
        await repository.purge_child_domain(owner_user_id=current_user, child_profile_id=child_id)
    else:
        await repository.archive_child(owner_user_id=current_user, child_profile_id=child_id)
    await db.commit()
    return Response(status_code=204)


@router.get("/children/{child_id}/questionnaires/current", response_model=schemas.ChildQuestionnaireResponse)
@child_access_operation("questionnaire")
async def current_questionnaire(child_id: UUID, db: DB, current_user: Owner) -> schemas.ChildQuestionnaireResponse:
    await guard(db, current_user, child_id=child_id)
    # Existing pinned draft/completed data remain readable on rollout rollback.
    existing = await db.scalar(
        select(models.ChildQuestionnaireSession)
        .where(
            models.ChildQuestionnaireSession.child_profile_id == child_id,
            models.ChildQuestionnaireSession.owner_user_id == current_user,
            models.ChildQuestionnaireSession.questionnaire_version == QUESTIONNAIRE_VERSION,
        )
        .order_by(models.ChildQuestionnaireSession.created_at.desc(), models.ChildQuestionnaireSession.id.desc())
        .limit(1)
    )
    if not settings.CHILD_REPORT_ENABLED:
        if existing is None:
            raise HTTPException(status_code=503, detail="Child Report is not enabled")
        repo = ChildQuestionnaireRepository(db)
        return await api.questionnaire_response(
            db, QuestionnaireDraft(existing, await repo._answers(existing.id), False)
        )
    snapshot = await ChildRepository(db).create_age_snapshot_idempotently(
        owner_user_id=current_user, child_profile_id=child_id
    )
    if existing is not None and existing.age_snapshot_id == snapshot.snapshot.id and existing.status == "completed":
        draft = QuestionnaireDraft(existing, await ChildQuestionnaireRepository(db)._answers(existing.id), False)
    else:
        draft = await ChildQuestionnaireRepository(db).get_or_create_current_draft(
            owner_user_id=current_user, child_profile_id=child_id, age_snapshot_id=snapshot.snapshot.id
        )
    await db.commit()
    return await api.questionnaire_response(db, draft)


@router.put("/questionnaires/{session_id}/answers", response_model=schemas.ChildQuestionnaireResponse)
@child_access_operation("questionnaire")
async def save_answers(
    session_id: UUID, payload: schemas.SaveAnswersRequest, db: DB, current_user: Owner
) -> schemas.ChildQuestionnaireResponse:
    child_id = await guard(db, current_user, resource="questionnaire", resource_id=session_id, mutation=True)
    draft = await ChildQuestionnaireRepository(db).save_draft_answers(
        owner_user_id=current_user,
        child_profile_id=child_id,
        questionnaire_session_id=session_id,
        answers=tuple(AnswerInput(**item.model_dump()) for item in payload.answers),
    )
    await db.commit()
    return await api.questionnaire_response(db, draft)


@router.post("/questionnaires/{session_id}/complete", response_model=schemas.ChildQuestionnaireResponse)
@child_access_operation("questionnaire")
async def complete_questionnaire(
    session_id: UUID,
    idempotency_key: IdempotencyKey,
    db: DB,
    current_user: Owner,
    payload: schemas.CompleteChildQuestionnaireRequest = Body(
        default_factory=schemas.CompleteChildQuestionnaireRequest
    ),
) -> schemas.ChildQuestionnaireResponse:
    del payload
    child_id = await guard(db, current_user, resource="questionnaire", resource_id=session_id, mutation=True)
    completed = await ChildQuestionnaireRepository(db).complete_idempotently(
        owner_user_id=current_user,
        child_profile_id=child_id,
        questionnaire_session_id=session_id,
        completion_idempotency_key=idempotency_key,
    )
    await db.commit()
    return await api.questionnaire_response(db, completed)


@router.post("/reports", response_model=ChildGenerationAcceptedResponse, status_code=202)
@child_access_operation("report_create")
async def create_child_report(
    payload: CreateChildReportRequest, idempotency_key: IdempotencyKey, db: DB, current_user: Owner
) -> ChildGenerationAcceptedResponse:
    # Cross-child/session mismatches are concealed before paid payload work.
    await api.owned_child_id(
        db,
        current_user,
        child_id=payload.child_profile_id,
        resource="questionnaire",
        resource_id=payload.questionnaire_session_id,
    )
    await paid(db, current_user, mutation=True)
    accepted = await accept_full_generation(
        db,
        owner_user_id=current_user,
        child_profile_id=payload.child_profile_id,
        questionnaire_session_id=payload.questionnaire_session_id,
        idempotency_key=idempotency_key,
        dispatcher=dispatch_child_generation,
    )
    return ChildGenerationAcceptedResponse(
        generation_id=accepted.generation_id, status=accepted.status, report_id=accepted.report_id
    )


@router.get("/generations/{generation_id}", response_model=schemas.GenerationResponse)
@child_access_operation("generation_status")
async def generation_status(generation_id: UUID, db: DB, current_user: Owner) -> schemas.GenerationResponse:
    child_id = await guard(db, current_user, resource="generation", resource_id=generation_id)
    row = (
        await db.execute(
            select(
                models.ChildGeneration.generation_id,
                models.ChildGeneration.status,
                func.coalesce(models.ChildGeneration.report_id, models.ChildGeneration.source_report_id).label(
                    "report_id"
                ),
                models.ChildGeneration.operation,
                models.ChildGeneration.last_error_code.label("error_code"),
                models.ChildGeneration.next_retry_at,
            ).where(models.ChildGeneration.generation_id == generation_id)
        )
    ).one()
    return schemas.GenerationResponse(child_id=child_id, **dict(row._mapping))


async def report_presentation(
    db: AsyncSession, owner: UUID, report_id: UUID, age_snapshot_id: UUID | None
) -> dict[str, Any]:
    await guard(db, owner, resource="report", resource_id=report_id)
    from app.modules.child.presentation import build_child_report_presentation

    return await build_child_report_presentation(
        db, owner_user_id=owner, report_id=report_id, age_snapshot_id=age_snapshot_id
    )


@router.get("/reports/{report_id}", response_model=schemas.ChildReportResponse)
@child_access_operation("report_read")
async def read_report(
    report_id: UUID, db: DB, current_user: Owner, age_snapshot_id: UUID | None = None
) -> schemas.ChildReportResponse:
    presentation = await report_presentation(db, current_user, report_id, age_snapshot_id)
    row = (
        await db.execute(
            select(
                models.ChildReport.child_profile_id,
                models.ChildReport.generation_id,
                models.ChildReport.status,
                models.ChildProfile.display_name,
            )
            .join(models.ChildProfile, models.ChildProfile.id == models.ChildReport.child_profile_id)
            .where(models.ChildReport.id == report_id)
        )
    ).one()
    return schemas.ChildReportResponse(
        report_id=report_id,
        child_id=row.child_profile_id,
        display_name=row.display_name,
        generation_id=UUID(presentation["metadata"]["generation_id"]),
        status=str(presentation.get("status", row.status)),
        presentation=presentation,
    )


@router.get("/reports/{report_id}/sections", response_model=schemas.SectionsResponse)
@child_access_operation("report_read")
async def read_sections(
    report_id: UUID, db: DB, current_user: Owner, age_snapshot_id: UUID | None = None
) -> schemas.SectionsResponse:
    presentation = await report_presentation(db, current_user, report_id, age_snapshot_id)
    return schemas.SectionsResponse(report_id=report_id, sections=presentation.get("sections", []))


@router.get("/reports/{report_id}/versions", response_model=schemas.VersionsResponse)
@child_access_operation("report_versions")
async def report_versions(report_id: UUID, db: DB, current_user: Owner) -> schemas.VersionsResponse:
    child_id = await guard(db, current_user, resource="report", resource_id=report_id)
    rows = await db.execute(
        select(
            models.ChildReport.id,
            models.ChildReport.generation_id,
            models.ChildReport.version,
            models.ChildReport.status,
            models.ChildReport.created_at,
        )
        .where(models.ChildReport.child_profile_id == child_id)
        .order_by(models.ChildReport.version.desc())
    )
    return schemas.VersionsResponse(
        versions=[
            schemas.ChildReportVersionResponse(
                report_id=r.id,
                generation_id=r.generation_id,
                core_report_version=r.version,
                status=r.status,
                created_at=r.created_at,
            )
            for r in rows
        ]
    )


@router.get("/reports/{report_id}/age-snapshots", response_model=schemas.AgeSnapshotsResponse)
@child_access_operation("age_snapshots")
async def age_snapshots(report_id: UUID, db: DB, current_user: Owner) -> schemas.AgeSnapshotsResponse:
    child_id = await guard(db, current_user, resource="report", resource_id=report_id)
    core_age_ids = (
        select(models.ChildGuidanceFacts.age_snapshot_id)
        .join(models.ChildReport, models.ChildReport.generation_id == models.ChildGuidanceFacts.generation_id)
        .where(models.ChildReport.id == report_id, models.ChildGuidanceFacts.child_profile_id == child_id)
    )
    update_age_ids = select(models.ChildReportAgeGuidance.age_snapshot_id).where(
        models.ChildReportAgeGuidance.report_id == report_id,
        models.ChildReportAgeGuidance.child_profile_id == child_id,
        models.ChildReportAgeGuidance.status == "age_update_ready",
    )
    rows = await db.scalars(
        select(models.ChildAgeSnapshot)
        .where(
            models.ChildAgeSnapshot.child_profile_id == child_id,
            models.ChildAgeSnapshot.id.in_(core_age_ids.union(update_age_ids)),
        )
        .order_by(models.ChildAgeSnapshot.as_of_date.desc(), models.ChildAgeSnapshot.id)
    )
    return schemas.AgeSnapshotsResponse(
        age_snapshots=[
            schemas.AgeSnapshotResponse(
                age_snapshot_id=row.id, **{key: getattr(row, key) for key in schemas.AgeResponse.model_fields}
            )
            for row in rows
        ]
    )


@router.post("/reports/{report_id}/regenerate", response_model=ChildGenerationAcceptedResponse, status_code=202)
@child_access_operation("report_regenerate")
async def regenerate_report(
    report_id: UUID, payload: schemas.RegenerateRequest, idempotency_key: IdempotencyKey, db: DB, current_user: Owner
) -> ChildGenerationAcceptedResponse:
    child_id = await guard(db, current_user, resource="report", resource_id=report_id, mutation=True)
    accepted = await api.regenerate(
        db,
        owner=current_user,
        child_id=child_id,
        report_id=report_id,
        scope=payload.scope,
        key=idempotency_key,
        dispatcher=dispatch_child_generation,
    )
    return ChildGenerationAcceptedResponse(
        generation_id=accepted.generation_id, status=accepted.status, report_id=accepted.report_id
    )


@router.post("/reports/{report_id}/age-updates", response_model=ChildGenerationAcceptedResponse, status_code=202)
@child_access_operation("age_update")
async def age_update(
    report_id: UUID, payload: schemas.AgeUpdateRequest, idempotency_key: IdempotencyKey, db: DB, current_user: Owner
) -> ChildGenerationAcceptedResponse:
    child_id = await guard(db, current_user, resource="report", resource_id=report_id, mutation=True)
    accepted = await api.accept_age_update(
        db,
        owner=current_user,
        child_id=child_id,
        report_id=report_id,
        expected_version=payload.expected_core_report_version,
        key=idempotency_key,
        dispatcher=dispatch_child_generation,
    )
    return ChildGenerationAcceptedResponse(
        generation_id=accepted.generation_id, status=accepted.status, report_id=accepted.report_id
    )


@router.get(
    "/reports/{report_id}/pdf",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
            "headers": {
                name: {"schema": {"type": "string"}}
                for name in (
                    "X-Child-Core-Version",
                    "X-Child-Age-Snapshot-Id",
                    "X-Child-Age-As-Of",
                    "X-Child-Presentation-Version",
                )
            },
        }
    },
)
@child_access_operation("pdf")
async def report_pdf(
    report_id: UUID, db: DB, current_user: Owner, age_snapshot_id: Annotated[UUID | None, Query()] = None
) -> Response:
    presentation = await report_presentation(db, current_user, report_id, age_snapshot_id)
    from app.modules.child.pdf import render_child_report_pdf

    content = render_child_report_pdf(presentation)
    metadata = presentation["metadata"]
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="child-report.pdf"',
            "Cache-Control": "private, no-store",
            "X-Child-Core-Version": str(metadata["core_report_version"]),
            "X-Child-Age-Snapshot-Id": str(metadata["age_snapshot_id"]),
            "X-Child-Age-As-Of": str(metadata["as_of_date"]),
            "X-Child-Presentation-Version": str(presentation["contract_version"]),
        },
    )
