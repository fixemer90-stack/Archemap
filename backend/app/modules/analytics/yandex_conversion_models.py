"""Destination-specific export fence with no ClientId, owner fields or secrets."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class YandexConversionExport(Base):
    __tablename__ = "analytics_yandex_conversion_exports"
    __table_args__ = (
        CheckConstraint(
            "(status = 'skipped' AND reason IN ('unproven_purchase', 'outside_window', 'no_current_consent') "
            "AND reason IS NOT NULL AND upload_id IS NULL AND upload_phase IS NULL) OR "
            "(status = 'outcome_unknown' AND reason IS NULL AND upload_id IS NULL AND upload_phase IS NULL) OR "
            "(status = 'upload_received' AND reason IS NULL AND upload_id IS NOT NULL)",
            name="ck_yandex_conversion_export_state",
        ),
        CheckConstraint("counter_id > 0 AND (upload_id IS NULL OR upload_id > 0)", name="ck_yandex_conversion_ids"),
        CheckConstraint(
            "upload_phase IS NULL OR upload_phase IN "
            "('PREPARED', 'UPLOADED', 'EXPORTED', 'MATCHED', 'PROCESSED', 'LINKAGE_FAILURE')",
            name="ck_yandex_conversion_upload_phase",
        ),
    )

    event_id: Mapped[UUID] = mapped_column(ForeignKey("business_events.id", ondelete="RESTRICT"), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(24))
    counter_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    upload_id: Mapped[int | None] = mapped_column(BigInteger)
    upload_phase: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
