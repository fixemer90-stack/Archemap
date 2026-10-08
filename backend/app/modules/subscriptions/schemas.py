"""Pydantic contracts for subscription lifecycle APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SubscriptionCheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_code: str = Field(default="astrotype_plus_monthly", max_length=80)
    return_url: str = ""


class SubscriptionCheckoutResponse(BaseModel):
    subscription_id: str
    payment_id: str
    status: str
    confirmation_url: str
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None


class SubscriptionResponse(BaseModel):
    id: str
    plan_code: str
    display_name: str
    amount: float
    currency: str
    billing_interval: str
    status: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    next_billing_at: datetime | None
    grace_until: datetime | None


class SubscriptionActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=500)
