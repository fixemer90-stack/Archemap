"""Timezone resolution — IANA timezone from coordinates.

Uses ``timezonefinder`` (offline, based on the IANA tz database)
so no external API call is needed.  Results are cached in Redis
because the mapping is deterministic for a given (lat, lon) pair.
"""

from __future__ import annotations

import json

import redis.asyncio as aioredis
import structlog
from timezonefinder import TimezoneFinder

logger = structlog.get_logger()

CACHE_TTL_SECONDS = 86400 * 30  # 30 days — coordinates don't change TZ

_tf = TimezoneFinder(in_memory=True)


class TimezoneResolver:
    """Resolve latitude/longitude to an IANA timezone string."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    @staticmethod
    def _cache_key(lat: float, lon: float) -> str:
        return f"tz:{lat:.4f},{lon:.4f}"

    async def resolve(self, latitude: float, longitude: float) -> str | None:
        """Return IANA timezone (e.g. ``Europe/Moscow``) or *None*.

        The lookup is first tried against Redis cache, then computed
        offline via ``timezonefinder``.
        """
        cached = await self._get_from_cache(latitude, longitude)
        if cached is not None:
            return cached

        tz_name = _tf.timezone_at(lat=latitude, lng=longitude)
        if tz_name:
            await self._set_in_cache(latitude, longitude, tz_name)
        return str(tz_name) if tz_name else None

    # ── cache helpers ─────────────────────────────────────────────────
    async def _get_from_cache(self, lat: float, lon: float) -> str | None:
        try:
            raw = await self._redis.get(self._cache_key(lat, lon))
        except Exception:
            return None
        if raw is None:
            return None
        try:
            data: dict[str, str] = json.loads(raw)
            return data.get("tz")
        except (json.JSONDecodeError, TypeError):
            return None

    async def _set_in_cache(self, lat: float, lon: float, tz: str) -> None:
        try:
            await self._redis.set(
                self._cache_key(lat, lon),
                json.dumps({"tz": tz}),
                ex=CACHE_TTL_SECONDS,
            )
        except Exception:
            logger.exception("tz_cache_set_failed", lat=lat, lon=lon)
