"""SQLAlchemy models for persisted LLM report narratives."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import BaseModel


class ReportNarrative(BaseModel):
    """A stored narrative layer generated for a deterministic report."""

    __tablename__ = "report_narratives"

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("generation_attempts", 0)
        super().__init__(**kwargs)

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    content: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    generation_finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    generation_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
