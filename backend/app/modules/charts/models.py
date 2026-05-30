"""ChartSnapshot SQLAlchemy model — persisted chart computation."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import BaseModel


class ChartSnapshot(BaseModel):
    """Stores a computed chart snapshot as JSON.

    Each snapshot is tied to a PersonProfile and includes the
    engine version for reproducibility. Stores all intermediate
    computation results for analysis and debugging.
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

    # Birth data snapshot (factual)
    birth_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # {date, time, time_accuracy, place, lat, lon, timezone}

    # Raw chart data (factual)
    chart_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # {planets, houses, aspects}

    # Feature vector (normalized)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # {fire, earth, air, water, cardinal, fixed, mutable}

    # Function strengths (computed)
    function_strengths: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # {Se, Si, Ne, Ni, Fe, Fi, Te, Ti}

    # Socionics results (computed)
    socionics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # {top3, model_a_scores}
