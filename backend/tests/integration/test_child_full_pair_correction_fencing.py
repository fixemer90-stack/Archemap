"""Real PostgreSQL fencing for full-pair regeneration and birth correction."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.modules.child import api_schemas, api_service, models
from app.modules.child.repository import (
    ChildIdempotencyTargetMismatchError,
    ChildLineageMismatchError,
    ChildRepository,
)
from app.modules.child.service import run_claimed_full_generation
from tests.integration.test_child_api_acceptance_review import _counts
from tests.integration.test_child_generation_lifecycle import (
    NOW,
    CountingProvider,
    _seed_claimable_full_pipeline,
)

pytestmark = pytest.mark.usefixtures("_setup_database")


async def _source(db: AsyncSession) -> tuple[UUID, UUID, UUID, UUID, UUID]:
    seed, generation = await _seed_claimable_full_pipeline(
        db, idempotency_key="fencing-source", snapshot_as_of=datetime.now(UTC)
    )
    child = await db.get(models.ChildProfile, seed.child_id)
    assert child is not None
    child.birth_time = time(12)
    child.caregiver_context = {}
    await db.commit()
    claim = await ChildRepository(db).claim_generation(
        generation_id=generation.generation_id,
        task_id="fencing-source",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await db.commit()
    result = await run_claimed_full_generation(db, claim=claim, provider=CountingProvider(), now=NOW)
    assert result.report_id is not None
    await db.commit()
    return seed.owner_id, seed.child_id, result.report_id, seed.child_chart_id, seed.questionnaire_id


async def _blocked(observer: AsyncSession, waiter: int, holder: int) -> None:
    # Observe the server's actual wait graph, not task timing or a mocked lock.
    async with asyncio.timeout(3):
        while True:
            blockers = await observer.scalar(text("SELECT pg_blocking_pids(:pid)"), {"pid": waiter})
            if holder in (blockers or []):
                assert await observer.scalar(
                    text("SELECT count(*) FROM pg_locks WHERE pid=:pid AND locktype='advisory' AND NOT granted"),
                    {"pid": waiter},
                )
                return
            await asyncio.sleep(0.01)


async def test_full_pair_acceptance_fences_correction_and_replays_old_target(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, child_id, report_id, chart_id, questionnaire_id = await _source(db_session)
    bind = db_session.bind
    assert isinstance(bind, AsyncEngine)
    engine = create_async_engine(bind.url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    reached, release = asyncio.Event(), asyncio.Event()
    original = ChildRepository.resolve_current_generation_lineage
    dispatches: list[UUID] = []

    def dispatch(*, generation_id: UUID) -> str:
        dispatches.append(generation_id)
        return "fencing-local-only"

    async def paused(self: ChildRepository, **kwargs: Any) -> Any:
        lineage = await original(self, **kwargs)
        reached.set()
        await release.wait()
        return lineage

    monkeypatch.setattr(ChildRepository, "resolve_current_generation_lineage", paused)
    tasks: list[asyncio.Task[Any]] = []
    try:
        async with sessions() as acceptance, sessions() as correction, sessions() as observer:
            accept_pid = int(await acceptance.scalar(text("SELECT pg_backend_pid()")) or 0)
            correction_pid = int(await correction.scalar(text("SELECT pg_backend_pid()")) or 0)
            await correction.execute(text("SET LOCAL lock_timeout='8s'"))
            accepted_task = asyncio.create_task(
                api_service.regenerate(
                    acceptance,
                    owner=owner,
                    child_id=child_id,
                    report_id=report_id,
                    scope="full_pair",
                    key="fenced-pair",
                    dispatcher=dispatch,
                )
            )
            tasks.append(accepted_task)
            await asyncio.wait_for(reached.wait(), 5)
            correction_task = asyncio.create_task(
                api_service.patch_child(
                    correction, owner, child_id, api_schemas.PatchChildRequest(birth_date=date(2019, 5, 12))
                )
            )
            tasks.append(correction_task)
            await _blocked(observer, correction_pid, accept_pid)
            assert not correction_task.done()
            release.set()
            accepted = await asyncio.wait_for(accepted_task, 5)
            await asyncio.wait_for(correction_task, 5)
            row = await acceptance.scalar(
                select(models.ChildGeneration).where(models.ChildGeneration.generation_id == accepted.generation_id)
            )
            assert row is not None
            assert (row.child_chart_version_id, row.questionnaire_session_id) == (chart_id, questionnaire_id)
            assert (
                await observer.scalar(
                    select(models.ChildChartVersion.id)
                    .where(models.ChildChartVersion.child_profile_id == child_id)
                    .order_by(models.ChildChartVersion.version.desc())
                    .limit(1)
                )
                != chart_id
            )
            # Retain the stale identity-map object while another connection updates status.
            assert row.status == "queued"
            async with sessions() as writer:
                await writer.execute(
                    update(models.ChildGeneration)
                    .where(models.ChildGeneration.generation_id == accepted.generation_id)
                    .values(status="failed")
                )
                await writer.commit()
            before = await _counts(observer)
            replay = await api_service.regenerate(
                acceptance,
                owner=owner,
                child_id=child_id,
                report_id=report_id,
                scope="full_pair",
                key="fenced-pair",
                dispatcher=dispatch,
            )
            assert replay.generation_id == accepted.generation_id
            assert replay.status == "failed"
            assert not replay.created
            await acceptance.rollback()
            with pytest.raises(ChildIdempotencyTargetMismatchError, match="Regeneration retry differs"):
                await api_service.regenerate(
                    acceptance,
                    owner=owner,
                    child_id=child_id,
                    report_id=report_id,
                    scope="narrative_all",
                    key="fenced-pair",
                    dispatcher=dispatch,
                )
            await acceptance.rollback()
            assert await _counts(observer) == before
            assert dispatches == [accepted.generation_id]
    finally:
        release.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await engine.dispose()


async def test_correction_first_blocks_full_pair_then_rejects_old_questionnaire(
    db_session: AsyncSession,
) -> None:
    owner, child_id, report_id, _, _ = await _source(db_session)
    bind = db_session.bind
    assert isinstance(bind, AsyncEngine)
    engine = create_async_engine(bind.url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    dispatches: list[UUID] = []

    def dispatch(*, generation_id: UUID) -> str:
        dispatches.append(generation_id)
        return "must-not-dispatch"

    task: asyncio.Task[Any] | None = None
    try:
        async with sessions() as correction, sessions() as acceptance, sessions() as observer:
            correction_pid = int(await correction.scalar(text("SELECT pg_backend_pid()")) or 0)
            accept_pid = int(await acceptance.scalar(text("SELECT pg_backend_pid()")) or 0)
            await acceptance.execute(text("SET LOCAL lock_timeout='8s'"))
            await ChildRepository(correction)._lock_child_lineage(child_id)
            task = asyncio.create_task(
                api_service.regenerate(
                    acceptance,
                    owner=owner,
                    child_id=child_id,
                    report_id=report_id,
                    scope="full_pair",
                    key="correction-first",
                    dispatcher=dispatch,
                )
            )
            await _blocked(observer, accept_pid, correction_pid)
            await api_service.patch_child(
                correction, owner, child_id, api_schemas.PatchChildRequest(birth_date=date(2019, 5, 12))
            )
            before = await _counts(observer)
            with pytest.raises(ChildLineageMismatchError, match="age snapshot is stale"):
                await asyncio.wait_for(task, 5)
            await acceptance.rollback()
            assert await _counts(observer) == before
            assert dispatches == []
    finally:
        if task is not None:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await engine.dispose()


async def test_full_pair_takes_shared_idempotency_lock_before_lineage(db_session: AsyncSession) -> None:
    owner, child_id, report_id, _, _ = await _source(db_session)
    bind = db_session.bind
    assert isinstance(bind, AsyncEngine)
    engine = create_async_engine(bind.url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    task: asyncio.Task[Any] | None = None
    dispatches: list[UUID] = []

    def dispatch(*, generation_id: UUID) -> str:
        dispatches.append(generation_id)
        return "shared-key-local-only"

    try:
        async with sessions() as holder, sessions() as acceptance, sessions() as observer:
            holder_pid = int(await holder.scalar(text("SELECT pg_backend_pid()")) or 0)
            accept_pid = int(await acceptance.scalar(text("SELECT pg_backend_pid()")) or 0)
            repo = ChildRepository(holder)
            await repo._lock_generation_idempotency(
                owner_user_id=owner, operation="full_report", idempotency_key="shared-key"
            )
            task = asyncio.create_task(
                api_service.regenerate(
                    acceptance,
                    owner=owner,
                    child_id=child_id,
                    report_id=report_id,
                    scope="full_pair",
                    key="shared-key",
                    dispatcher=dispatch,
                )
            )
            await _blocked(observer, accept_pid, holder_pid)
            # A canonical POST /reports caller must still be able to take
            # lineage: regeneration cannot hold it while waiting for the key.
            await holder.execute(text("SET LOCAL lock_timeout='1s'"))
            await repo._lock_child_lineage(child_id)
            await holder.commit()
            accepted = await asyncio.wait_for(task, 5)
            assert accepted.created
            assert dispatches == [accepted.generation_id]
    finally:
        if task is not None:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await engine.dispose()
