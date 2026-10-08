"""Authenticated monthly subscription lifecycle endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.catalog.service import CatalogService
from app.modules.subscriptions.models import Subscription
from app.modules.subscriptions.schemas import (
    SubscriptionActionRequest,
    SubscriptionCheckoutRequest,
    SubscriptionCheckoutResponse,
    SubscriptionResponse,
)
from app.modules.subscriptions.service import SubscriptionsService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _subscription_response(subscription: Subscription) -> SubscriptionResponse:
    plan_code = str(subscription.metadata_json.get("plan_code") or "astrotype_plus_monthly")
    plan = CatalogService().get_subscription_plan(plan_code)
    current_period_end = subscription.current_period_end
    cancel_at_period_end = subscription.cancel_at_period_end
    return SubscriptionResponse(
        id=str(subscription.id),
        plan_code=plan.plan_code,
        display_name=plan.display_name,
        amount=plan.amount,
        currency=plan.currency,
        billing_interval=plan.billing_interval,
        status=subscription.status,
        current_period_start=subscription.current_period_start,
        current_period_end=current_period_end,
        cancel_at_period_end=cancel_at_period_end,
        next_billing_at=current_period_end if not cancel_at_period_end else None,
        grace_until=subscription.grace_until,
    )


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


@router.post("/{subscription_id}/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: UUID,
    body: SubscriptionActionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> SubscriptionResponse:
    subscription = await SubscriptionsService(db).cancel_at_period_end(
        subscription_id=subscription_id,
        user_id=current_user,
        reason=body.reason or "user_request",
    )
    return _subscription_response(subscription)


@router.post("/{subscription_id}/resume", response_model=SubscriptionResponse)
async def resume_subscription(
    subscription_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> SubscriptionResponse:
    subscription = await SubscriptionsService(db).resume(
        subscription_id=subscription_id,
        user_id=current_user,
    )
    return _subscription_response(subscription)
