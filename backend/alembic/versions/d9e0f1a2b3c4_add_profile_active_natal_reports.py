"""add profile active natal report pointer

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-09-29 19:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9e0f1a2b3c4"
down_revision: str | None = "c8d9e0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profile_active_natal_reports",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["person_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["astrotype_v2_natal_reports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", name="uq_profile_active_natal_reports_profile"),
        sa.UniqueConstraint("report_id", name="uq_profile_active_natal_reports_report"),
    )
    op.create_index("ix_profile_active_natal_reports_user_id", "profile_active_natal_reports", ["user_id"])
    op.create_index("ix_profile_active_natal_reports_profile_id", "profile_active_natal_reports", ["profile_id"])
    op.create_index("ix_profile_active_natal_reports_report_id", "profile_active_natal_reports", ["report_id"])


def downgrade() -> None:
    op.drop_index("ix_profile_active_natal_reports_report_id", table_name="profile_active_natal_reports")
    op.drop_index("ix_profile_active_natal_reports_profile_id", table_name="profile_active_natal_reports")
    op.drop_index("ix_profile_active_natal_reports_user_id", table_name="profile_active_natal_reports")
    op.drop_table("profile_active_natal_reports")
