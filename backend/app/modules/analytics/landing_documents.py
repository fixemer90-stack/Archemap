"""Best-effort count of observed landing responses; never a traffic total."""

import asyncio
import logging
from datetime import date, datetime, time, timedelta
from functools import cache
from time import time_ns
from zoneinfo import ZoneInfo

from pydantic import BaseModel, PositiveInt
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from starlette.datastructures import Headers
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings

_MOSCOW = ZoneInfo("Europe/Moscow")
_RETENTION_DAYS = 30  # expiry is 30 days from the start of the bucket, not its last write
_PREFIX = "business:landing-documents:v1:"
_SIGNAL_PATH = "/_internal/landing-document"
_WRITE_BUDGET_MS = 250
_WRITE = """
local deadline_us = tonumber(ARGV[2])
if not deadline_us then return 0 end
local now = redis.call('TIME')
local now_us = tonumber(now[1]) * 1000000 + tonumber(now[2])
if now_us >= deadline_us then return 0 end
redis.call('INCR', KEYS[1])
redis.call('EXPIREAT', KEYS[1], ARGV[1])
return 1
"""


class _SignalAccessLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Uvicorn h11 and httptools both put the target in argument 3.
        args = record.args
        if isinstance(args, tuple) and len(args) == 5 and isinstance(path := args[2], str):
            return path.partition("?")[0] != _SIGNAL_PATH
        return True


_LOG_FILTER = _SignalAccessLogFilter()


def omit_signal_access_log() -> None:
    logging.getLogger("uvicorn.access").addFilter(_LOG_FILTER)


class LandingDocuments(BaseModel):
    through_date: date
    observed: PositiveInt | None = None


def _redis() -> Redis:
    url = settings.LANDING_DOCUMENT_REDIS_URL
    if not url:
        raise ValueError("landing document storage is not configured")
    return _redis_for_url(url)


@cache
def _redis_for_url(url: str) -> Redis:
    # Never put these buckets in the persistent application/Celery Redis.
    return Redis.from_url(
        url,
        decode_responses=True,
        max_connections=8,
        retry=Retry(NoBackoff(), 0),
    )


def _key(day: date) -> str:
    return f"{_PREFIX}{day.isoformat()}"


async def read_landing_documents(now: datetime) -> LandingDocuments:
    day = now.astimezone(_MOSCOW).date()
    result = LandingDocuments(through_date=day)
    if not settings.LANDING_DOCUMENT_COUNTER_ENABLED:
        return result
    try:
        async with asyncio.timeout(0.25):
            values = await _redis().mget([_key(day - timedelta(days=i)) for i in range(_RETENTION_DAYS)])
        counts = [int(value) for value in values if value is not None]
        total = sum(counts)
        if counts and min(counts) > 0 and total <= 2**53 - 1:
            result.observed = total
    except (RedisError, OSError, TimeoutError, ValueError):
        pass
    # Missing/expired days, off periods and write failures are not proven zeros.
    return result


class LandingDocumentSignalMiddleware:
    """Receive an empty signal on the private service network, before API middleware."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] != _SIGNAL_PATH:
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        status = 404
        if (
            settings.LANDING_DOCUMENT_COUNTER_ENABLED
            and scope["method"] == "POST"
            and scope.get("raw_path") == _SIGNAL_PATH.encode()
            and not scope.get("query_string")
            and headers.getlist("x-astrotype-landing-signal") == ["1"]
            and not any(name in headers for name in ("origin", "cookie", "authorization", "transfer-encoding"))
            and headers.get("content-length", "0") == "0"
        ):
            # A client timeout cannot retract queued bytes. Pass an absolute
            # deadline, checked atomically by the co-located Redis before INCR.
            received_us = time_ns() // 1_000
            deadline_us = received_us + _WRITE_BUDGET_MS * 1_000
            day = datetime.fromtimestamp(received_us // 1_000_000, _MOSCOW).date()
            expires = datetime.combine(day + timedelta(days=_RETENTION_DAYS), time.min, _MOSCOW)
            status = 503
            try:
                async with asyncio.timeout(_WRITE_BUDGET_MS / 1_000):
                    admitted = await _redis().eval(_WRITE, 1, _key(day), int(expires.timestamp()), deadline_us)
                if admitted == 1:
                    status = 204
            except (RedisError, OSError, TimeoutError, ValueError):
                pass
        await Response(status_code=status, headers={"Cache-Control": "no-store"})(scope, receive, send)
