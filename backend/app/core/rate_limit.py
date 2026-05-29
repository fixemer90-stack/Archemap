"""Redis-backed rate limiting for authentication endpoints."""

from __future__ import annotations

import redis.asyncio as aioredis


class RateLimiter:
    """Token-bucket-style rate limiter using Redis INCR + EXPIRE.

    Keys follow the pattern ``rate_limit:{scope}:{identifier}``.
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    @staticmethod
    def _make_key(scope: str, identifier: str) -> str:
        return f"rate_limit:{scope}:{identifier}"

    async def check_rate_limit(
        self,
        key: str,
        max_attempts: int,
        window_seconds: int,
    ) -> bool:
        """Return *True* if the request is **within** the limit, *False* if exceeded."""
        current = await self._redis.get(key)
        return current is None or int(current) < max_attempts

    async def increment_rate_limit(
        self,
        key: str,
        window_seconds: int,
    ) -> None:
        """Atomically increment the counter and set expiry if this is the first hit."""
        pipe = self._redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        await pipe.execute()

    async def reset_rate_limit(self, key: str) -> None:
        """Delete the counter (e.g. after a successful login)."""
        await self._redis.delete(key)

    async def get_retry_after(self, key: str) -> int:
        """Return the remaining TTL in seconds, or 0 if the key doesn't exist."""
        ttl = await self._redis.ttl(key)
        return max(ttl, 0)
