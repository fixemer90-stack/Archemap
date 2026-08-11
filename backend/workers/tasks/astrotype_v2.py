"""Astrotype v2 report generation background tasks."""

from __future__ import annotations

import asyncio
from typing import Any

from workers.celery_app import app


@app.task(name="astrotype_v2.generate_natal_report", bind=True)  # type: ignore[untyped-decorator]
def generate_natal_report_v2(
    self: object,
    *,
    profile_id: str,
    user_id: str,
    generation_id: str,
    force: bool = False,
) -> dict[str, Any]:
    """Run the v2 generation pipeline outside the request lifecycle."""

    return asyncio.run(
        _generate_natal_report_v2_async(
            profile_id=profile_id,
            user_id=user_id,
            generation_id=generation_id,
            force=force,
        )
    )


async def _generate_natal_report_v2_async(
    *,
    profile_id: str,
    user_id: str,
    generation_id: str,
    force: bool,
) -> dict[str, Any]:
    """Placeholder execution boundary until full orchestration is wired."""

    _ = user_id
    return {
        "contract_version": "astrotype_v2_generation_task_v1",
        "generation_id": generation_id,
        "profile_id": profile_id,
        "status": "accepted",
        "force": force,
    }
