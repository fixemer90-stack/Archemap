"""add generation_id to v2 natal reports

Revision ID: b1e2f3a4b5c6
Revises: a3b4c5d6e7f8
Create Date: 2026-08-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b1e2f3a4b5c6"
down_revision: str | None = "a3b4c5d6e7f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE_NAME = "astrotype_v2_natal_reports"


def upgrade() -> None:
    op.add_column(_TABLE_NAME, sa.Column("generation_id", sa.Uuid(), nullable=True))
    op.create_index("ix_astrotype_v2_natal_reports_generation_id", _TABLE_NAME, ["generation_id"])


def downgrade() -> None:
    op.drop_index("ix_astrotype_v2_natal_reports_generation_id", table_name=_TABLE_NAME)
    op.drop_column(_TABLE_NAME, "generation_id")
