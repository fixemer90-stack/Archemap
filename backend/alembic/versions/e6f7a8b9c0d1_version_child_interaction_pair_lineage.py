"""version child interaction pair lineage

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-10-18 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_UNIQUE = "uq_child_interaction_generation_dimension"
_NEW_UNIQUE = "uq_child_interaction_generation_dimension_version"
_OLD_SYNASTRY_UNIQUE = "uq_child_synastry_generation_source"
_NEW_SYNASTRY_UNIQUE = "uq_child_synastry_generation_source_version"
_OLD_FK = "fk_child_interaction_generation_lineage"
_CHART_FK = "fk_child_interaction_chart_lineage"


def upgrade() -> None:
    op.add_column(
        "child_synastry_evidence",
        sa.Column("reference_version", sa.String(length=80), nullable=False, server_default="legacy"),
    )
    op.execute(
        "UPDATE child_synastry_evidence SET reference_version = "
        "COALESCE(NULLIF(payload->>'reference_version', ''), 'legacy')"
    )
    op.alter_column("child_synastry_evidence", "reference_version", server_default=None)
    op.drop_constraint(_OLD_SYNASTRY_UNIQUE, "child_synastry_evidence", type_="unique")
    op.create_unique_constraint(
        _NEW_SYNASTRY_UNIQUE,
        "child_synastry_evidence",
        ["generation_id", "source_key", "reference_version"],
    )
    op.add_column("child_interaction_scores", sa.Column("parent_chart_id", sa.UUID(), nullable=True))
    op.add_column("child_interaction_scores", sa.Column("child_chart_version_id", sa.UUID(), nullable=True))
    op.execute(
        """
        UPDATE child_interaction_scores AS scores
        SET parent_chart_id = generations.parent_chart_id,
            child_chart_version_id = generations.child_chart_version_id
        FROM child_generations AS generations
        WHERE generations.child_profile_id = scores.child_profile_id
          AND generations.generation_id = scores.generation_id
        """
    )
    missing = op.get_bind().scalar(
        sa.text(
            "SELECT count(*) FROM child_interaction_scores "
            "WHERE parent_chart_id IS NULL OR child_chart_version_id IS NULL"
        )
    )
    if missing:
        raise RuntimeError(f"Cannot establish pair lineage for {missing} child interaction score row(s)")
    op.alter_column("child_interaction_scores", "parent_chart_id", nullable=False)
    op.alter_column("child_interaction_scores", "child_chart_version_id", nullable=False)
    op.drop_constraint(_OLD_UNIQUE, "child_interaction_scores", type_="unique")
    op.drop_constraint(_OLD_FK, "child_interaction_scores", type_="foreignkey")
    op.create_unique_constraint(
        _NEW_UNIQUE,
        "child_interaction_scores",
        ["generation_id", "dimension", "scoring_version"],
    )
    op.create_foreign_key(
        _CHART_FK,
        "child_interaction_scores",
        "child_chart_versions",
        ["child_profile_id", "child_chart_version_id"],
        ["child_profile_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        _OLD_FK,
        "child_interaction_scores",
        "child_generations",
        ["child_profile_id", "generation_id", "parent_chart_id", "child_chart_version_id"],
        ["child_profile_id", "generation_id", "parent_chart_id", "child_chart_version_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_child_interaction_parent_chart",
        "child_interaction_scores",
        "astrotype_v2_natal_charts",
        ["parent_chart_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_child_interaction_scores_parent_chart_id",
        "child_interaction_scores",
        ["parent_chart_id"],
    )
    op.create_index(
        "ix_child_interaction_scores_child_chart_version_id",
        "child_interaction_scores",
        ["child_chart_version_id"],
    )


def downgrade() -> None:
    duplicate_groups = op.get_bind().scalar(
        sa.text(
            """
            SELECT count(*)
            FROM (
                SELECT 1
                FROM child_interaction_scores
                GROUP BY generation_id, dimension
                HAVING count(*) > 1
            ) AS duplicate_profiles
            """
        )
    )
    if duplicate_groups:
        raise RuntimeError(
            "Refusing lossy downgrade: child_interaction_scores contains "
            f"{duplicate_groups} duplicate (generation_id, dimension) group(s)"
        )
    synastry_duplicate_groups = op.get_bind().scalar(
        sa.text(
            """
            SELECT count(*)
            FROM (
                SELECT 1
                FROM child_synastry_evidence
                GROUP BY generation_id, source_key
                HAVING count(*) > 1
            ) AS duplicate_evidence
            """
        )
    )
    if synastry_duplicate_groups:
        raise RuntimeError(
            "Refusing lossy downgrade: child_synastry_evidence contains "
            f"{synastry_duplicate_groups} duplicate (generation_id, source_key) group(s)"
        )
    op.drop_index("ix_child_interaction_scores_child_chart_version_id", table_name="child_interaction_scores")
    op.drop_index("ix_child_interaction_scores_parent_chart_id", table_name="child_interaction_scores")
    op.drop_constraint("fk_child_interaction_parent_chart", "child_interaction_scores", type_="foreignkey")
    op.drop_constraint(_OLD_FK, "child_interaction_scores", type_="foreignkey")
    op.drop_constraint(_CHART_FK, "child_interaction_scores", type_="foreignkey")
    op.drop_constraint(_NEW_UNIQUE, "child_interaction_scores", type_="unique")
    op.create_foreign_key(
        _OLD_FK,
        "child_interaction_scores",
        "child_generations",
        ["child_profile_id", "generation_id"],
        ["child_profile_id", "generation_id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        _OLD_UNIQUE,
        "child_interaction_scores",
        ["generation_id", "dimension"],
    )
    op.drop_column("child_interaction_scores", "child_chart_version_id")
    op.drop_column("child_interaction_scores", "parent_chart_id")
    op.drop_constraint(_NEW_SYNASTRY_UNIQUE, "child_synastry_evidence", type_="unique")
    op.create_unique_constraint(
        _OLD_SYNASTRY_UNIQUE,
        "child_synastry_evidence",
        ["generation_id", "source_key"],
    )
    op.drop_column("child_synastry_evidence", "reference_version")
