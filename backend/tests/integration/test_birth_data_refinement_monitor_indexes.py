"""PostgreSQL planner proof for birth-data refinement monitor indexes."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.usefixtures("_setup_database")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "expected_index"),
    [
        (
            """
            SELECT count(*)
            FROM profile_birth_data_revisions
            WHERE status IN ('queued', 'processing')
              AND updated_at < now() - interval '20 minutes'
            """,
            "ix_profile_birth_data_revisions_monitor_active_updated_at",
        ),
        (
            """
            SELECT count(*)
            FROM profile_birth_data_revisions
            WHERE error_code IN ('narrative_generation_failed', 'report_generation_failed')
              AND updated_at >= now() - interval '15 minutes'
            """,
            "ix_profile_birth_data_revisions_monitor_failure_updated_at",
        ),
    ],
)
async def test_postgresql_planner_can_use_refinement_monitor_indexes(
    db_session: AsyncSession, query: str, expected_index: str
) -> None:
    await db_session.execute(text("SET LOCAL enable_seqscan = off"))

    plan = await db_session.execute(text(f"EXPLAIN (COSTS OFF) {query}"))
    rendered_plan = "\n".join(str(row[0]) for row in plan)

    assert expected_index in rendered_plan
