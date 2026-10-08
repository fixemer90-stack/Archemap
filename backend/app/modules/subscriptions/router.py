"""Authenticated monthly subscription lifecycle endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.subscriptions.schemas import SubscriptionCheckoutRequest, SubscriptionCheckoutResponse
from app.modules.subscriptions.service import SubscriptionsService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("/checkout", response_model=SubscriptionCheckoutResponse)
async def create_subscription_checkout(
    body: SubscriptionCheckoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> SubscriptionCheckoutResponse:
    result = await SubscriptionsService(db).create_checkout(
        user_id=current_user,
        plan_code=body.plan_code,
        return_url=body.return_url,
    )
    return SubscriptionCheckoutResponse(
        subscription_id=str(result.subscription_id),
        payment_id=str(result.payment_id),
        status=result.status,
        confirmation_url=result.confirmation_url,
    )
