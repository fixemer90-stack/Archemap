"""Payments schemas — Pydantic models for API requests/responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreatePaymentRequest(BaseModel):
    """Request to create a payment."""

    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field("RUB", description="Currency code")
    description: str = Field("", max_length=500, description="Payment description")
    return_url: str = Field("", description="URL to redirect after payment")
    metadata: dict[str, Any] | None = Field(None, description="Custom metadata")


class PaymentResponse(BaseModel):
    """Payment response."""

    id: str
    provider: str
    provider_payment_id: str | None
    amount: float
    currency: str
    status: str
    description: str
    confirmation_url: str | None  # URL to redirect user for payment
    payment_method_type: str | None
    paid_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentListResponse(BaseModel):
    """Paginated payment list."""

    items: list[PaymentResponse]
    total: int
    limit: int
    offset: int


class WebhookEventResponse(BaseModel):
    """Webhook processing result."""

    processed: bool
    payment_id: str | None
    status: str | None
    message: str
