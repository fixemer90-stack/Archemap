"""Add owner-bound first-party analytics attribution.

Revision ID: c1e2f3a4b5d6
Revises: b5c6d7e8f9a0
"""

import sqlalchemy as sa
from alembic import op

# Load the additive model in Alembic's registry without editing the shared env.
from app.modules.analytics import attribution_models as attribution_models

revision = "c1e2f3a4b5d6"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pin revision DDL independently of future model changes.
    table = op.create_table(
        "analytics_attributions",
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("policy_version", sa.String(64)),
        sa.Column("client_id", sa.String(32)),
        sa.Column("captured_at", sa.DateTime(timezone=True)),
        sa.Column("bound_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "(revoked_at IS NULL AND policy_version IS NOT NULL AND captured_at IS NOT NULL AND bound_at IS NOT NULL "
            "AND captured_at <= bound_at AND bound_at < expires_at) OR "
            "(revoked_at IS NOT NULL AND policy_version IS NULL AND client_id IS NULL AND captured_at IS NULL "
            "AND bound_at IS NULL AND revoked_at < expires_at)",
            name="ck_analytics_attribution_state",
        ),
        sa.CheckConstraint(
            "client_id IS NULL OR client_id ~ '^[0-9]{1,32}$'", name="ck_analytics_attribution_client_id"
        ),
        sa.CheckConstraint(
            "policy_version IS NULL OR policy_version ~ '^[A-Za-z0-9._-]{1,64}$'",
            name="ck_analytics_attribution_policy",
        ),
    )
    op.create_index("ix_analytics_attributions_expires_at", table.name, ["expires_at"])


def downgrade() -> None:
    op.execute("LOCK TABLE analytics_attributions IN ACCESS EXCLUSIVE MODE")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM analytics_attributions) THEN
                RAISE EXCEPTION 'Refusing to downgrade with retained analytics attribution rows';
            END IF;
        END $$
    """)
    op.drop_index("ix_analytics_attributions_expires_at", table_name="analytics_attributions")
    op.drop_table("analytics_attributions")
