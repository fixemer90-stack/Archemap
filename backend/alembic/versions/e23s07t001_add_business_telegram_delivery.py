"""Persist a fail-closed fence for each outbound S07 Telegram notice."""

import sqlalchemy as sa
from alembic import op

revision: str = "e23s07t001"
down_revision: str = "e23s08a001"
branch_labels = None
depends_on = None

_TABLE = "business_telegram_deliveries"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column(
            "message_key",
            sa.String(120),
            sa.ForeignKey("business_operator_messages.message_key", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(status IN ('indeterminate', 'invalid_message') AND acknowledged_at IS NULL) OR "
            "(status = 'acknowledged' AND acknowledged_at IS NOT NULL AND acknowledged_at >= recorded_at)",
            name="ck_business_telegram_delivery_state",
        ),
    )


def downgrade() -> None:
    op.execute(sa.text("LOCK TABLE business_telegram_deliveries IN ACCESS EXCLUSIVE MODE"))
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT FROM business_telegram_deliveries)")):
        raise RuntimeError("refusing downgrade of used S07 Telegram delivery fences")
    op.drop_table(_TABLE)
