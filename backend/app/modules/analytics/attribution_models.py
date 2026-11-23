"""First-party attribution storage, separate from the internal event payloads."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class AnalyticsAttribution(Base):
    __tablename__ = "analytics_attributions"
    __table_args__ = (
        CheckConstraint(
            "(revoked_at IS NULL AND policy_version IS NOT NULL AND captured_at IS NOT NULL AND bound_at IS NOT NULL "
            "AND captured_at <= bound_at AND bound_at < expires_at) OR "
            "(revoked_at IS NOT NULL AND policy_version IS NULL AND client_id IS NULL AND captured_at IS NULL "
            "AND bound_at IS NULL AND revoked_at < expires_at)",
            name="ck_analytics_attribution_state",
        ),
        CheckConstraint("client_id IS NULL OR client_id ~ '^[0-9]{1,32}$'", name="ck_analytics_attribution_client_id"),
        CheckConstraint(
            "policy_version IS NULL OR policy_version ~ '^[A-Za-z0-9._-]{1,64}$'",
            name="ck_analytics_attribution_policy",
        ),
        CheckConstraint(
            "counter_id IS NULL OR (counter_id > 0 AND revoked_at IS NULL)",
            name="ck_analytics_attribution_counter",
        ),
        Index("ix_analytics_attributions_expires_at", "expires_at"),
    )

    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    policy_version: Mapped[str | None] = mapped_column(String(64))
    counter_id: Mapped[int | None] = mapped_column(BigInteger)
    client_id: Mapped[str | None] = mapped_column(String(32))
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
