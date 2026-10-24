from __future__ import annotations

import os
import subprocess
import sys
from datetime import timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.modules.child import models
from app.modules.child.repository import ChildRepository
from app.modules.child.service import run_claimed_full_generation
from tests.integration.test_child_generation_lifecycle import (
    NOW,
    CountingProvider,
    _seed_claimable_full_pipeline,
)


@pytest.mark.asyncio
async def test_upgraded_lifecycle_guards_refuse_lossy_downgrade_and_allow_empty_cycle(
    db_session: AsyncSession,
) -> None:
    assert isinstance(db_session.bind, AsyncEngine)
    engine = db_session.bind
    await db_session.rollback()
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))

    def alembic(*args: str, succeeds: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["DATABASE_URL"] = engine.url.render_as_string(hide_password=False)
        result = subprocess.run(  # noqa: S603 - fixed interpreter/module and test-owned arguments
            [sys.executable, "-m", "alembic", *args],
            cwd=os.fspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert (result.returncode == 0) is succeeds, result.stderr
        return result

    alembic("upgrade", "head")
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sessions() as session:
        seed, generation = await _seed_claimable_full_pipeline(
            session,
            idempotency_key="migration-assembly-guard",
        )
        repository = ChildRepository(session)
        claim = await repository.claim_generation(
            generation_id=generation.generation_id,
            task_id="migration-assembly-worker",
            now=NOW,
            lease_duration=timedelta(minutes=5),
        )
        assert claim is not None
        await session.commit()
        result = await run_claimed_full_generation(
            session,
            claim=claim,
            provider=CountingProvider(),
            now=NOW,
        )
        assert result.report_id is not None
        assembly = await session.scalar(
            select(models.ChildReportAssembly).where(
                models.ChildReportAssembly.generation_id == generation.generation_id
            )
        )
        assert assembly is not None
        assembly_id = assembly.id
        terminal_segment_id = await session.scalar(
            select(models.ChildSegmentGeneration.id).where(
                models.ChildSegmentGeneration.generation_id == generation.generation_id,
                models.ChildSegmentGeneration.status == "ready",
            )
        )
        assert terminal_segment_id is not None
        child_id = seed.child_id
        owner_id = seed.owner_id
        event_count = await session.scalar(
            select(func.count())
            .select_from(models.ChildGenerationEvent)
            .where(models.ChildGenerationEvent.generation_id == generation.generation_id)
        )
        assert event_count and event_count > 0

    async with sessions() as writer:
        for statement in (
            text("UPDATE child_report_assemblies SET status = 'narrative_failed' WHERE id = :id"),
            text("DELETE FROM child_report_assemblies WHERE id = :id"),
            text("UPDATE child_generation_events SET event_code = 'mutated' WHERE generation_id = :generation_id"),
            text("DELETE FROM child_generation_events WHERE generation_id = :generation_id"),
        ):
            with pytest.raises(DBAPIError, match="append-only"):
                await writer.execute(statement, {"id": assembly_id, "generation_id": generation.generation_id})
                await writer.commit()
            await writer.rollback()
        for statement in (
            text("UPDATE child_segment_generations SET content = 'tampered' WHERE id = :id"),
            text("DELETE FROM child_segment_generations WHERE id = :id"),
        ):
            with pytest.raises(DBAPIError, match="Published Child segment is immutable"):
                await writer.execute(statement, {"id": terminal_segment_id})
                await writer.commit()
            await writer.rollback()

    refused = alembic("downgrade", "f7a8b9c0d1e2", succeeds=False)
    assert "Refusing lossy downgrade" in refused.stderr
    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "a8b9c0d1e2f3"
        assert await connection.scalar(text("SELECT count(*) FROM child_report_assemblies")) == 1
        assert await connection.scalar(text("SELECT count(*) FROM child_generation_events")) == event_count
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM pg_trigger WHERE tgname IN "
                    "('trg_child_report_assemblies_immutable', 'trg_child_generation_events_immutable', "
                    "'trg_child_segment_generations_immutable')"
                )
            )
            == 3
        )
        assert (
            await connection.scalar(
                text(
                    "SELECT count(*) FROM pg_constraint WHERE conname IN "
                    "('uq_child_report_assemblies_generation', "
                    "'fk_child_report_assemblies_source_generation_lineage')"
                )
            )
            == 2
        )

    async with sessions() as session:
        await ChildRepository(session).purge_child_domain(
            owner_user_id=owner_id,
            child_profile_id=child_id,
        )
        await session.commit()
        assert await session.scalar(select(func.count()).select_from(models.ChildGenerationEvent)) == 0
        assert await session.scalar(select(func.count()).select_from(models.ChildReportAssembly)) == 0

    alembic("downgrade", "f7a8b9c0d1e2")
    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "f7a8b9c0d1e2"
        assert await connection.scalar(text("SELECT to_regclass('public.child_report_assemblies')")) is None
        assert await connection.scalar(text("SELECT to_regclass('public.child_generation_events')")) is None
    alembic("upgrade", "head")
    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "a8b9c0d1e2f3"
