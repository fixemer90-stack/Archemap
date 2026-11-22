"""Helpers for running async code inside sync Celery worker tasks."""

from __future__ import annotations

import asyncio
import signal
from collections.abc import Coroutine
from contextvars import ContextVar
from dataclasses import dataclass
from threading import current_thread, main_thread
from types import FrameType
from typing import Any, TypeVar

from billiard.exceptions import SoftTimeLimitExceeded  # type: ignore[import-untyped]
from billiard.pool import SIG_SOFT_TIMEOUT, soft_timeout_sighandler  # type: ignore[import-untyped]

T = TypeVar("T")

_TASK_LOOP: asyncio.AbstractEventLoop | None = None


@dataclass
class _SoftTimeout:
    requested: bool = False


_SOFT_TIMEOUT: ContextVar[_SoftTimeout | None] = ContextVar("worker_soft_timeout", default=None)


def check_worker_soft_timeout() -> None:
    """Keep queued side effects from starting ahead of the loop's cancellation callback."""
    timeout = _SOFT_TIMEOUT.get()
    if timeout is not None and timeout.requested:
        raise asyncio.CancelledError


async def _drain_cancelled_task(task: asyncio.Task[Any]) -> None:
    await asyncio.gather(task, return_exceptions=True)


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

    loop = _TASK_LOOP
    timeout = _SoftTimeout()
    task: asyncio.Task[T] | None = None
    started = False
    guarded: Coroutine[Any, Any, T] | None = None
    signum: int | None = SIG_SOFT_TIMEOUT
    if signum is not None and (
        current_thread() is not main_thread() or signal.getsignal(signum) is not soft_timeout_sighandler
    ):
        signum = None

    def cancel_delivery() -> None:
        if task is not None and not task.done():
            task.cancel()

    def request_timeout(_signum: int, _frame: FrameType | None) -> None:
        # Never raise from the signal handler inside asyncio/TaskGroup bookkeeping.
        if not timeout.requested:
            timeout.requested = True
            loop.call_soon_threadsafe(cancel_delivery)

    async def run_delivery() -> T:
        nonlocal started
        check_worker_soft_timeout()
        started = True
        return await coro

    token = _SOFT_TIMEOUT.set(timeout)
    try:
        if signum is not None:
            signal.signal(signum, request_timeout)
        guarded = run_delivery()
        task = loop.create_task(guarded)
        result = loop.run_until_complete(task)
    except BaseException as exc:
        if task is not None and not task.done():
            task.cancel()
            loop.run_until_complete(_drain_cancelled_task(task))
        if timeout.requested:
            raise SoftTimeLimitExceeded() from exc
        raise
    finally:
        try:
            _SOFT_TIMEOUT.reset(token)
            if task is None and guarded is not None:
                guarded.close()
            if not started:
                coro.close()
        finally:
            if signum is not None:
                signal.signal(signum, soft_timeout_sighandler)
    if timeout.requested:
        raise SoftTimeLimitExceeded()
    return result
