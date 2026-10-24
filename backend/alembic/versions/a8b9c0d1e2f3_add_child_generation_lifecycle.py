"""add child generation lifecycle leases

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-10-23 00:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a8b9c0d1e2f3"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("child_segment_generations", sa.Column("lifecycle_token", sa.UUID(), nullable=True))
    op.add_column("child_generations", sa.Column("questionnaire_session_id", sa.UUID(), nullable=True))
    op.add_column(
        "child_generations",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("child_generations", sa.Column("claim_token", sa.UUID(), nullable=True))
    op.add_column("child_generations", sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("child_generations", sa.Column("dispatch_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("child_generations", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("child_generations", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("child_generations", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("child_generations", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("child_generations", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("child_generations", sa.Column("last_error_code", sa.String(length=80), nullable=True))
    op.add_column(
        "child_generations",
        sa.Column(
            "operation_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("child_generations", "attempt_count", server_default=None)
    op.create_foreign_key(
        "fk_child_generations_questionnaire_session",
        "child_generations",
        "child_questionnaire_sessions",
        ["questionnaire_session_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_child_generations_questionnaire_lineage",
        "child_generations",
        "child_questionnaire_sessions",
        ["child_profile_id", "questionnaire_session_id"],
        ["child_profile_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_child_generations_questionnaire_session_id",
        "child_generations",
        ["questionnaire_session_id"],
    )
    op.create_index(
        "ix_child_generations_status_lease",
        "child_generations",
        ["status", "lease_expires_at"],
    )
    op.create_index(
        "ix_child_generations_status_retry",
        "child_generations",
        ["status", "next_retry_at"],
    )
    op.create_table(
        "child_report_assemblies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("child_profile_id", sa.UUID(), nullable=False),
        sa.Column("report_id", sa.UUID(), nullable=False),
        sa.Column("generation_id", sa.UUID(), nullable=False),
        sa.Column("source_generation_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("contract_version", sa.String(length=80), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["child_profile_id"], ["child_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["child_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["child_profile_id", "report_id"],
            ["child_reports.child_profile_id", "child_reports.id"],
            name="fk_child_report_assemblies_report_lineage",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["child_profile_id", "generation_id"],
            ["child_generations.child_profile_id", "child_generations.generation_id"],
            name="fk_child_report_assemblies_generation_lineage",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["child_profile_id", "source_generation_id"],
            ["child_generations.child_profile_id", "child_generations.generation_id"],
            name="fk_child_report_assemblies_source_generation_lineage",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generation_id", name="uq_child_report_assemblies_generation"),
    )
    op.create_index("ix_child_report_assemblies_child_profile_id", "child_report_assemblies", ["child_profile_id"])
    op.create_index("ix_child_report_assemblies_report_id", "child_report_assemblies", ["report_id"])
    op.create_index("ix_child_report_assemblies_generation_id", "child_report_assemblies", ["generation_id"])
    op.create_index(
        "ix_child_report_assemblies_source_generation_id",
        "child_report_assemblies",
        ["source_generation_id"],
    )
    op.create_index("ix_child_report_assemblies_status", "child_report_assemblies", ["status"])
    op.create_table(
        "child_generation_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("generation_id", sa.UUID(), nullable=False),
        sa.Column("event_code", sa.String(length=50), nullable=False),
        sa.Column("status_from", sa.String(length=40), nullable=True),
        sa.Column("status_to", sa.String(length=40), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("task_correlation", sa.String(length=120), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["generation_id"],
            ["child_generations.generation_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_child_generation_events_generation_id", "child_generation_events", ["generation_id"])
    op.create_index("ix_child_generation_events_event_code", "child_generation_events", ["event_code"])
    op.execute(
        """
        CREATE FUNCTION guard_child_segment_generation_mutation() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' AND current_setting('app.child_purge', true) = 'on' THEN
                RETURN OLD;
            END IF;
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Published Child segment is immutable';
            END IF;
            IF OLD.status IN ('in_progress', 'retry_waiting')
               AND NEW.status IN ('in_progress', 'retry_waiting', 'ready', 'not_applicable', 'failed') THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'Published Child segment is immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER trg_child_segment_generations_immutable "
        "BEFORE UPDATE OR DELETE ON child_segment_generations "
        "FOR EACH ROW EXECUTE FUNCTION guard_child_segment_generation_mutation()"
    )
    op.execute(
        "CREATE TRIGGER trg_child_report_assemblies_immutable "
        "BEFORE UPDATE OR DELETE ON child_report_assemblies "
        "FOR EACH ROW EXECUTE FUNCTION reject_child_artifact_mutation()"
    )
    op.execute(
        "CREATE TRIGGER trg_child_generation_events_immutable "
        "BEFORE UPDATE OR DELETE ON child_generation_events "
        "FOR EACH ROW EXECUTE FUNCTION reject_child_artifact_mutation()"
    )


def downgrade() -> None:
    connection = op.get_bind()
    lossy = connection.execute(
        sa.text(
            """
            SELECT
                EXISTS (SELECT 1 FROM child_report_assemblies)
                OR EXISTS (SELECT 1 FROM child_generation_events)
                OR EXISTS (
                    SELECT 1 FROM child_segment_generations
                    WHERE lifecycle_token IS NOT NULL
                )
                OR EXISTS (
                    SELECT 1 FROM child_generations
                    WHERE questionnaire_session_id IS NOT NULL
                       OR attempt_count <> 0
                       OR claim_token IS NOT NULL
                       OR dispatched_at IS NOT NULL
                       OR dispatch_expires_at IS NOT NULL
                       OR claimed_at IS NOT NULL
                       OR lease_expires_at IS NOT NULL
                       OR heartbeat_at IS NOT NULL
                       OR next_retry_at IS NOT NULL
                       OR finished_at IS NOT NULL
                       OR last_error_code IS NOT NULL
                       OR operation_payload <> '{}'::jsonb
                )
            """
        )
    ).scalar_one()
    if lossy:
        raise RuntimeError("Refusing lossy downgrade: child generation lifecycle data would be lost")

    op.execute("DROP TRIGGER IF EXISTS trg_child_generation_events_immutable ON child_generation_events")
    op.execute("DROP TRIGGER IF EXISTS trg_child_report_assemblies_immutable ON child_report_assemblies")
    op.execute("DROP TRIGGER IF EXISTS trg_child_segment_generations_immutable ON child_segment_generations")
    op.execute("DROP FUNCTION IF EXISTS guard_child_segment_generation_mutation()")
    op.drop_index("ix_child_generation_events_event_code", table_name="child_generation_events")
    op.drop_index("ix_child_generation_events_generation_id", table_name="child_generation_events")
    op.drop_table("child_generation_events")
    op.drop_index("ix_child_report_assemblies_status", table_name="child_report_assemblies")
    op.drop_index("ix_child_report_assemblies_source_generation_id", table_name="child_report_assemblies")
    op.drop_index("ix_child_report_assemblies_generation_id", table_name="child_report_assemblies")
    op.drop_index("ix_child_report_assemblies_report_id", table_name="child_report_assemblies")
    op.drop_index("ix_child_report_assemblies_child_profile_id", table_name="child_report_assemblies")
    op.drop_table("child_report_assemblies")
    op.drop_column("child_segment_generations", "lifecycle_token")
    op.drop_index("ix_child_generations_status_retry", table_name="child_generations")
    op.drop_index("ix_child_generations_status_lease", table_name="child_generations")
    op.drop_index("ix_child_generations_questionnaire_session_id", table_name="child_generations")
    op.drop_constraint(
        "fk_child_generations_questionnaire_lineage",
        "child_generations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_child_generations_questionnaire_session",
        "child_generations",
        type_="foreignkey",
    )
    op.drop_column("child_generations", "last_error_code")
    op.drop_column("child_generations", "operation_payload")
    op.drop_column("child_generations", "finished_at")
    op.drop_column("child_generations", "next_retry_at")
    op.drop_column("child_generations", "heartbeat_at")
    op.drop_column("child_generations", "lease_expires_at")
    op.drop_column("child_generations", "claimed_at")
    op.drop_column("child_generations", "claim_token")
    op.drop_column("child_generations", "dispatch_expires_at")
    op.drop_column("child_generations", "dispatched_at")
    op.drop_column("child_generations", "attempt_count")
    op.drop_column("child_generations", "questionnaire_session_id")
