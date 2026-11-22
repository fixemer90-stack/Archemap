"""Protect a YooKassa binding across attempts and payment retention.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
"""

import sqlalchemy as sa
from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: str = "e2f3a4b5c6d7"
branch_labels: str | None = None
depends_on: str | None = None

_TABLE = "yookassa_merchant_bindings"
_FK = "fk_payments_yookassa_binding"


def upgrade() -> None:
    op.execute("LOCK TABLE payments IN ACCESS EXCLUSIVE MODE")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT merchant_binding_id FROM payments WHERE merchant_binding_id IS NOT NULL
                GROUP BY merchant_binding_id
                HAVING count(DISTINCT (payment_mode, merchant_account_id)) > 1
            ) THEN
                RAISE EXCEPTION 'refusing migration: conflicting historical YooKassa binding provenance';
            END IF;
        END $$
        """)
    op.create_table(
        _TABLE,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("payment_mode", sa.String(4), nullable=False),
        sa.Column("merchant_account_id", sa.String(255), nullable=False),
        sa.CheckConstraint("payment_mode IN ('test', 'live')", name="ck_yookassa_binding_mode"),
        sa.CheckConstraint("btrim(merchant_account_id) <> ''", name="ck_yookassa_binding_account"),
        sa.UniqueConstraint("id", "payment_mode", "merchant_account_id", name="uq_yookassa_binding_provenance"),
    )
    op.execute("""
        INSERT INTO yookassa_merchant_bindings (id, payment_mode, merchant_account_id)
        SELECT DISTINCT merchant_binding_id, payment_mode, merchant_account_id FROM payments
        WHERE merchant_binding_id IS NOT NULL
        """)
    op.create_foreign_key(
        _FK,
        "payments",
        _TABLE,
        ["merchant_binding_id", "payment_mode", "merchant_account_id"],
        ["id", "payment_mode", "merchant_account_id"],
    )
    op.execute("""
        CREATE FUNCTION reject_yookassa_binding_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'YooKassa binding provenance is immutable' USING ERRCODE = '55000';
        END;
        $$;
        """)
    op.execute("""
        CREATE TRIGGER yookassa_binding_immutable BEFORE UPDATE OR DELETE OR TRUNCATE
        ON yookassa_merchant_bindings FOR EACH STATEMENT EXECUTE FUNCTION reject_yookassa_binding_change()
        """)


def downgrade() -> None:
    op.execute("LOCK TABLE payments, yookassa_merchant_bindings IN ACCESS EXCLUSIVE MODE")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT FROM yookassa_merchant_bindings) THEN
                RAISE EXCEPTION 'refusing downgrade: registered YooKassa binding provenance exists';
            END IF;
        END $$
        """)
    op.drop_constraint(_FK, "payments", type_="foreignkey")
    op.drop_table(_TABLE)
    op.execute("DROP FUNCTION reject_yookassa_binding_change()")
