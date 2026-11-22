import asyncio
import signal
from collections.abc import Coroutine, Generator
from selectors import BaseSelector, SelectorKey
from typing import Any

import pytest
from billiard.exceptions import SoftTimeLimitExceeded  # type: ignore[import-untyped]

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

    def timeout_handler(*_args: object) -> None:
        raise SoftTimeLimitExceeded

    async def interrupted() -> None:
        nonlocal started
        started = True
        try:
            await asyncio.sleep(60)
        finally:
            await asyncio.sleep(0)
            finalized.append(True)

    previous = signal.signal(signal.SIGUSR1, timeout_handler)
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

    def timeout_handler(*_args: object) -> None:
        raise SoftTimeLimitExceeded

    async def interrupted() -> None:
        calls.append("old delivery")

    monkeypatch.setattr(worker_loop, "create_task", interrupt_root)
    previous = signal.signal(signal.SIGUSR1, timeout_handler)
    try:
        with pytest.raises(SoftTimeLimitExceeded):
            celery_async.run_async_in_worker(interrupted())
    finally:
        signal.signal(signal.SIGUSR1, previous)

    pending_at_return = asyncio.all_tasks(worker_loop)
    celery_async.run_async_in_worker(asyncio.sleep(0))
    assert calls == []
    assert not pending_at_return
