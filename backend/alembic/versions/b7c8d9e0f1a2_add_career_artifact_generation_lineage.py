"""add Career artifact generation lineage

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-09-26 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7c8d9e0f1a2"
down_revision: str | None = "a6b7c8d9e0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_uuid = postgresql.UUID(as_uuid=True)

_TABLES: tuple[tuple[str, str, tuple[str, ...], str, tuple[str, ...]], ...] = (
    (
        "career_dimension_scores",
        "uq_career_dimension_scores_profile_dimension",
        ("career_profile_id", "dimension"),
        "uq_career_dimension_scores_generation_dimension",
        ("generation_id", "dimension"),
    ),
    (
        "career_resolutions",
        "uq_career_resolutions_profile_version",
        ("career_profile_id", "resolver_version"),
        "uq_career_resolutions_generation_version",
        ("generation_id", "resolver_version"),
    ),
    (
        "career_archetype_scores",
        "uq_career_archetype_profile_key",
        ("career_profile_id", "archetype_key"),
        "uq_career_archetype_generation_key",
        ("generation_id", "archetype_key"),
    ),
    (
        "career_environment_axes",
        "uq_career_environment_profile_axis",
        ("career_profile_id", "axis_key"),
        "uq_career_environment_generation_axis",
        ("generation_id", "axis_key"),
    ),
    (
        "career_role_matches",
        "uq_career_role_profile_family",
        ("career_profile_id", "role_family_key"),
        "uq_career_role_generation_family",
        ("generation_id", "role_family_key"),
    ),
    (
        "career_interpretation_facts",
        "uq_career_fact_profile_key_version",
        ("career_profile_id", "fact_key", "source_version"),
        "uq_career_fact_generation_key_version",
        ("generation_id", "fact_key", "source_version"),
    ),
)


def upgrade() -> None:
    for table, old_name, _old_columns, new_name, new_columns in _TABLES:
        op.add_column(table, sa.Column("generation_id", _uuid, nullable=True))
        op.execute(
            sa.text(
                f"UPDATE {table} AS artifact "  # noqa: S608 - fixed migration table names
                "SET generation_id = career_profiles.generation_id "
                "FROM career_profiles "
                "WHERE career_profiles.id = artifact.career_profile_id"
            )
        )
        op.alter_column(table, "generation_id", existing_type=_uuid, nullable=False)
        op.create_index(f"ix_{table}_generation_id", table, ["generation_id"])
        op.drop_constraint(old_name, table, type_="unique")
        op.create_unique_constraint(new_name, table, list(new_columns))


def downgrade() -> None:
    for table, old_name, old_columns, new_name, _new_columns in reversed(_TABLES):
        op.drop_constraint(new_name, table, type_="unique")
        op.create_unique_constraint(old_name, table, list(old_columns))
        op.drop_index(f"ix_{table}_generation_id", table_name=table)
        op.drop_column(table, "generation_id")
