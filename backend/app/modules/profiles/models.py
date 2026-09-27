"""PersonProfile SQLAlchemy model — birth data for chart computation."""

from __future__ import annotations

import uuid
from datetime import date, time
from typing import Any

from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, Index, String, Time, UniqueConstraint, event, inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID
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


class ProfileBirthDataRevision(BaseModel):
    """Immutable birth-data snapshots with mutable generation status/result links."""

    __tablename__ = "profile_birth_data_revisions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'processing', 'deterministic_ready', 'ready', 'failed')",
            name="ck_profile_birth_data_revisions_status",
        ),
        UniqueConstraint("generation_id", name="uq_profile_birth_data_revisions_generation_id"),
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_profile_birth_data_revisions_user_idempotency",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    previous_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    new_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    changed_fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="queued", index=True)
    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("astrotype_v2_natal_report_generations.generation_id", ondelete="RESTRICT"),
        nullable=False,
    )
    chart_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("astrotype_v2_natal_charts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("astrotype_v2_natal_reports.id", ondelete="RESTRICT"),
        nullable=True,
    )
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)


_IMMUTABLE_REVISION_FIELDS = (
    "user_id",
    "profile_id",
    "previous_snapshot",
    "new_snapshot",
    "changed_fields",
    "generation_id",
    "idempotency_key",
    "request_hash",
    "created_at",
)


@event.listens_for(ProfileBirthDataRevision, "before_update")
def _prevent_revision_fact_changes(_mapper: object, _connection: object, target: ProfileBirthDataRevision) -> None:
    state = inspect(target)
    changed = [field for field in _IMMUTABLE_REVISION_FIELDS if state.attrs[field].history.has_changes()]
    if changed:
        raise ValueError(f"Profile birth-data revision facts are immutable: {', '.join(changed)}")


Index(
    "ix_profile_birth_data_revisions_user_created_at",
    ProfileBirthDataRevision.user_id,
    ProfileBirthDataRevision.created_at.desc(),
)
Index(
    "ix_profile_birth_data_revisions_profile_created_at",
    ProfileBirthDataRevision.profile_id,
    ProfileBirthDataRevision.created_at.desc(),
)
