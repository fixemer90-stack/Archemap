"""add child questionnaire context resolver

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-10-18 21:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ANSWER_GUARD_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION guard_child_questionnaire_answer_mutation() RETURNS trigger AS $$
DECLARE
    old_parent_status text;
    new_parent_status text;
BEGIN
    IF TG_OP = 'DELETE' AND current_setting('app.child_purge', true) = 'on' THEN
        RETURN OLD;
    END IF;
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        SELECT status INTO old_parent_status
        FROM child_questionnaire_sessions
        WHERE id = OLD.questionnaire_session_id;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        SELECT status INTO new_parent_status
        FROM child_questionnaire_sessions
        WHERE id = NEW.questionnaire_session_id;
    END IF;
    IF TG_OP = 'INSERT' AND new_parent_status = 'draft' THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE'
       AND old_parent_status = 'draft'
       AND new_parent_status = 'draft' THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'DELETE' AND old_parent_status = 'draft' THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'completed questionnaire answer is immutable';
END;
$$ LANGUAGE plpgsql
"""
ANSWER_GUARD_TRIGGER_SQL = (
    "CREATE TRIGGER trg_child_answers_questionnaire_guard "
    "BEFORE INSERT OR UPDATE OR DELETE ON child_answers "
    "FOR EACH ROW EXECUTE FUNCTION guard_child_questionnaire_answer_mutation()"
)
SESSION_GUARD_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION guard_child_questionnaire_session_mutation() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' AND current_setting('app.child_purge', true) = 'on' THEN
        RETURN OLD;
    END IF;
    IF TG_OP = 'UPDATE'
       AND OLD.status = 'draft'
       AND NEW.status = 'completed'
       AND current_setting('app.child_questionnaire_completion_id', true) = NEW.id::text
       AND NEW.owner_user_id = OLD.owner_user_id
       AND NEW.child_profile_id = OLD.child_profile_id
       AND NEW.age_snapshot_id = OLD.age_snapshot_id
       AND NEW.selected_question_keys = OLD.selected_question_keys
       AND NEW.questionnaire_version = OLD.questionnaire_version
       AND NEW.answer_version = OLD.answer_version
       AND NEW.context_version = OLD.context_version
       AND NEW.consent_version = OLD.consent_version
       AND NEW.completion_idempotency_key IS NOT NULL
       AND NEW.answers_hash IS NOT NULL
       AND NEW.completed_at IS NOT NULL THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'questionnaire session is immutable outside draft completion';
END;
$$ LANGUAGE plpgsql
"""
SESSION_GUARD_TRIGGER_SQL = (
    "CREATE TRIGGER trg_child_questionnaire_sessions_guard "
    "BEFORE UPDATE OR DELETE ON child_questionnaire_sessions "
    "FOR EACH ROW EXECUTE FUNCTION guard_child_questionnaire_session_mutation()"
)


def upgrade() -> None:
    op.add_column("child_questionnaire_sessions", sa.Column("owner_user_id", sa.UUID(), nullable=True))
    op.add_column(
        "child_questionnaire_sessions",
        sa.Column(
            "selected_question_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"
        ),
    )
    op.add_column(
        "child_questionnaire_sessions",
        sa.Column("answer_version", sa.String(length=80), nullable=False, server_default="legacy"),
    )
    op.execute(
        """
        UPDATE child_questionnaire_sessions AS sessions
        SET owner_user_id = profiles.owner_user_id
        FROM child_profiles AS profiles
        WHERE profiles.id = sessions.child_profile_id
        """
    )
    missing_owner = op.get_bind().scalar(
        sa.text("SELECT count(*) FROM child_questionnaire_sessions WHERE owner_user_id IS NULL")
    )
    if missing_owner:
        raise RuntimeError(f"Cannot backfill owner lineage for {missing_owner} questionnaire session row(s)")
    op.alter_column("child_questionnaire_sessions", "owner_user_id", nullable=False)
    op.alter_column("child_questionnaire_sessions", "selected_question_keys", server_default=None)
    op.alter_column("child_questionnaire_sessions", "answer_version", server_default=None)
    op.drop_constraint("uq_child_questionnaire_profile_version", "child_questionnaire_sessions", type_="unique")
    op.drop_constraint("uq_child_questionnaire_completion_idempotency", "child_questionnaire_sessions", type_="unique")
    op.create_unique_constraint(
        "uq_child_questionnaire_profile_id_age",
        "child_questionnaire_sessions",
        ["child_profile_id", "id", "age_snapshot_id"],
    )
    op.create_unique_constraint(
        "uq_child_questionnaire_owner_completion_idempotency",
        "child_questionnaire_sessions",
        ["owner_user_id", "completion_idempotency_key"],
    )
    op.create_foreign_key(
        "fk_child_questionnaire_owner_lineage",
        "child_questionnaire_sessions",
        "child_profiles",
        ["child_profile_id", "owner_user_id"],
        ["id", "owner_user_id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_child_questionnaire_sessions_owner_user_id",
        "child_questionnaire_sessions",
        ["owner_user_id"],
    )
    op.create_index(
        "uq_child_questionnaire_current_draft",
        "child_questionnaire_sessions",
        ["child_profile_id", "age_snapshot_id", "questionnaire_version"],
        unique=True,
        postgresql_where=sa.text("status = 'draft'"),
    )

    existing_contexts = op.get_bind().scalar(sa.text("SELECT count(*) FROM child_context_resolutions"))
    if existing_contexts:
        raise RuntimeError(
            "Cannot infer questionnaire and age lineage for existing child context resolutions; migrate them explicitly"
        )
    op.add_column("child_context_resolutions", sa.Column("questionnaire_session_id", sa.UUID(), nullable=True))
    op.add_column("child_context_resolutions", sa.Column("age_snapshot_id", sa.UUID(), nullable=True))
    op.add_column(
        "child_context_resolutions",
        sa.Column("interaction_scoring_version", sa.String(length=80), nullable=False, server_default="legacy"),
    )
    op.add_column(
        "child_context_resolutions",
        sa.Column("input_hash", sa.String(length=64), nullable=False, server_default="0" * 64),
    )
    op.alter_column("child_context_resolutions", "questionnaire_session_id", nullable=False)
    op.alter_column("child_context_resolutions", "age_snapshot_id", nullable=False)
    op.alter_column("child_context_resolutions", "interaction_scoring_version", server_default=None)
    op.alter_column("child_context_resolutions", "input_hash", server_default=None)
    op.create_foreign_key(
        "fk_child_context_questionnaire_lineage",
        "child_context_resolutions",
        "child_questionnaire_sessions",
        ["child_profile_id", "questionnaire_session_id", "age_snapshot_id"],
        ["child_profile_id", "id", "age_snapshot_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_child_context_age_lineage",
        "child_context_resolutions",
        "child_age_snapshots",
        ["child_profile_id", "age_snapshot_id"],
        ["child_profile_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_child_context_questionnaire_session",
        "child_context_resolutions",
        "child_questionnaire_sessions",
        ["questionnaire_session_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_child_context_age_snapshot",
        "child_context_resolutions",
        "child_age_snapshots",
        ["age_snapshot_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_child_context_resolutions_questionnaire_session_id",
        "child_context_resolutions",
        ["questionnaire_session_id"],
    )
    op.create_index(
        "ix_child_context_resolutions_age_snapshot_id",
        "child_context_resolutions",
        ["age_snapshot_id"],
    )

    op.execute("DROP TRIGGER IF EXISTS trg_child_answers_immutable ON child_answers")
    op.execute(sa.text(ANSWER_GUARD_FUNCTION_SQL))
    op.execute(ANSWER_GUARD_TRIGGER_SQL)
    op.execute(sa.text(SESSION_GUARD_FUNCTION_SQL))
    op.execute(SESSION_GUARD_TRIGGER_SQL)


def downgrade() -> None:
    duplicate_profile_versions = op.get_bind().scalar(
        sa.text(
            """
            SELECT count(*) FROM (
                SELECT 1 FROM child_questionnaire_sessions
                GROUP BY child_profile_id, questionnaire_version
                HAVING count(*) > 1
            ) AS duplicate_sessions
            """
        )
    )
    if duplicate_profile_versions:
        raise RuntimeError(
            "Refusing lossy downgrade: child questionnaire history contains duplicate "
            f"(child_profile_id, questionnaire_version) groups: {duplicate_profile_versions}"
        )

    op.execute("DROP TRIGGER IF EXISTS trg_child_questionnaire_sessions_guard ON child_questionnaire_sessions")
    op.execute("DROP FUNCTION IF EXISTS guard_child_questionnaire_session_mutation()")
    op.execute("DROP TRIGGER IF EXISTS trg_child_answers_questionnaire_guard ON child_answers")
    op.execute("DROP FUNCTION IF EXISTS guard_child_questionnaire_answer_mutation()")
    op.execute(
        "CREATE TRIGGER trg_child_answers_immutable BEFORE UPDATE OR DELETE ON child_answers "
        "FOR EACH ROW EXECUTE FUNCTION reject_child_artifact_mutation()"
    )

    op.drop_index("ix_child_context_resolutions_age_snapshot_id", table_name="child_context_resolutions")
    op.drop_index("ix_child_context_resolutions_questionnaire_session_id", table_name="child_context_resolutions")
    op.drop_constraint("fk_child_context_age_snapshot", "child_context_resolutions", type_="foreignkey")
    op.drop_constraint("fk_child_context_questionnaire_session", "child_context_resolutions", type_="foreignkey")
    op.drop_constraint("fk_child_context_age_lineage", "child_context_resolutions", type_="foreignkey")
    op.drop_constraint("fk_child_context_questionnaire_lineage", "child_context_resolutions", type_="foreignkey")
    op.drop_column("child_context_resolutions", "input_hash")
    op.drop_column("child_context_resolutions", "interaction_scoring_version")
    op.drop_column("child_context_resolutions", "age_snapshot_id")
    op.drop_column("child_context_resolutions", "questionnaire_session_id")

    op.drop_index("uq_child_questionnaire_current_draft", table_name="child_questionnaire_sessions")
    op.drop_index("ix_child_questionnaire_sessions_owner_user_id", table_name="child_questionnaire_sessions")
    op.drop_constraint("fk_child_questionnaire_owner_lineage", "child_questionnaire_sessions", type_="foreignkey")
    op.drop_constraint(
        "uq_child_questionnaire_owner_completion_idempotency", "child_questionnaire_sessions", type_="unique"
    )
    op.drop_constraint("uq_child_questionnaire_profile_id_age", "child_questionnaire_sessions", type_="unique")
    op.create_unique_constraint(
        "uq_child_questionnaire_completion_idempotency",
        "child_questionnaire_sessions",
        ["child_profile_id", "completion_idempotency_key"],
    )
    op.create_unique_constraint(
        "uq_child_questionnaire_profile_version",
        "child_questionnaire_sessions",
        ["child_profile_id", "questionnaire_version"],
    )
    op.drop_column("child_questionnaire_sessions", "answer_version")
    op.drop_column("child_questionnaire_sessions", "selected_question_keys")
    op.drop_column("child_questionnaire_sessions", "owner_user_id")
