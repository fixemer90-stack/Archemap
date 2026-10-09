"""Admin module — authenticated support endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_superuser, get_db
from app.modules.admin.schemas import SubscriptionReconcileRequest, SubscriptionSupportResponse
from app.modules.admin.service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/subscriptions/support", response_model=SubscriptionSupportResponse)
async def get_subscription_support(
    email: Annotated[EmailStr, Query()],
    db: Annotated[AsyncSession, Depends(get_db)],
    _operator: Annotated[UUID, Depends(get_current_superuser)],
) -> SubscriptionSupportResponse:
    return await AdminService(db).get_subscription_support(email=str(email))


@router.post("/subscriptions/reconcile", response_model=SubscriptionSupportResponse)
async def reconcile_subscription(
    body: SubscriptionReconcileRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    operator: Annotated[UUID, Depends(get_current_superuser)],
) -> SubscriptionSupportResponse:
    return await AdminService(db).reconcile_subscription(
        email=str(body.email),
        reason=body.reason,
        operator_user_id=operator,
    )
