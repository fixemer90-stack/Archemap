"""Checkpoint Child report assemblies before terminal event publication.

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "b5c6d7e8f9a0"
down_revision: str = "a4b5c6d7e8f9"
branch_labels: str | None = None
depends_on: str | None = None

_TABLE = "child_generations"
_INDEX = "ix_child_generations_pending_publication"


def upgrade() -> None:
    op.add_column(_TABLE, sa.Column("pending_publication", JSONB(none_as_null=True)))
    op.create_index(_INDEX, _TABLE, ["heartbeat_at", "id"], postgresql_where=sa.text("pending_publication IS NOT NULL"))


def downgrade() -> None:
    op.execute("LOCK TABLE child_generations IN ACCESS EXCLUSIVE MODE")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT FROM child_generations WHERE pending_publication IS NOT NULL) THEN
                RAISE EXCEPTION 'refusing downgrade: unpublished Child report candidates exist';
            END IF;
        END $$
        """)
    op.drop_index(_INDEX, table_name=_TABLE)
    op.drop_column(_TABLE, "pending_publication")
