from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.child import models
from app.modules.child.privacy_export import CHILD_EXPORT_TABLES, ChildExportNotFoundError, export_child_domain
from app.modules.child.repository import ChildRepository
from app.modules.child.service import run_claimed_full_generation
from tests.integration.test_child_generation_lifecycle import (
    NOW,
    CountingProvider,
    _seed_claimable_full_pipeline,
)

pytestmark = pytest.mark.usefixtures("_setup_database")


async def _claim(db: AsyncSession, generation_id: UUID, task: str) -> Any:
    claim = await ChildRepository(db).claim_generation(
        generation_id=generation_id, task_id=task, now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db.commit()
    return claim


@pytest.mark.asyncio
async def test_export_complete_owner_scoped_archived_and_non_destructive(db_session: AsyncSession) -> None:
    seed, generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="ops-export")
    claim = await _claim(db_session, generation.generation_id, "ops-export")
    await run_claimed_full_generation(db_session, claim=claim, provider=CountingProvider(), now=NOW)
    child = await db_session.get(models.ChildProfile, seed.child_id)
    assert child is not None
    child.status = "archived"
    child.caregiver_context = {"api_key": "NEVER-EXPORT", "nested": {"Authorization": "NEVER-EXPORT"}}
    await db_session.commit()
    before = await db_session.scalar(select(func.count()).select_from(models.ChildProfile))
    export = await export_child_domain(db_session, owner_user_id=seed.owner_id, child_profile_id=seed.child_id)
    assert set(export["records"]) == {table.name for table in CHILD_EXPORT_TABLES}
    assert export["records"]["child_profiles"][0]["status"] == "archived"
    assert export["records"]["child_generations"]
    assert export["records"]["child_generation_events"]
    assert export["records"]["child_report_assemblies"]
    assert "NEVER-EXPORT" not in str(export)
    for owner_id, child_id in [(uuid4(), seed.child_id), (seed.owner_id, uuid4())]:
        with pytest.raises(ChildExportNotFoundError, match="Child resource not found"):
            await export_child_domain(db_session, owner_user_id=owner_id, child_profile_id=child_id)
    await db_session.rollback()
    assert await db_session.scalar(select(func.count()).select_from(models.ChildProfile)) == before


@pytest.mark.asyncio
async def test_export_purge_rollback_preserves_export_graph(db_session: AsyncSession) -> None:
    seed, generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="ops-purge")
    claim = await _claim(db_session, generation.generation_id, "ops-purge")
    await run_claimed_full_generation(db_session, claim=claim, provider=CountingProvider(), now=NOW)
    before: dict[str, Any] = await export_child_domain(
        db_session, owner_user_id=seed.owner_id, child_profile_id=seed.child_id
    )
    await db_session.rollback()
    await ChildRepository(db_session).purge_child_domain(owner_user_id=seed.owner_id, child_profile_id=seed.child_id)
    await db_session.rollback()
    after = await export_child_domain(db_session, owner_user_id=seed.owner_id, child_profile_id=seed.child_id)
    assert before == after
