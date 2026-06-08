"""Helpers for running async code inside sync Celery worker tasks."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")

_TASK_LOOP: asyncio.AbstractEventLoop | None = None


def run_async_in_worker(coro: Coroutine[Any, Any, T]) -> T:  # noqa: UP047
    """Run async code on a process-scoped event loop.

    Celery prefork workers execute one task at a time per child process, so a
    single long-lived loop avoids asyncpg pool objects being rebound to a new
    loop on every task invocation.
    """
    global _TASK_LOOP

    if _TASK_LOOP is None or _TASK_LOOP.is_closed():
        _TASK_LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_TASK_LOOP)

    return _TASK_LOOP.run_until_complete(coro)
