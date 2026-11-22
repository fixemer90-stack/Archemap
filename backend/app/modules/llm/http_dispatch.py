"""Final admission check for Celery-owned LLM HTTP attempts."""

from __future__ import annotations

import httpx

from app.infrastructure.celery_async import check_worker_soft_timeout


async def guard_llm_http_request(_request: httpx.Request) -> None:
    # HTTPX invokes this after encoding the request, immediately before sending it.
    check_worker_soft_timeout()
