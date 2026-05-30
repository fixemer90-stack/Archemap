"""PersonProfile SQLAlchemy model — birth data for chart computation."""

from __future__ import annotations

import uuid
from datetime import date, time

from sqlalchemy import Date, Float, ForeignKey, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import BaseModel


class PersonProfile(BaseModel):
    """Stores natal data needed to compute a chart snapshot.

    ``birth_time_accuracy`` tracks how reliable the time is:
      - ``exact``  — confirmed by birth certificate
      - ``approximate`` — known within ~15 min
      - ``unknown`` — time not available; houses/ASC will be excluded
    """

    __tablename__ = "person_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    birth_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    birth_time_accuracy: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown"
    )  # "exact" | "approximate" | "unknown"
    birth_place: Mapped[str] = mapped_column(String(300), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str] = mapped_column(String(60), nullable=False)  # IANA, e.g. "Europe/Moscow"
