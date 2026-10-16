"""include input hash in child age snapshot identity

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-10-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_CONSTRAINT = "uq_child_age_snapshots_profile_date_rules"
_NEW_CONSTRAINT = "uq_child_age_snapshots_profile_date_rules_input"


def upgrade() -> None:
    op.drop_constraint(_OLD_CONSTRAINT, "child_age_snapshots", type_="unique")
    op.create_unique_constraint(
        _NEW_CONSTRAINT,
        "child_age_snapshots",
        ["child_profile_id", "as_of_date", "age_rules_version", "input_hash"],
    )


def downgrade() -> None:
    duplicate_groups = op.get_bind().scalar(
        sa.text(
            """
            SELECT count(*)
            FROM (
                SELECT 1
                FROM child_age_snapshots
                GROUP BY child_profile_id, as_of_date, age_rules_version
                HAVING count(*) > 1
            ) AS duplicate_lineages
            """
        )
    )
    if duplicate_groups:
        raise RuntimeError(
            "Refusing lossy downgrade: child_age_snapshots contains "
            f"{duplicate_groups} duplicate (child_profile_id, as_of_date, age_rules_version) lineage group(s)"
        )
    op.drop_constraint(_NEW_CONSTRAINT, "child_age_snapshots", type_="unique")
    op.create_unique_constraint(
        _OLD_CONSTRAINT,
        "child_age_snapshots",
        ["child_profile_id", "as_of_date", "age_rules_version"],
    )
