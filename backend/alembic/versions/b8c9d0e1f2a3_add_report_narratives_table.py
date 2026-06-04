"""add report_narratives table

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-04 22:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_json_col = postgresql.JSON(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "report_narratives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product", sa.String(20), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("model_provider", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("content", _json_col, nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("generation_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generation_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generation_attempts", sa.Integer(), nullable=False, server_default="0"),
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
        sa.UniqueConstraint(
            "report_id",
            "product",
            "prompt_version",
            "input_hash",
            "model_name",
            name="uq_report_narratives_cache_key",
        ),
    )

    op.create_index(op.f("ix_report_narratives_report_id"), "report_narratives", ["report_id"], unique=False)
    op.create_index(op.f("ix_report_narratives_product"), "report_narratives", ["product"], unique=False)
    op.create_index(op.f("ix_report_narratives_prompt_version"), "report_narratives", ["prompt_version"], unique=False)
    op.create_index(op.f("ix_report_narratives_status"), "report_narratives", ["status"], unique=False)
    op.create_index(op.f("ix_report_narratives_input_hash"), "report_narratives", ["input_hash"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_report_narratives_input_hash"), table_name="report_narratives")
    op.drop_index(op.f("ix_report_narratives_status"), table_name="report_narratives")
    op.drop_index(op.f("ix_report_narratives_prompt_version"), table_name="report_narratives")
    op.drop_index(op.f("ix_report_narratives_product"), table_name="report_narratives")
    op.drop_index(op.f("ix_report_narratives_report_id"), table_name="report_narratives")
    op.drop_table("report_narratives")
