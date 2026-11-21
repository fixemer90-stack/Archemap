"""Add internal business facts and transactional projection outbox.

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b9c0d1e2f3a4"
down_revision: str = "a8b9c0d1e2f3"
branch_labels: str | None = None
depends_on: str | None = None


def timestamps() -> list[sa.Column[datetime]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "business_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        *timestamps(),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("semantic_key", sa.String(160), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("subject_id", sa.UUID(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mode", sa.String(7), nullable=False),
        sa.Column("product", sa.String(6), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("semantic_key", name="uq_business_events_semantic_key"),
        sa.CheckConstraint("schema_version = 1", name="ck_business_events_version"),
        sa.CheckConstraint("mode IN ('unknown', 'test', 'live')", name="ck_business_events_mode"),
        sa.CheckConstraint(
            "product IS NULL OR product IN ('self', 'career', 'child', 'plus')", name="ck_business_events_product"
        ),
        sa.CheckConstraint(
            "event_type IN ('registration_completed', 'account_verified', 'basic_report_ready', "
            "'checkout_created', 'payment_confirmed', 'refund_confirmed', 'subscription_period_started', "
            "'renewal_confirmed', 'renewal_canceled', 'report_requested', 'report_ready', 'report_partial', "
            "'report_failed', 'report_opened', 'provider_usage_observed')",
            name="ck_business_events_type",
        ),
    )
    op.create_index("ix_business_events_type_occurred", "business_events", ["event_type", "occurred_at"])
    op.execute("""
        CREATE FUNCTION reject_business_event_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'business events are append-only' USING ERRCODE = '55000';
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER business_events_append_only
        BEFORE UPDATE OR DELETE OR TRUNCATE ON business_events
        FOR EACH STATEMENT EXECUTE FUNCTION reject_business_event_mutation();
    """)
    op.create_table(
        "business_event_outbox",
        sa.Column("id", sa.UUID(), primary_key=True),
        *timestamps(),
        sa.Column("event_id", sa.UUID(), sa.ForeignKey("business_events.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("destination", sa.String(24), nullable=False),
        sa.Column("status", sa.String(9), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claim_token", sa.UUID(), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("event_id", "destination", name="uq_business_event_outbox_identity"),
        sa.CheckConstraint("destination = 'internal_projection'", name="ck_business_event_outbox_destination"),
        sa.CheckConstraint("status IN ('pending', 'delivered')", name="ck_business_event_outbox_status"),
        sa.CheckConstraint("attempts BETWEEN 0 AND 10", name="ck_business_event_outbox_attempts"),
        sa.CheckConstraint("(claim_token IS NULL) = (lease_until IS NULL)", name="ck_business_event_outbox_claim"),
        sa.CheckConstraint(
            "(status = 'delivered') = (delivered_at IS NOT NULL)", name="ck_business_event_outbox_delivered"
        ),
    )
    op.create_index(
        "ix_business_event_outbox_pending", "business_event_outbox", ["status", "next_attempt_at", "lease_until"]
    )


def downgrade() -> None:
    connection = op.get_bind()
    # No concurrent insertion may cross the emptiness check and lose history.
    connection.execute(sa.text("LOCK TABLE business_events, business_event_outbox IN ACCESS EXCLUSIVE MODE"))
    if connection.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM business_events) OR EXISTS (SELECT 1 FROM business_event_outbox)")
    ):
        raise RuntimeError("refusing downgrade: nonempty business monitoring history")
    op.drop_table("business_event_outbox")
    op.drop_table("business_events")
    op.execute("DROP FUNCTION reject_business_event_mutation()")
