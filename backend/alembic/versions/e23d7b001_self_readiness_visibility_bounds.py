"""Store bounded evidence for new Self foundation publications without backfill."""

import sqlalchemy as sa
from alembic import op

revision: str = "e23d7b001"
down_revision: str = "e23s08b001"
branch_labels = None
depends_on = None

_TABLE = "business_self_readiness_evidence"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("business_events.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("generation_id", sa.Uuid(), nullable=False),
        sa.Column("publish_not_before", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("observed_at >= publish_not_before", name="ck_self_readiness_evidence_bounds"),
    )
    op.create_index(
        "ix_self_readiness_evidence_pending",
        _TABLE,
        ["publish_not_before", "event_id"],
        postgresql_where=sa.text("observed_at IS NULL"),
    )
    op.execute("""
        CREATE FUNCTION guard_self_readiness_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.observed_at IS NULL THEN
                    RETURN NEW;
                END IF;
            ELSIF TG_OP = 'UPDATE' THEN
                IF OLD.observed_at IS NULL AND NEW.observed_at IS NOT NULL
                   AND ROW(NEW.event_id, NEW.report_id, NEW.owner_id, NEW.generation_id, NEW.publish_not_before)
                       IS NOT DISTINCT FROM
                       ROW(OLD.event_id, OLD.report_id, OLD.owner_id, OLD.generation_id, OLD.publish_not_before) THEN
                    RETURN NEW;
                END IF;
            END IF;
            RAISE EXCEPTION 'Self readiness evidence is write-once' USING ERRCODE = '55000';
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER self_readiness_evidence_write_once
        BEFORE INSERT OR UPDATE OR DELETE ON business_self_readiness_evidence
        FOR EACH ROW EXECUTE FUNCTION guard_self_readiness_evidence()
    """)
    op.execute("""
        CREATE TRIGGER self_readiness_evidence_no_truncate
        BEFORE TRUNCATE ON business_self_readiness_evidence
        FOR EACH STATEMENT EXECUTE FUNCTION guard_self_readiness_evidence()
    """)


def downgrade() -> None:
    op.execute(f"LOCK TABLE {_TABLE} IN ACCESS EXCLUSIVE MODE")
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM business_self_readiness_evidence) THEN
            RAISE EXCEPTION 'refusing D7 downgrade: keep retained Self readiness evidence';
        END IF;
    END $$""")
    op.drop_table(_TABLE)
    op.execute("DROP FUNCTION guard_self_readiness_evidence()")
