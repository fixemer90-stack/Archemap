"""add refinement monitor indexes

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-10-06 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e0f1a2b3c4d5"
down_revision: str | None = "d9e0f1a2b3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE_NAME = "profile_birth_data_revisions"
_ACTIVE_INDEX = "ix_profile_birth_data_revisions_monitor_active_updated_at"
_FAILURE_INDEX = "ix_profile_birth_data_revisions_monitor_failure_updated_at"


def upgrade() -> None:
    op.create_index(
        _ACTIVE_INDEX,
        _TABLE_NAME,
        ["status", "updated_at"],
        postgresql_where=sa.text("status IN ('queued', 'processing')"),
    )
    op.create_index(
        _FAILURE_INDEX,
        _TABLE_NAME,
        ["error_code", "updated_at"],
        postgresql_where=sa.text("error_code IN ('narrative_generation_failed', 'report_generation_failed')"),
    )


def downgrade() -> None:
    op.drop_index(_FAILURE_INDEX, table_name=_TABLE_NAME)
    op.drop_index(_ACTIVE_INDEX, table_name=_TABLE_NAME)
