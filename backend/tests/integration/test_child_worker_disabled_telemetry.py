from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.child import models
from tests.integration.test_child_generation_lifecycle import _seed_claimable_full_pipeline
from workers.tasks import child as worker

pytestmark = [pytest.mark.asyncio, pytest.mark.usefixtures("_setup_database")]


async def test_real_worker_telemetry_preserves_disabled_provider_semantics(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="disabled-observed-worker")
    monkeypatch.setattr(worker, "async_session_factory", async_sessionmaker(db_session.bind, expire_on_commit=False))
    monkeypatch.setattr("app.modules.child.service.settings.LLM_ENABLED", False)
    outcome = await worker._generate_child_report_async(
        generation_id=str(generation.generation_id), task_id="disabled-observed-worker"
    )
    assert outcome["status"] == "narrative_failed"
    assert outcome["provider_calls"] == 0
    rows = (
        await db_session.scalars(
            select(models.ChildSegmentGeneration).where(
                models.ChildSegmentGeneration.generation_id == generation.generation_id,
                models.ChildSegmentGeneration.status == "failed",
            )
        )
    ).all()
    assert rows and all(row.error_code == "child_narrative_disabled" for row in rows)
    assert all(row.diagnostics["attempts"] == 0 for row in rows)
