import asyncio
import signal
from collections.abc import Coroutine, Generator
from selectors import BaseSelector, SelectorKey
from typing import Any

import pytest
from billiard.exceptions import SoftTimeLimitExceeded  # type: ignore[import-untyped]
from billiard.pool import soft_timeout_sighandler  # type: ignore[import-untyped]

from app.infrastructure import celery_async


@pytest.fixture
def worker_loop(monkeypatch: pytest.MonkeyPatch) -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    monkeypatch.setattr(celery_async, "_TASK_LOOP", loop)
    try:
        yield loop
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


def test_soft_timeout_drains_interrupted_coroutine_before_worker_reuses_loop(
    worker_loop: asyncio.AbstractEventLoop,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    finalized = []
    started = False
    fired = False
    selector: BaseSelector = getattr(worker_loop, "_selector")  # noqa: B009
    select = selector.select

    def interrupt_select(timeout: float | None = None) -> list[tuple[SelectorKey, int]]:
        nonlocal fired
        if started and not fired:
            fired = True
            signal.raise_signal(signal.SIGUSR1)
        return select(timeout)

    monkeypatch.setattr(selector, "select", interrupt_select)

    async def interrupted() -> None:
        nonlocal started
        started = True
        try:
            await asyncio.sleep(60)
        finally:
            await asyncio.sleep(0)
            finalized.append(True)

    previous = signal.signal(signal.SIGUSR1, soft_timeout_sighandler)
    try:
        with pytest.raises(SoftTimeLimitExceeded):
            celery_async.run_async_in_worker(interrupted())
    finally:
        signal.signal(signal.SIGUSR1, previous)

    assert finalized == [True]
    assert not asyncio.all_tasks(worker_loop)


def test_soft_timeout_after_root_scheduled_never_restarts_old_delivery(
    worker_loop: asyncio.AbstractEventLoop, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_task = worker_loop.create_task
    calls: list[str] = []
    fired = False

    def interrupt_root(coro: Coroutine[Any, Any, Any], **kwargs: Any) -> asyncio.Task[Any]:
        nonlocal fired
        task = create_task(coro, **kwargs)
        if not fired:
            fired = True
            signal.raise_signal(signal.SIGUSR1)
        return task

    async def interrupted() -> None:
        calls.append("old delivery")

    monkeypatch.setattr(worker_loop, "create_task", interrupt_root)
    previous = signal.signal(signal.SIGUSR1, soft_timeout_sighandler)
    try:
        with pytest.raises(SoftTimeLimitExceeded):
            celery_async.run_async_in_worker(interrupted())
    finally:
        signal.signal(signal.SIGUSR1, previous)

    pending_at_return = asyncio.all_tasks(worker_loop)
    celery_async.run_async_in_worker(asyncio.sleep(0))
    assert calls == []
    assert not pending_at_return


def test_soft_timeout_during_initial_task_step_registration_has_no_loop_errors(
    worker_loop: asyncio.AbstractEventLoop, monkeypatch: pytest.MonkeyPatch
) -> None:
    call_soon = worker_loop.call_soon
    calls: list[str] = []
    errors: list[dict[str, Any]] = []
    fired = False

    def interrupt_step(callback: Any, *args: Any, **kwargs: Any) -> asyncio.Handle:
        nonlocal fired
        handle = call_soon(callback, *args, **kwargs)
        if not fired and isinstance(getattr(callback, "__self__", None), asyncio.Task):
            fired = True
            signal.raise_signal(signal.SIGUSR1)
        return handle

    async def interrupted() -> None:
        calls.append("old delivery")

    worker_loop.set_exception_handler(lambda _loop, context: errors.append(context))
    monkeypatch.setattr(worker_loop, "call_soon", interrupt_step)
    previous = signal.signal(signal.SIGUSR1, soft_timeout_sighandler)
    try:
        with pytest.raises(SoftTimeLimitExceeded):
            celery_async.run_async_in_worker(interrupted())
        celery_async.run_async_in_worker(asyncio.sleep(0))
    finally:
        signal.signal(signal.SIGUSR1, previous)

    assert fired and calls == []
    assert errors == []
