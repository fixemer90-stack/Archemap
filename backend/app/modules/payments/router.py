"""Payments router — API endpoints for payments and webhooks."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.payments.schemas import (
    CreatePaymentRequest,
    PaymentListResponse,
    PaymentResponse,
    WebhookEventResponse,
)
from app.modules.payments.service import PaymentsService

logger = structlog.get_logger()

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse)
async def create_payment(
    body: CreatePaymentRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> PaymentResponse:
    """Create a new payment.

    Returns payment details including confirmation_url for redirect.
    """
    service = PaymentsService(db)
    payment = await service.create_payment(
        user_id=current_user,
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        metadata=body.metadata,
        return_url=body.return_url,
    )

    confirmation_url = None
    if payment.metadata_json:
        confirmation_url = payment.metadata_json.get("confirmation_url")

    return PaymentResponse(
        id=str(payment.id),
        provider=payment.provider,
        provider_payment_id=payment.provider_payment_id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        description=payment.description,
        confirmation_url=confirmation_url,
        payment_method_type=payment.payment_method_type,
        paid_at=payment.paid_at,
        created_at=payment.created_at,
    )


@router.get("", response_model=PaymentListResponse)
async def list_payments(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
    limit: int = 10,
    offset: int = 0,
) -> PaymentListResponse:
    """List payments for the current user."""
    service = PaymentsService(db)
    payments, total = await service.list_payments(
        user_id=current_user,
        limit=limit,
        offset=offset,
    )
    return PaymentListResponse(
        items=[
            PaymentResponse(
                id=str(p.id),
                provider=p.provider,
                provider_payment_id=p.provider_payment_id,
                amount=p.amount,
                currency=p.currency,
                status=p.status,
                description=p.description,
                confirmation_url=p.metadata_json.get("confirmation_url") if p.metadata_json else None,
                payment_method_type=p.payment_method_type,
                paid_at=p.paid_at,
                created_at=p.created_at,
            )
            for p in payments
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> PaymentResponse:
    """Get payment by ID."""
    service = PaymentsService(db)
    payment = await service.get_payment(payment_id, current_user)

    confirmation_url = None
    if payment.metadata_json:
        confirmation_url = payment.metadata_json.get("confirmation_url")

    return PaymentResponse(
        id=str(payment.id),
        provider=payment.provider,
        provider_payment_id=payment.provider_payment_id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        description=payment.description,
        confirmation_url=confirmation_url,
        payment_method_type=payment.payment_method_type,
        paid_at=payment.paid_at,
        created_at=payment.created_at,
    )


# ── Webhooks ─────────────────────────────────────────────────────────


@router.post("/webhooks/yookassa", response_model=None)
async def yookassa_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_signature: str | None = Header(None, alias="X-Signature"),
) -> WebhookEventResponse | JSONResponse:
    """Handle YooKassa webhook events.

    YooKassa sends events when payment status changes.
    We verify the signature and update the payment record.
    """
    body = await request.body()

    # Verify signature
    from app.modules.payments.providers.yookassa import YooKassaProvider

    yookassa = YooKassaProvider()

    if x_signature and not yookassa.verify_webhook(body, x_signature):
        logger.warning("yookassa_webhook_invalid_signature")
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid signature"},
        )

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON"},
        )

    # Process webhook
    service = PaymentsService(db)
    result = await service.handle_webhook(provider="yookassa", payload=payload)

    return WebhookEventResponse(
        processed=result["processed"],
        payment_id=result.get("payment_id"),
        status=result.get("status"),
        message=result["message"],
    )
