"""add durable Career generations

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-09-18 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a6b7c8d9e0f1"
down_revision: str | None = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_uuid = postgresql.UUID(as_uuid=True)
_jsonb = postgresql.JSONB(astext_type=sa.Text())
_TABLE = "career_generations"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", _uuid, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("generation_id", _uuid, nullable=False),
        sa.Column("user_id", _uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "career_profile_id",
            _uuid,
            sa.ForeignKey("career_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chart_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("report_id", _uuid, sa.ForeignKey("career_reports.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "source_report_id",
            _uuid,
            sa.ForeignKey("career_reports.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("status", sa.String(40), server_default="queued", nullable=False),
        sa.Column("celery_task_id", sa.String(120), nullable=True),
        sa.Column("diagnostics", _jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.UniqueConstraint("generation_id", name="uq_career_generations_generation"),
        sa.UniqueConstraint(
            "user_id", "operation", "idempotency_key", name="uq_career_generations_user_operation_idempotency"
        ),
    )
    for column in ("generation_id", "user_id", "career_profile_id", "chart_id", "report_id", "status"):
        op.create_index(f"ix_{_TABLE}_{column}", _TABLE, [column])


def downgrade() -> None:
    op.drop_table(_TABLE)
