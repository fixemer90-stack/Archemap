"""Checkpoint Career publication independently of event enqueue.

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "a4b5c6d7e8f9"
down_revision: str = "f3a4b5c6d7e8"
branch_labels: str | None = None
depends_on: str | None = None

_TABLE = "career_generations"
_INDEX = "ix_career_generations_pending_publication"


def upgrade() -> None:
    op.add_column(_TABLE, sa.Column("pending_publication", JSONB(none_as_null=True)))
    op.create_index(
        _INDEX,
        _TABLE,
        ["updated_at", "generation_id"],
        postgresql_where=sa.text("pending_publication IS NOT NULL"),
    )


def downgrade() -> None:
    op.execute("LOCK TABLE career_generations IN ACCESS EXCLUSIVE MODE")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT FROM career_generations WHERE pending_publication IS NOT NULL) THEN
                RAISE EXCEPTION 'refusing downgrade: unpublished Career report candidates exist';
            END IF;
        END $$
        """)
    op.drop_index(_INDEX, table_name=_TABLE)
    op.drop_column(_TABLE, "pending_publication")
