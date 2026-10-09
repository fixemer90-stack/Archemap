"""Admin subscription support contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


@dataclass(frozen=True)
class SubscriptionSupportData:
    user_id: UUID
    email: str
    subscription_id: UUID
    plan_code: str
    display_name: str
    status: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    next_billing_at: datetime | None
    latest_payment_id: UUID | None
    latest_payment_status: str | None
    events: tuple[Any, ...]


class SubscriptionEventSummary(BaseModel):
    event_type: str
    effective_at: datetime
    provider_event_id: str | None
    metadata: dict[str, Any]


class SubscriptionSupportResponse(BaseModel):
    user_id: str
    email: str
    subscription_id: str
    plan_code: str
    display_name: str
    status: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    next_billing_at: datetime | None
    latest_payment_id: str | None
    latest_payment_status: str | None
    events: list[SubscriptionEventSummary]


class SubscriptionSupportQuery(BaseModel):
    email: EmailStr


class SubscriptionReconcileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    reason: str = Field(min_length=3, max_length=500)
