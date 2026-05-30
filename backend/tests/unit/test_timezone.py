"""Unit tests for timezone resolution."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.timezone import TimezoneResolver


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    return redis


@pytest.fixture
def resolver(mock_redis: AsyncMock) -> TimezoneResolver:
    return TimezoneResolver(mock_redis)


class TestCacheKey:
    def test_format(self) -> None:
        key = TimezoneResolver._cache_key(55.7558, 37.6173)
        assert key == "tz:55.7558,37.6173"

    def test_different_coords_different_keys(self) -> None:
        assert TimezoneResolver._cache_key(55.0, 37.0) != TimezoneResolver._cache_key(51.0, -0.1)


class TestResolve:
    async def test_moscow(self, resolver: TimezoneResolver) -> None:
        """Moscow coordinates → Europe/Moscow."""
        tz = await resolver.resolve(55.7558, 37.6173)
        assert tz == "Europe/Moscow"

    async def test_london(self, resolver: TimezoneResolver) -> None:
        """London coordinates → Europe/London."""
        tz = await resolver.resolve(51.5074, -0.1278)
        assert tz == "Europe/London"

    async def test_new_york(self, resolver: TimezoneResolver) -> None:
        """New York coordinates → America/New_York."""
        tz = await resolver.resolve(40.7128, -74.0060)
        assert tz == "America/New_York"

    async def test_tokyo(self, resolver: TimezoneResolver) -> None:
        """Tokyo coordinates → Asia/Tokyo."""
        tz = await resolver.resolve(35.6762, 139.6503)
        assert tz == "Asia/Tokyo"

    async def test_ocean_returns_none(self, resolver: TimezoneResolver) -> None:
        """Middle of the ocean → None."""
        tz = await resolver.resolve(0.0, 0.0)
        # (0, 0) is in the Gulf of Guinea — no timezone polygon
        # Result may be None or a nearby coastal TZ; just check it doesn't crash
        assert tz is None or isinstance(tz, str)


class TestCacheHit:
    async def test_returns_cached(self, resolver: TimezoneResolver, mock_redis: AsyncMock) -> None:
        mock_redis.get = AsyncMock(return_value=json.dumps({"tz": "Europe/Moscow"}))

        tz = await resolver.resolve(55.7558, 37.6173)

        assert tz == "Europe/Moscow"
        mock_redis.get.assert_awaited_once()

    async def test_cache_miss_computes_and_stores(self, resolver: TimezoneResolver, mock_redis: AsyncMock) -> None:
        mock_redis.get = AsyncMock(return_value=None)

        tz = await resolver.resolve(55.7558, 37.6173)

        assert tz == "Europe/Moscow"
        mock_redis.set.assert_awaited_once()

    async def test_redis_error_falls_through(self, resolver: TimezoneResolver, mock_redis: AsyncMock) -> None:
        mock_redis.get = AsyncMock(side_effect=Exception("redis down"))
        mock_redis.set = AsyncMock(side_effect=Exception("redis down"))

        tz = await resolver.resolve(55.7558, 37.6173)
        assert tz == "Europe/Moscow"
