"""Geocoding provider — Nominatim (OpenStreetMap) with Redis cache."""

from __future__ import annotations

import json
from dataclasses import dataclass

import httpx
import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
CACHE_TTL_SECONDS = 86400  # 24 hours


@dataclass(frozen=True, slots=True)
class GeocodeResult:
    """A single geocoding hit."""

    display_name: str
    latitude: float
    longitude: float
    city: str
    country: str


class NominatimGeocoder:
    """Geocode place names via Nominatim with Redis caching."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    @staticmethod
    def _cache_key(query: str) -> str:
        return f"geocode:{query.strip().lower()}"

    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[GeocodeResult]:
        """Search for places matching *query*.

        Results are cached in Redis for 24 h.
        Returns an empty list when nothing matches.
        """
        # ── cache hit ─────────────────────────────────────────────────
        cached = await self._get_from_cache(query)
        if cached is not None:
            return cached

        # ── cache miss → Nominatim ────────────────────────────────────
        results = await self._fetch_from_nominatim(query, limit)
        await self._set_in_cache(query, results)
        return results

    # ── Nominatim HTTP call ───────────────────────────────────────────
    async def _fetch_from_nominatim(
        self, query: str, limit: int
    ) -> list[GeocodeResult]:
        params = {
            "q": query,
            "format": "jsonv2",
            "limit": str(limit),
            "accept-language": "ru,en",
            "addressdetails": "1",
        }
        headers = {"User-Agent": "Archemap/0.1 (astro-platform)"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    NOMINATIM_SEARCH_URL, params=params, headers=headers
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, httpx.TimeoutException):
            logger.exception("geocoding_request_failed", query=query)
            return []

        results: list[GeocodeResult] = []
        for item in data:
            address = item.get("address", {})
            city = (
                address.get("city")
                or address.get("town")
                or address.get("village")
                or address.get("municipality")
                or ""
            )
            country = address.get("country", "")
            results.append(
                GeocodeResult(
                    display_name=item.get("display_name", ""),
                    latitude=float(item["lat"]),
                    longitude=float(item["lon"]),
                    city=city,
                    country=country,
                )
            )
        return results

    # ── Redis cache helpers ───────────────────────────────────────────
    async def _get_from_cache(self, query: str) -> list[GeocodeResult] | None:
        try:
            raw = await self._redis.get(self._cache_key(query))
        except Exception:
            return None
        if raw is None:
            return None
        try:
            items = json.loads(raw)
            return [GeocodeResult(**item) for item in items]
        except (json.JSONDecodeError, TypeError):
            return None

    async def _set_in_cache(
        self, query: str, results: list[GeocodeResult]
    ) -> None:
        if not results:
            return
        try:
            data = json.dumps(
                [
                    {
                        "display_name": r.display_name,
                        "latitude": r.latitude,
                        "longitude": r.longitude,
                        "city": r.city,
                        "country": r.country,
                    }
                    for r in results
                ],
                ensure_ascii=False,
            )
            await self._redis.set(
                self._cache_key(query), data, ex=CACHE_TTL_SECONDS
            )
        except Exception:
            logger.exception("geocoding_cache_set_failed", query=query)
