"""Version one internal event registry; never an external analytics payload."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EventType(StrEnum):
    REGISTRATION_COMPLETED = "registration_completed"
    ACCOUNT_VERIFIED = "account_verified"
    BASIC_REPORT_READY = "basic_report_ready"
    CHECKOUT_CREATED = "checkout_created"
    PAYMENT_CONFIRMED = "payment_confirmed"
    REFUND_CONFIRMED = "refund_confirmed"
    SUBSCRIPTION_PERIOD_STARTED = "subscription_period_started"
    RENEWAL_CONFIRMED = "renewal_confirmed"
    RENEWAL_CANCELED = "renewal_canceled"
    REPORT_REQUESTED = "report_requested"
    REPORT_READY = "report_ready"
    REPORT_PARTIAL = "report_partial"
    REPORT_FAILED = "report_failed"
    REPORT_OPENED = "report_opened"
    PROVIDER_USAGE_OBSERVED = "provider_usage_observed"


class Mode(StrEnum):
    UNKNOWN = "unknown"
    TEST = "test"
    LIVE = "live"


class Product(StrEnum):
    SELF = "self"
    CAREER = "career"
    CHILD = "child"
    PLUS = "plus"


class StrictModel(BaseModel):
    model_config = ConfigDict(
        strict=True, extra="forbid", frozen=True, allow_inf_nan=False, revalidate_instances="always"
    )


class Currency(StrEnum):
    USD = "USD"
    RUB = "RUB"
    EUR = "EUR"


class CostBasis(StrEnum):
    OBSERVED = "observed"
    ESTIMATED = "estimated"


class EventDetails(StrictModel):
    """Bounded per-event details; absent cost means unknown, never zero.

    Additional financial/report parameters require registry and schema review.
    No provider/model/request identifiers or free text are admitted.
    """

    input_tokens: int | None = Field(default=None, ge=0, le=1_000_000_000)
    output_tokens: int | None = Field(default=None, ge=0, le=1_000_000_000)
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)
    cost_microunits: int | None = Field(default=None, ge=0, le=1_000_000_000_000)
    cost_currency: Currency | None = None
    cost_basis: CostBasis | None = None
    registration_method: Literal["email", "oauth"] | None = None

    @model_validator(mode="after")
    def complete_cost(self) -> Self:
        supplied = (self.cost_microunits is not None, self.cost_currency is not None, self.cost_basis is not None)
        if any(supplied) and not all(supplied):
            raise ValueError("cost requires amount, currency and provenance together")
        return self


class BusinessEventInput(StrictModel):
    schema_version: Literal[1] = 1
    event_type: EventType
    entity_id: UUID
    source_id: UUID | None = None
    occurred_at: datetime
    subject_id: UUID | None = None
    mode: Mode = Mode.UNKNOWN
    product: Product | None = None
    details: EventDetails = Field(default_factory=EventDetails)

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("integer schema version required")
        return value

    @field_validator("occurred_at")
    @classmethod
    def utc_occurrence(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("aware occurrence required")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def registered_details(self) -> Self:
        if self.event_type is EventType.REGISTRATION_COMPLETED and self.source_id is not None:
            raise ValueError("registration identity uses only the account UUID")
        if self.event_type is EventType.PAYMENT_CONFIRMED and self.source_id is None:
            raise ValueError("payment confirmation requires a local merchant binding UUID")
        if (
            self.event_type not in (EventType.REGISTRATION_COMPLETED, EventType.PAYMENT_CONFIRMED)
            and self.source_id is not None
        ):
            raise ValueError("event identity uses only the canonical entity UUID")
        keys = self.details.model_dump(exclude_none=True).keys()
        if self.event_type is EventType.REGISTRATION_COMPLETED:
            if keys - {"registration_method"}:
                raise ValueError("details not registered for event type")
        elif self.details.registration_method is not None or (
            self.event_type is not EventType.PROVIDER_USAGE_OBSERVED and keys
        ):
            raise ValueError("details not registered for event type")
        return self

    @property
    def semantic_key(self) -> str:
        return f"v1:{self.event_type.value}:{self.entity_id}:-"


class OutboxClaim(StrictModel):
    outbox_id: UUID
    event_id: UUID
    token: UUID
