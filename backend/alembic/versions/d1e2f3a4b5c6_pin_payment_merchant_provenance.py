"""Pin optional merchant provenance on new payment attempts only.

Revision ID: d1e2f3a4b5c6
Revises: b9c0d1e2f3a4
"""

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: str = "b9c0d1e2f3a4"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("merchant_binding_id", sa.Uuid(), nullable=True))
    op.add_column("payments", sa.Column("payment_mode", sa.String(4), nullable=True))
    op.add_column("payments", sa.Column("merchant_account_id", sa.String(255), nullable=True))
    op.create_check_constraint(
        "ck_payments_merchant_provenance",
        "payments",
        "(merchant_binding_id IS NULL AND payment_mode IS NULL AND merchant_account_id IS NULL) OR "
        "(merchant_binding_id IS NOT NULL AND payment_mode IS NOT NULL AND payment_mode IN ('test', 'live') "
        "AND merchant_account_id IS NOT NULL AND btrim(merchant_account_id) <> '' AND provider = 'yookassa')",
    )
    op.execute("""
        CREATE FUNCTION reject_payment_merchant_provenance_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF ROW(NEW.merchant_binding_id, NEW.payment_mode, NEW.merchant_account_id)
                 IS DISTINCT FROM ROW(OLD.merchant_binding_id, OLD.payment_mode, OLD.merchant_account_id) THEN
                RAISE EXCEPTION 'payment merchant provenance is immutable' USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$;
        """)
    op.execute("""
        CREATE TRIGGER payments_merchant_provenance_immutable
        BEFORE UPDATE ON payments
        FOR EACH ROW EXECUTE FUNCTION reject_payment_merchant_provenance_change();
        """)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("LOCK TABLE payments IN ACCESS EXCLUSIVE MODE"))
    if connection.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM payments WHERE merchant_binding_id IS NOT NULL)")):
        raise RuntimeError("refusing downgrade: pinned payment merchant provenance exists")
    op.execute("DROP TRIGGER payments_merchant_provenance_immutable ON payments")
    op.execute("DROP FUNCTION reject_payment_merchant_provenance_change()")
    op.drop_constraint("ck_payments_merchant_provenance", "payments", type_="check")
    op.drop_column("payments", "merchant_account_id")
    op.drop_column("payments", "payment_mode")
    op.drop_column("payments", "merchant_binding_id")
