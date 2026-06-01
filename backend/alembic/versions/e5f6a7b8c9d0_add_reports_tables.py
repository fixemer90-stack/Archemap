"""add reports and report_versions tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-31 12:00:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_json_col = postgresql.JSON(astext_type=sa.Text())
_default = sa.text("'{}'::jsonb")


def upgrade() -> None:
    # Create reports table
    op.create_table(
        "reports",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("product", sa.String(20), nullable=False),
        sa.Column(
            "version", sa.Integer, nullable=False, server_default="1"
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "mode", sa.String(20), nullable=False, server_default="full"
        ),
        sa.Column(
            "report_data",
            _json_col,
            nullable=False,
            server_default=_default,
        ),
        sa.Column("archetype", sa.String(100), nullable=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("pdf_url", sa.String(500), nullable=True),
        sa.Column(
            "pdf_generated",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create report_versions table
    op.create_table(
        "report_versions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True
        ),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column(
            "report_data",
            _json_col,
            nullable=False,
            server_default=_default,
        ),
        sa.Column("pdf_url", sa.String(500), nullable=True),
        sa.Column("diff_summary", _json_col, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("report_versions")
    op.drop_table("reports")
