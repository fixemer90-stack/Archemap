"""E23.S07 central business projections and operator notification history.

Revision ID: e23s07b001
Revises: c1e2f3a4b5d6
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e23s07b001"
down_revision: str | None = "c1e2f3a4b5d6"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "business_daily_counts",
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("mode", sa.String(7), nullable=False),
        sa.Column("product", sa.String(6), nullable=False),
        sa.Column("event_count", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("business_date", "event_type", "mode", "product"),
        sa.CheckConstraint("event_count > 0", name="ck_business_daily_counts_positive"),
    )
    op.create_table(
        "business_operations_heartbeats",
        sa.Column("job", sa.String(24), primary_key=True),
        sa.Column("succeeded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "business_incidents",
        sa.Column("code", sa.String(40), primary_key=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_notified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "business_operator_messages",
        sa.Column("message_key", sa.String(120), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("kind IN ('opened', 'reminder', 'resolved', 'digest')", name="ck_business_message_kind"),
    )
    op.create_index("ix_business_operator_messages_time", "business_operator_messages", ["created_at"])
    op.create_index("ix_business_events_occurred", "business_events", ["occurred_at"])
    op.create_index("ix_business_outbox_pending_age", "business_event_outbox", ["status", "created_at"])
    op.create_index("ix_business_outbox_pending_attempts", "business_event_outbox", ["status", "attempts"])
    op.create_index(
        "ix_career_segments_business_observations",
        "career_segment_generations",
        ["updated_at"],
        postgresql_where=sa.text("provider IS NOT NULL AND provider <> 'mock' AND status IN ('ready', 'failed')"),
    )


def downgrade() -> None:
    # Discarding aggregate rows while outbox entries stay delivered would lose counts.
    # A quiet, never-used installation can roll back; a used one must roll forward.
    op.execute("""
        LOCK TABLE business_daily_counts, business_operations_heartbeats,
                   business_incidents, business_operator_messages IN ACCESS EXCLUSIVE MODE
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM business_daily_counts)
                OR EXISTS (SELECT 1 FROM business_operations_heartbeats)
                OR EXISTS (SELECT 1 FROM business_incidents)
                OR EXISTS (SELECT 1 FROM business_operator_messages) THEN
                RAISE EXCEPTION 'refusing downgrade of used E23.S07 operations state';
            END IF;
        END $$;
    """)
    op.drop_index("ix_career_segments_business_observations", table_name="career_segment_generations")
    op.drop_index("ix_business_outbox_pending_attempts", table_name="business_event_outbox")
    op.drop_index("ix_business_outbox_pending_age", table_name="business_event_outbox")
    op.drop_index("ix_business_events_occurred", table_name="business_events")
    op.drop_table("business_operator_messages")
    op.drop_table("business_incidents")
    op.drop_table("business_operations_heartbeats")
    op.drop_table("business_daily_counts")
