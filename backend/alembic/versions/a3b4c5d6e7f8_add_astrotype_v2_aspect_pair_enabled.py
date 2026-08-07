"""add astrotype v2 aspect pair enabled

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-08-06 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3b4c5d6e7f8"
down_revision: str | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE_NAME = "astrotype_v2_aspect_pair_interpretations"
_OLD_UNIQUE = "uq_astrotype_v2_aspect_pair_interpretation"
_INDEX_NAME = "ix_astrotype_v2_aspect_pair_interpretations_enabled"


def upgrade() -> None:
    op.add_column(
        "astrotype_v2_aspect_pair_interpretations",
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_index("ix_astrotype_v2_aspect_pair_interpretations_enabled", _TABLE_NAME, ["enabled"])
    op.drop_constraint(_OLD_UNIQUE, _TABLE_NAME, type_="unique")
    op.create_unique_constraint(
        _OLD_UNIQUE,
        _TABLE_NAME,
        ["aspect_code", "planet_a", "planet_b", "locale", "source_version"],
    )


def downgrade() -> None:
    op.drop_constraint(_OLD_UNIQUE, _TABLE_NAME, type_="unique")
    op.create_unique_constraint(
        _OLD_UNIQUE,
        _TABLE_NAME,
        ["aspect_code", "planet_a", "planet_b", "locale"],
    )
    op.drop_index(_INDEX_NAME, table_name=_TABLE_NAME)
    op.drop_column(_TABLE_NAME, "enabled")
