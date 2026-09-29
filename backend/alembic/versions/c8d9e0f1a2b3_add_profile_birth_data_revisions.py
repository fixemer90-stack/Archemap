"""add profile birth data revisions

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-09-27 13:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8d9e0f1a2b3"
down_revision: str | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE_NAME = "profile_birth_data_revisions"


def upgrade() -> None:
    op.create_table(
        "profile_birth_data_revisions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("previous_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("new_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("changed_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=40), server_default="queued", nullable=False),
        sa.Column("generation_id", sa.Uuid(), nullable=False),
        sa.Column("chart_id", sa.Uuid(), nullable=True),
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("dispatch_status", sa.String(length=24), server_default="pending", nullable=False),
        sa.Column("dispatch_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("dispatch_claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatch_error_code", sa.String(length=80), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'deterministic_ready', 'ready', 'failed')",
            name="ck_profile_birth_data_revisions_status",
        ),
        sa.CheckConstraint(
            "dispatch_status IN ('pending', 'dispatching', 'dispatched')",
            name="ck_profile_birth_data_revisions_dispatch_status",
        ),
        sa.ForeignKeyConstraint(["chart_id"], ["astrotype_v2_natal_charts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["generation_id"],
            ["astrotype_v2_natal_report_generations.generation_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["person_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["report_id"], ["astrotype_v2_natal_reports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generation_id", name="uq_profile_birth_data_revisions_generation_id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_profile_birth_data_revisions_user_idempotency"),
    )
    op.create_index(
        "ix_profile_birth_data_revisions_user_created_at",
        _TABLE_NAME,
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_profile_birth_data_revisions_profile_created_at",
        _TABLE_NAME,
        ["profile_id", sa.text("created_at DESC")],
    )
    op.create_index("ix_profile_birth_data_revisions_status", _TABLE_NAME, ["status"])
    op.create_index("ix_profile_birth_data_revisions_dispatch_status", _TABLE_NAME, ["dispatch_status"])
    op.execute(
        """
        CREATE FUNCTION prevent_profile_birth_data_revision_fact_changes()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.user_id IS DISTINCT FROM OLD.user_id
               OR NEW.profile_id IS DISTINCT FROM OLD.profile_id
               OR NEW.previous_snapshot IS DISTINCT FROM OLD.previous_snapshot
               OR NEW.new_snapshot IS DISTINCT FROM OLD.new_snapshot
               OR NEW.changed_fields IS DISTINCT FROM OLD.changed_fields
               OR NEW.generation_id IS DISTINCT FROM OLD.generation_id
               OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
               OR NEW.request_hash IS DISTINCT FROM OLD.request_hash
               OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                RAISE EXCEPTION 'profile birth-data revision facts are immutable'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_profile_birth_data_revisions_immutable
        BEFORE UPDATE ON profile_birth_data_revisions
        FOR EACH ROW
        EXECUTE FUNCTION prevent_profile_birth_data_revision_fact_changes()
        """
    )
    op.execute(
        """
        CREATE FUNCTION prevent_profile_birth_data_revision_deletion()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'profile birth-data revisions cannot be deleted'
                USING ERRCODE = '23514';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_profile_birth_data_revisions_no_delete
        BEFORE DELETE ON profile_birth_data_revisions
        FOR EACH ROW
        EXECUTE FUNCTION prevent_profile_birth_data_revision_deletion()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_profile_birth_data_revisions_no_delete ON profile_birth_data_revisions")
    op.execute("DROP FUNCTION prevent_profile_birth_data_revision_deletion()")
    op.execute("DROP TRIGGER trg_profile_birth_data_revisions_immutable ON profile_birth_data_revisions")
    op.execute("DROP FUNCTION prevent_profile_birth_data_revision_fact_changes()")
    op.drop_index("ix_profile_birth_data_revisions_dispatch_status", table_name=_TABLE_NAME)
    op.drop_index("ix_profile_birth_data_revisions_status", table_name=_TABLE_NAME)
    op.drop_index("ix_profile_birth_data_revisions_profile_created_at", table_name=_TABLE_NAME)
    op.drop_index("ix_profile_birth_data_revisions_user_created_at", table_name=_TABLE_NAME)
    op.drop_table(_TABLE_NAME)
