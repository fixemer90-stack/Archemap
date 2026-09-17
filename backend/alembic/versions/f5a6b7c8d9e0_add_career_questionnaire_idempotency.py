"""add Career questionnaire completion idempotency

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-09-16 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "career_questionnaire_sessions"


def upgrade() -> None:
    op.add_column(_TABLE, sa.Column("completion_idempotency_key", sa.String(120), nullable=True))
    op.add_column(_TABLE, sa.Column("answers_hash", sa.String(64), nullable=True))
    op.create_unique_constraint(
        "uq_career_questionnaire_completion_idempotency",
        _TABLE,
        ["career_profile_id", "completion_idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_career_questionnaire_completion_idempotency", _TABLE, type_="unique")
    op.drop_column(_TABLE, "answers_hash")
    op.drop_column(_TABLE, "completion_idempotency_key")
