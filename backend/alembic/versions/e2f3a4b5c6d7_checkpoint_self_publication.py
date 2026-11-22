"""Checkpoint validated Self publication independently of event enqueue.

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "e2f3a4b5c6d7"
down_revision: str = "d1e2f3a4b5c6"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("astrotype_v2_natal_reports", sa.Column("pending_publication", JSONB(none_as_null=True)))


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("LOCK TABLE astrotype_v2_natal_reports IN ACCESS EXCLUSIVE MODE"))
    if connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM astrotype_v2_natal_reports WHERE pending_publication IS NOT NULL)")
    ):
        raise RuntimeError("refusing downgrade: unpublished Self report candidates exist")
    op.drop_column("astrotype_v2_natal_reports", "pending_publication")
