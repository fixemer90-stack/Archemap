"""Billing module — invoices, billing cycles."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.payments.schemas import BillingAccessResponse
from app.modules.payments.service import PaymentsService

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/access", response_model=BillingAccessResponse)
async def get_billing_access(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> BillingAccessResponse:
    """Return current backend-owned billing/access state for the user."""
    return await PaymentsService(db).get_billing_access_state(current_user)
