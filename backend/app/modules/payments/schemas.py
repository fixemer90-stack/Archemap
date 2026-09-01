"""Payments schemas — Pydantic models for API requests/responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreatePaymentRequest(BaseModel):
    """Request to create a payment for a server-priced product."""

    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(..., min_length=1, max_length=80, description="Server-side product/plan identifier")
    return_url: str = Field("", description="URL to redirect after payment")


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


class BillingPaymentSummary(BaseModel):
    """Safe latest payment summary for billing access UI."""

    id: str
    product_id: str | None
    product: str | None
    status: str
    created_at: datetime
    paid_at: datetime | None


class BillingEntitlementSummary(BaseModel):
    """Safe entitlement summary for billing access UI."""

    product: str
    status: str
    starts_at: datetime | None
    expires_at: datetime | None


class BillingAccessResponse(BaseModel):
    """Current backend-owned billing/access state for the user."""

    account_tier: str
    access_state: str
    entitlements: list[BillingEntitlementSummary]
    latest_payment: BillingPaymentSummary | None
