"""Minimal asynchronous Child Report creation endpoint for the S11 lifecycle."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.modules.authorization.service import EntitlementsService
from app.modules.child.access import ChildAccessPolicy
from app.modules.child.contracts import child_access_operation
from app.modules.child.dispatch import dispatch_child_generation
from app.modules.child.repository import (
    ChildIdempotencyTargetMismatchError,
    ChildLineageMismatchError,
)
from app.modules.child.service import accept_full_generation

router = APIRouter(prefix="/child/reports", tags=["child"])


class CreateChildReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_profile_id: UUID
    questionnaire_session_id: UUID


class ChildGenerationAcceptedResponse(BaseModel):
    generation_id: UUID
    status: str
    report_id: UUID | None


@router.post(
    "",
    response_model=ChildGenerationAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@child_access_operation("report_create")
async def create_child_report(
    payload: CreateChildReportRequest,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=120),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> ChildGenerationAcceptedResponse:
    if not settings.CHILD_REPORT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Child Report is not enabled",
        )
    access = await ChildAccessPolicy(EntitlementsService(db)).check(current_user)
    if not access.allowed:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=access.to_payload())
    try:
        accepted = await accept_full_generation(
            db,
            owner_user_id=current_user,
            child_profile_id=payload.child_profile_id,
            questionnaire_session_id=payload.questionnaire_session_id,
            idempotency_key=idempotency_key,
            dispatcher=dispatch_child_generation,
        )
    except ChildLineageMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child resource not found",
        ) from exc
    except ChildIdempotencyTargetMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key was already used for another target",
        ) from exc
    return ChildGenerationAcceptedResponse(
        generation_id=accepted.generation_id,
        status=accepted.status,
        report_id=accepted.report_id,
    )
