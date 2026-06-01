"""Reports module — SQLAlchemy models for reports and versioning."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import BaseModel


class Report(BaseModel):
    """A generated report for a product vertical.

    One user can have one report per product per profile.
    Versions are created when the profile changes.
    """

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product: Mapped[str] = mapped_column(String(20), nullable=False)  # self, love, child, career
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, generating, ready, failed
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="full")  # preview, full

    # Report content
    report_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    archetype: Mapped[str | None] = mapped_column(String(100), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # PDF
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportVersion(BaseModel):
    """Immutable snapshot of a report version.

    Created when a profile changes — old report data is preserved here.
    """

    __tablename__ = "report_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    report_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    diff_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
