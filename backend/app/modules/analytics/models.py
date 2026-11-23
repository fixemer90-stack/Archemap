"""Append-only internal facts and a separate mutable internal delivery queue."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import BaseModel
from app.infrastructure.database import Base


class BusinessEvent(BaseModel):
    __tablename__ = "business_events"
    __table_args__ = (
        UniqueConstraint("semantic_key", name="uq_business_events_semantic_key"),
        CheckConstraint("schema_version = 1", name="ck_business_events_version"),
        CheckConstraint("mode IN ('unknown', 'test', 'live')", name="ck_business_events_mode"),
        CheckConstraint(
            "product IS NULL OR product IN ('self', 'career', 'child', 'plus')", name="ck_business_events_product"
        ),
        CheckConstraint(
            "event_type IN ('registration_completed', 'account_verified', 'basic_report_ready', "
            "'checkout_created', 'payment_confirmed', 'refund_confirmed', 'subscription_period_started', "
            "'renewal_confirmed', 'renewal_canceled', 'report_requested', 'report_ready', 'report_partial', "
            "'report_failed', 'report_opened', 'provider_usage_observed')",
            name="ck_business_events_type",
        ),
        Index("ix_business_events_type_occurred", "event_type", "occurred_at"),
    )

    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    semantic_key: Mapped[str] = mapped_column(String(160), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(nullable=True)
    subject_id: Mapped[UUID | None] = mapped_column(nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mode: Mapped[str] = mapped_column(String(7), nullable=False)
    product: Mapped[str | None] = mapped_column(String(6), nullable=True)
    details: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class BusinessEventOutbox(BaseModel):
    __tablename__ = "business_event_outbox"
    __table_args__ = (
        UniqueConstraint("event_id", "destination", name="uq_business_event_outbox_identity"),
        CheckConstraint("destination = 'internal_projection'", name="ck_business_event_outbox_destination"),
        CheckConstraint("status IN ('pending', 'delivered')", name="ck_business_event_outbox_status"),
        CheckConstraint("attempts BETWEEN 0 AND 10", name="ck_business_event_outbox_attempts"),
        CheckConstraint("(claim_token IS NULL) = (lease_until IS NULL)", name="ck_business_event_outbox_claim"),
        CheckConstraint(
            "(status = 'delivered') = (delivered_at IS NOT NULL)", name="ck_business_event_outbox_delivered"
        ),
        Index("ix_business_event_outbox_pending", "status", "next_attempt_at", "lease_until"),
    )

    event_id: Mapped[UUID] = mapped_column(ForeignKey("business_events.id", ondelete="RESTRICT"), nullable=False)
    destination: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(9), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    claim_token: Mapped[UUID | None] = mapped_column(nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SelfReadinessEvidence(Base):
    """Bounds for an original Self foundation publication, not an event timestamp."""

    __tablename__ = "business_self_readiness_evidence"
    __table_args__ = (
        CheckConstraint("observed_at >= publish_not_before", name="ck_self_readiness_evidence_bounds"),
        Index(
            "ix_self_readiness_evidence_pending",
            "publish_not_before",
            "event_id",
            postgresql_where=text("observed_at IS NULL"),
        ),
    )

    event_id: Mapped[UUID] = mapped_column(ForeignKey("business_events.id", ondelete="RESTRICT"), primary_key=True)
    report_id: Mapped[UUID] = mapped_column(nullable=False)
    owner_id: Mapped[UUID] = mapped_column(nullable=False)
    generation_id: Mapped[UUID] = mapped_column(nullable=False)
    publish_not_before: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
