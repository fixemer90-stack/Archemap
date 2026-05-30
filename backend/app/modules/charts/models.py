"""ChartSnapshot SQLAlchemy model — persisted chart computation."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import BaseModel


class ChartSnapshot(BaseModel):
    """Stores a computed chart snapshot as JSON.

    Each snapshot is tied to a PersonProfile and includes the
    engine version for reproducibility.
    """

    __tablename__ = "chart_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False, default="0.1.0")
    chart_data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
