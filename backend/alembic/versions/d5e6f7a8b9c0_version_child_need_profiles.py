"""version child needs profiles

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-10-17 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_CONSTRAINT = "uq_child_need_generation_dimension"
_NEW_CONSTRAINT = "uq_child_need_generation_dimension_version"


def upgrade() -> None:
    op.drop_constraint(_OLD_CONSTRAINT, "child_need_scores", type_="unique")
    op.create_unique_constraint(
        _NEW_CONSTRAINT,
        "child_need_scores",
        ["generation_id", "dimension", "scoring_version"],
    )


def downgrade() -> None:
    duplicate_groups = op.get_bind().scalar(
        sa.text(
            """
            SELECT count(*)
            FROM (
                SELECT 1
                FROM child_need_scores
                GROUP BY generation_id, dimension
                HAVING count(*) > 1
            ) AS duplicate_profiles
            """
        )
    )
    if duplicate_groups:
        raise RuntimeError(
            "Refusing lossy downgrade: child_need_scores contains "
            f"{duplicate_groups} duplicate (generation_id, dimension) group(s)"
        )
    op.drop_constraint(_NEW_CONSTRAINT, "child_need_scores", type_="unique")
    op.create_unique_constraint(
        _OLD_CONSTRAINT,
        "child_need_scores",
        ["generation_id", "dimension"],
    )
