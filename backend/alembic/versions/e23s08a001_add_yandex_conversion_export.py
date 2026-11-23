"""Fence Yandex offline conversions separately from the internal event outbox."""

import sqlalchemy as sa
from alembic import op

revision: str = "e23s08a001"
down_revision: str = "7ad3c4e591b2"
branch_labels = None
depends_on = None

_TABLE = "analytics_yandex_conversion_exports"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("business_events.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(24)),
        sa.Column("counter_id", sa.BigInteger(), nullable=False),
        sa.Column("target", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("upload_id", sa.BigInteger()),
        sa.Column("upload_phase", sa.String(16)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(status = 'skipped' AND reason IN ('unproven_purchase', 'outside_window', 'no_current_consent') "
            "AND reason IS NOT NULL AND upload_id IS NULL AND upload_phase IS NULL) OR "
            "(status = 'outcome_unknown' AND reason IS NULL AND upload_id IS NULL AND upload_phase IS NULL) OR "
            "(status = 'upload_received' AND reason IS NULL AND upload_id IS NOT NULL)",
            name="ck_yandex_conversion_export_state",
        ),
        sa.CheckConstraint("counter_id > 0 AND (upload_id IS NULL OR upload_id > 0)", name="ck_yandex_conversion_ids"),
        sa.CheckConstraint(
            "upload_phase IS NULL OR upload_phase IN "
            "('PREPARED', 'UPLOADED', 'EXPORTED', 'MATCHED', 'PROCESSED', 'LINKAGE_FAILURE')",
            name="ck_yandex_conversion_upload_phase",
        ),
    )


def downgrade() -> None:
    # Lock even an empty table: no sender may insert a fence after the check.
    op.execute(sa.text("LOCK TABLE analytics_yandex_conversion_exports IN ACCESS EXCLUSIVE MODE"))
    existing = op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT FROM analytics_yandex_conversion_exports)"))
    if existing:
        raise RuntimeError("refusing S08 downgrade: keep existing offline conversion fences")
    op.drop_table(_TABLE)
