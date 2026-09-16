"""add Career report foundation

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-09-16 09:00:00.000000
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_uuid = postgresql.UUID(as_uuid=True)
_jsonb = postgresql.JSONB(astext_type=sa.Text())


def _base() -> list[sa.Column[Any]]:
    return [
        sa.Column("id", _uuid, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def _chart() -> sa.Column[Any]:
    return sa.Column(
        "chart_id",
        _uuid,
        sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="RESTRICT"),
        nullable=False,
    )


def _profile() -> sa.Column[Any]:
    return sa.Column(
        "career_profile_id",
        _uuid,
        sa.ForeignKey("career_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "career_profiles",
        *_base(),
        sa.Column("user_id", _uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", _uuid, sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False),
        _chart(),
        sa.Column("generation_id", _uuid, nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("status", sa.String(40), server_default="questionnaire_draft", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("scoring_version", sa.String(80), nullable=False),
        sa.Column("reference_version", sa.String(80), nullable=False),
        sa.Column("questionnaire_version", sa.String(80), nullable=False),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_career_profiles_user_idempotency"),
        sa.UniqueConstraint("generation_id", name="uq_career_profiles_generation"),
    )
    op.create_index("ix_career_profiles_user_id", "career_profiles", ["user_id"])
    op.create_index("ix_career_profiles_profile_id", "career_profiles", ["profile_id"])
    op.create_index("ix_career_profiles_chart_id", "career_profiles", ["chart_id"])
    op.create_index("ix_career_profiles_status", "career_profiles", ["status"])

    op.create_table(
        "career_dimension_scores",
        *_base(),
        _profile(),
        _chart(),
        sa.Column("dimension", sa.String(60), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("scoring_version", sa.String(80), nullable=False),
        sa.Column("breakdown", _jsonb, server_default="{}", nullable=False),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_career_dimension_scores_score"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_career_dimension_scores_confidence"),
        sa.UniqueConstraint("career_profile_id", "dimension", name="uq_career_dimension_scores_profile_dimension"),
    )
    op.create_table(
        "career_dimension_evidence",
        *_base(),
        sa.Column(
            "dimension_score_id", _uuid, sa.ForeignKey("career_dimension_scores.id", ondelete="CASCADE"), nullable=False
        ),
        _chart(),
        sa.Column("source_type", sa.String(80), nullable=False),
        sa.Column("source_id", _uuid, nullable=False),
        sa.Column("contribution", sa.Float(), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("payload", _jsonb, server_default="{}", nullable=False),
        sa.CheckConstraint(
            "contribution >= -1 AND contribution <= 1", name="ck_career_dimension_evidence_contribution"
        ),
        sa.UniqueConstraint(
            "dimension_score_id", "source_type", "source_id", name="uq_career_dimension_evidence_source"
        ),
    )
    op.create_table(
        "career_questionnaire_sessions",
        *_base(),
        _profile(),
        _chart(),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("questionnaire_version", sa.String(80), nullable=False),
        sa.Column("context_version", sa.String(80), nullable=False),
        sa.Column("consent_version", sa.String(80), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "career_profile_id", "questionnaire_version", name="uq_career_questionnaire_profile_version"
        ),
    )
    op.create_table(
        "career_answers",
        *_base(),
        sa.Column(
            "questionnaire_session_id",
            _uuid,
            sa.ForeignKey("career_questionnaire_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        _chart(),
        sa.Column("question_key", sa.String(100), nullable=False),
        sa.Column("answer", _jsonb, nullable=False),
        sa.Column("answer_version", sa.String(80), nullable=False),
        sa.UniqueConstraint("questionnaire_session_id", "question_key", name="uq_career_answers_session_question"),
    )
    op.create_table(
        "career_resolutions",
        *_base(),
        _profile(),
        _chart(),
        sa.Column("resolver_version", sa.String(80), nullable=False),
        sa.Column("confirmed_traits", _jsonb, server_default="[]", nullable=False),
        sa.Column("contradictions", _jsonb, server_default="[]", nullable=False),
        sa.Column("preferences", _jsonb, server_default="[]", nullable=False),
        sa.Column("context_constraints", _jsonb, server_default="[]", nullable=False),
        sa.Column("unresolved_ambiguities", _jsonb, server_default="[]", nullable=False),
        sa.UniqueConstraint("career_profile_id", "resolver_version", name="uq_career_resolutions_profile_version"),
    )
    op.create_table(
        "career_archetype_scores",
        *_base(),
        _profile(),
        _chart(),
        sa.Column("archetype_key", sa.String(80), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reference_version", sa.String(80), nullable=False),
        sa.Column("evidence_refs", _jsonb, server_default="[]", nullable=False),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_career_archetype_score"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_career_archetype_confidence"),
        sa.UniqueConstraint("career_profile_id", "archetype_key", name="uq_career_archetype_profile_key"),
    )
    op.create_table(
        "career_environment_axes",
        *_base(),
        _profile(),
        _chart(),
        sa.Column("axis_key", sa.String(80), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reference_version", sa.String(80), nullable=False),
        sa.Column("anti_environment_conditions", _jsonb, server_default="[]", nullable=False),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_career_environment_score"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_career_environment_confidence"),
        sa.UniqueConstraint("career_profile_id", "axis_key", name="uq_career_environment_profile_axis"),
    )
    op.create_table(
        "career_role_matches",
        *_base(),
        _profile(),
        _chart(),
        sa.Column("role_family_key", sa.String(100), nullable=False),
        sa.Column("match_category", sa.String(30), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reference_version", sa.String(80), nullable=False),
        sa.Column("reasons", _jsonb, server_default="[]", nullable=False),
        sa.Column("tensions", _jsonb, server_default="[]", nullable=False),
        sa.Column("requirements", _jsonb, server_default="[]", nullable=False),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_career_role_score"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_career_role_confidence"),
        sa.UniqueConstraint("career_profile_id", "role_family_key", name="uq_career_role_profile_family"),
    )
    op.create_table(
        "career_path_steps",
        *_base(),
        _profile(),
        sa.Column("role_match_id", _uuid, sa.ForeignKey("career_role_matches.id", ondelete="CASCADE"), nullable=False),
        _chart(),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("node_key", sa.String(100), nullable=False),
        sa.Column("transition_key", sa.String(100), nullable=True),
        sa.Column("reference_version", sa.String(80), nullable=False),
        sa.Column("payload", _jsonb, server_default="{}", nullable=False),
        sa.UniqueConstraint("role_match_id", "step_order", name="uq_career_path_role_order"),
    )
    op.create_table(
        "career_interpretation_facts",
        *_base(),
        _profile(),
        _chart(),
        sa.Column("fact_key", sa.String(140), nullable=False),
        sa.Column("section_key", sa.String(80), nullable=False),
        sa.Column("source_version", sa.String(80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("payload", _jsonb, nullable=False),
        sa.Column("evidence_refs", _jsonb, server_default="[]", nullable=False),
        sa.UniqueConstraint(
            "career_profile_id", "fact_key", "source_version", name="uq_career_fact_profile_key_version"
        ),
    )
    op.create_table(
        "career_segment_generations",
        *_base(),
        _profile(),
        _chart(),
        sa.Column("generation_id", _uuid, nullable=False),
        sa.Column("section_key", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("prompt_version", sa.String(80), nullable=False),
        sa.Column("provider", sa.String(80), nullable=True),
        sa.Column("model_version", sa.String(120), nullable=True),
        sa.Column("input_payload", _jsonb, server_default="{}", nullable=False),
        sa.Column("output_payload", _jsonb, server_default="{}", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.UniqueConstraint("generation_id", "section_key", name="uq_career_segment_generation_section"),
    )
    op.create_table(
        "career_reports",
        *_base(),
        _profile(),
        _chart(),
        sa.Column("generation_id", _uuid, nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(40), server_default="deterministic_ready", nullable=False),
        sa.Column("scoring_version", sa.String(80), nullable=False),
        sa.Column("reference_version", sa.String(80), nullable=False),
        sa.Column("questionnaire_version", sa.String(80), nullable=False),
        sa.Column("prompt_version", sa.String(80), nullable=False),
        sa.Column("deterministic_payload", _jsonb, server_default="{}", nullable=False),
        sa.Column("narrative_payload", _jsonb, server_default="{}", nullable=False),
        sa.Column("assembled_payload", _jsonb, server_default="{}", nullable=False),
        sa.UniqueConstraint("career_profile_id", "version", name="uq_career_reports_profile_version"),
        sa.UniqueConstraint("career_profile_id", "idempotency_key", name="uq_career_reports_profile_idempotency"),
        sa.UniqueConstraint("generation_id", name="uq_career_reports_generation"),
    )

    for table in (
        "career_dimension_scores",
        "career_dimension_evidence",
        "career_questionnaire_sessions",
        "career_answers",
        "career_resolutions",
        "career_archetype_scores",
        "career_environment_axes",
        "career_role_matches",
        "career_path_steps",
        "career_interpretation_facts",
        "career_segment_generations",
        "career_reports",
    ):
        op.create_index(f"ix_{table}_chart_id", table, ["chart_id"])

    for table, column in (
        ("career_profiles", "generation_id"),
        ("career_dimension_scores", "career_profile_id"),
        ("career_dimension_scores", "dimension"),
        ("career_dimension_evidence", "dimension_score_id"),
        ("career_questionnaire_sessions", "career_profile_id"),
        ("career_questionnaire_sessions", "status"),
        ("career_answers", "questionnaire_session_id"),
        ("career_resolutions", "career_profile_id"),
        ("career_archetype_scores", "career_profile_id"),
        ("career_environment_axes", "career_profile_id"),
        ("career_role_matches", "career_profile_id"),
        ("career_path_steps", "career_profile_id"),
        ("career_path_steps", "role_match_id"),
        ("career_interpretation_facts", "career_profile_id"),
        ("career_interpretation_facts", "fact_key"),
        ("career_interpretation_facts", "section_key"),
        ("career_segment_generations", "career_profile_id"),
        ("career_segment_generations", "generation_id"),
        ("career_segment_generations", "section_key"),
        ("career_segment_generations", "status"),
        ("career_reports", "career_profile_id"),
        ("career_reports", "generation_id"),
        ("career_reports", "status"),
    ):
        op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table in (
        "career_reports",
        "career_segment_generations",
        "career_interpretation_facts",
        "career_path_steps",
        "career_role_matches",
        "career_environment_axes",
        "career_archetype_scores",
        "career_resolutions",
        "career_answers",
        "career_questionnaire_sessions",
        "career_dimension_evidence",
        "career_dimension_scores",
        "career_profiles",
    ):
        op.drop_table(table)
