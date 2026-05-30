"""add fields to chart_snapshots

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-31 01:00:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_json_col = postgresql.JSON(astext_type=sa.Text())
_default = sa.text("'{}'::jsonb")


def upgrade() -> None:
    op.add_column(
        "chart_snapshots",
        sa.Column("birth_data", _json_col, nullable=False, server_default=_default),
    )
    op.add_column(
        "chart_snapshots",
        sa.Column("features", _json_col, nullable=False, server_default=_default),
    )
    op.add_column(
        "chart_snapshots",
        sa.Column("function_strengths", _json_col, nullable=False, server_default=_default),
    )
    op.add_column(
        "chart_snapshots",
        sa.Column("socionics", _json_col, nullable=False, server_default=_default),
    )


def downgrade() -> None:
    op.drop_column("chart_snapshots", "socionics")
    op.drop_column("chart_snapshots", "function_strengths")
    op.drop_column("chart_snapshots", "features")
    op.drop_column("chart_snapshots", "birth_data")
