"""Async Redis client factory."""

from __future__ import annotations

import redis.asyncio as aioredis

from app.config import settings

_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(  # type: ignore[no-untyped-call]
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return _client
