"""Central E23.S07 projections and operator messages; no subject/entity data."""

from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base
from app.modules.analytics.models import BusinessEvent, BusinessEventOutbox
from app.modules.career.models import CareerSegmentGeneration

# Match the source predicate in operations.py; keep the periodic monitor bounded by time.
CAREER_OBSERVATION_PREDICATE = "provider IS NOT NULL AND provider <> 'mock' AND status IN ('ready', 'failed')"
Index(
    "ix_career_segments_business_observations",
    CareerSegmentGeneration.updated_at,
    postgresql_where=text(CAREER_OBSERVATION_PREDICATE),
)
Index("ix_business_events_occurred", BusinessEvent.occurred_at)
Index("ix_business_outbox_pending_age", BusinessEventOutbox.status, BusinessEventOutbox.created_at)
Index("ix_business_outbox_pending_attempts", BusinessEventOutbox.status, BusinessEventOutbox.attempts)


class BusinessDailyCount(Base):
    __tablename__ = "business_daily_counts"
    __table_args__ = (CheckConstraint("event_count > 0", name="ck_business_daily_counts_positive"),)

    business_date: Mapped[date] = mapped_column(Date, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(40), primary_key=True)
    mode: Mapped[str] = mapped_column(String(7), primary_key=True)
    product: Mapped[str] = mapped_column(String(6), primary_key=True)  # empty = not applicable
    event_count: Mapped[int] = mapped_column(BigInteger, nullable=False)


class BusinessOperationsHeartbeat(Base):
    __tablename__ = "business_operations_heartbeats"

    job: Mapped[str] = mapped_column(String(24), primary_key=True)
    succeeded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BusinessIncident(Base):
    __tablename__ = "business_incidents"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_notified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BusinessOperatorMessage(Base):
    __tablename__ = "business_operator_messages"
    __table_args__ = (
        CheckConstraint("kind IN ('opened', 'reminder', 'resolved', 'digest')", name="ck_business_message_kind"),
        Index("ix_business_operator_messages_time", "created_at"),
    )

    message_key: Mapped[str] = mapped_column(String(120), primary_key=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class BusinessTelegramDelivery(Base):
    __tablename__ = "business_telegram_deliveries"
    __table_args__ = (
        CheckConstraint(
            "(status IN ('indeterminate', 'invalid_message') AND acknowledged_at IS NULL) OR "
            "(status = 'acknowledged' AND acknowledged_at IS NOT NULL AND acknowledged_at >= recorded_at)",
            name="ck_business_telegram_delivery_state",
        ),
    )

    message_key: Mapped[str] = mapped_column(
        String(120), ForeignKey("business_operator_messages.message_key", ondelete="RESTRICT"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
