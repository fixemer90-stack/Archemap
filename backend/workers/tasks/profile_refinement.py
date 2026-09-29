"""Recovery dispatcher for committed birth-data refinements."""

from __future__ import annotations

from typing import Any

from app.infrastructure.celery_async import run_async_in_worker
from app.infrastructure.database import async_session_factory
from app.modules.profiles.dispatch import dispatch_pending_birth_data_revisions
from workers.celery_app import app


@app.task(name="profiles.dispatch_birth_data_refinements")  # type: ignore[untyped-decorator]
def dispatch_birth_data_refinements() -> dict[str, Any]:
    return run_async_in_worker(_dispatch_birth_data_refinements_async())


async def _dispatch_birth_data_refinements_async() -> dict[str, Any]:
    async with async_session_factory() as session:
        dispatched, failed = await dispatch_pending_birth_data_revisions(session)
    return {"dispatched": dispatched, "failed": failed}
