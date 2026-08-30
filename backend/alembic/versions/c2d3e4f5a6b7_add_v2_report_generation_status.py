"""add v2 report generation status rows

Revision ID: c2d3e4f5a6b7
Revises: b1e2f3a4b5c6
Create Date: 2026-08-30 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "b1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE_NAME = "astrotype_v2_natal_report_generations"


def upgrade() -> None:
    op.create_table(
        _TABLE_NAME,
        sa.Column("generation_id", sa.Uuid(), nullable=False),
        sa.Column("celery_task_id", sa.String(length=120), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("diagnostics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["person_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["astrotype_v2_natal_reports.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generation_id", name="uq_astrotype_v2_report_generations_generation_id"),
    )
    op.create_index(op.f("ix_astrotype_v2_natal_report_generations_celery_task_id"), _TABLE_NAME, ["celery_task_id"])
    op.create_index(op.f("ix_astrotype_v2_natal_report_generations_generation_id"), _TABLE_NAME, ["generation_id"])
    op.create_index(op.f("ix_astrotype_v2_natal_report_generations_profile_id"), _TABLE_NAME, ["profile_id"])
    op.create_index(op.f("ix_astrotype_v2_natal_report_generations_report_id"), _TABLE_NAME, ["report_id"])
    op.create_index(op.f("ix_astrotype_v2_natal_report_generations_status"), _TABLE_NAME, ["status"])
    op.create_index(op.f("ix_astrotype_v2_natal_report_generations_user_id"), _TABLE_NAME, ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_astrotype_v2_natal_report_generations_user_id"), table_name=_TABLE_NAME)
    op.drop_index(op.f("ix_astrotype_v2_natal_report_generations_status"), table_name=_TABLE_NAME)
    op.drop_index(op.f("ix_astrotype_v2_natal_report_generations_report_id"), table_name=_TABLE_NAME)
    op.drop_index(op.f("ix_astrotype_v2_natal_report_generations_profile_id"), table_name=_TABLE_NAME)
    op.drop_index(op.f("ix_astrotype_v2_natal_report_generations_generation_id"), table_name=_TABLE_NAME)
    op.drop_index(op.f("ix_astrotype_v2_natal_report_generations_celery_task_id"), table_name=_TABLE_NAME)
    op.drop_table(_TABLE_NAME)
