"""Durable Child Report generation and reconciliation tasks."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from time import monotonic
from typing import Any

from app.config import settings
from app.infrastructure.celery_async import run_async_in_worker
from app.infrastructure.database import async_session_factory
from app.modules.child import models
from app.modules.child.dispatch import dispatch_child_generation
from app.modules.child.observability import child_telemetry, observe_child_provider
from app.modules.child.repository import ChildRepository
from app.modules.child.service import (
    configured_child_provider,
    list_queued_generation_ids,
    run_claimed_age_update,
    run_claimed_full_generation,
    run_claimed_narrative_retry,
)
from app.modules.child.status import ChildGenerationOperation
from workers.celery_app import app


@app.task(  # type: ignore[untyped-decorator]
    name="child.generate_report",
    bind=True,
    soft_time_limit=max(settings.LLM_TIMEOUT_SECONDS * 20, 900),
    time_limit=max(settings.LLM_TIMEOUT_SECONDS * 20 + 120, 1020),
)
def generate_child_report(self: Any, *, generation_id: str) -> dict[str, Any]:
    task_id = str(getattr(getattr(self, "request", None), "id", "")) or f"child-generation-{generation_id}"
    return run_async_in_worker(_generate_child_report_async(generation_id=generation_id, task_id=task_id))


async def _generate_child_report_async(*, generation_id: str, task_id: str) -> dict[str, Any]:
    started = monotonic()
    with child_telemetry.lifecycle():
        try:
            result = await _run_child_report_async(generation_id=generation_id, task_id=task_id)
        except Exception:
            child_telemetry.record(
                operation="worker",
                outcome="worker_failure",
                duration_seconds=monotonic() - started,
            )
            raise
        child_telemetry.record(
            operation="worker",
            outcome=result["status"],
            duration_seconds=monotonic() - started,
        )
        return result


async def _run_child_report_async(*, generation_id: str, task_id: str) -> dict[str, Any]:
    generation_uuid = uuid.UUID(generation_id)
    lease = timedelta(seconds=settings.CHILD_GENERATION_LEASE_SECONDS)
    async with async_session_factory() as session:
        repository = ChildRepository(session)
        claim = await repository.claim_generation(
            generation_id=generation_uuid,
            task_id=task_id,
            now=datetime.now(UTC),
            lease_duration=lease,
        )
        await session.commit()
        if claim is None:
            generation = await session.scalar(
                models.ChildGeneration.__table__.select().where(models.ChildGeneration.generation_id == generation_uuid)
            )
            return {"generation_id": generation_id, "status": "not_claimed", "row": bool(generation)}
        if claim.generation.operation == ChildGenerationOperation.AGE_UPDATE.value:
            result = await run_claimed_age_update(session, claim=claim)
        elif claim.generation.operation == ChildGenerationOperation.NARRATIVE_RETRY.value:
            result = await run_claimed_narrative_retry(
                session,
                claim=claim,
                provider=observe_child_provider(configured_child_provider(), operation=claim.generation.operation),
            )
        else:
            result = await run_claimed_full_generation(
                session,
                claim=claim,
                provider=observe_child_provider(configured_child_provider(), operation=claim.generation.operation),
            )
        return {
            "generation_id": str(result.generation_id),
            "report_id": str(result.report_id) if result.report_id is not None else None,
            "status": result.status,
            "provider_calls": result.provider_calls,
        }


@app.task(name="child.reconcile_generations")  # type: ignore[untyped-decorator]
def reconcile_child_generations() -> dict[str, int]:
    return run_async_in_worker(_reconcile_child_generations_async())


async def _reconcile_child_generations_async() -> dict[str, int]:
    async with async_session_factory() as session:
        repository = ChildRepository(session)
        result = await repository.reconcile_stuck_generations(
            now=datetime.now(UTC),
            max_attempts=settings.CHILD_GENERATION_MAX_ATTEMPTS,
            retry_base_seconds=settings.CHILD_GENERATION_RETRY_BASE_SECONDS,
        )
        await session.commit()
        generation_ids = await list_queued_generation_ids(session, now=datetime.now(UTC))
        dispatched = 0
        failed = 0
        for generation_id in generation_ids:
            task_id = await repository.claim_generation_dispatch(
                generation_id=generation_id,
                now=datetime.now(UTC),
                lease_duration=timedelta(seconds=settings.CHILD_GENERATION_DISPATCH_LEASE_SECONDS),
            )
            if task_id is None:
                continue
            await session.commit()
            succeeded = False
            try:
                dispatched_task_id = dispatch_child_generation(generation_id=generation_id)
                if dispatched_task_id != task_id:
                    raise RuntimeError("Child generation dispatcher returned an unstable task id")
                succeeded = True
            except Exception:
                failed += 1
            await repository.record_generation_dispatch_outcome(
                generation_id=generation_id,
                task_id=task_id,
                succeeded=succeeded,
                now=datetime.now(UTC),
            )
            await session.commit()
            if succeeded:
                dispatched += 1
        return {
            "requeued": len(result.requeued_generation_ids),
            "terminal": len(result.terminal_generation_ids),
            "dispatched": dispatched,
            "dispatch_failed": failed,
        }
