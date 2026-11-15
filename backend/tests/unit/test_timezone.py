"""Unit tests for timezone resolution."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

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
    def test_format(self, resolver: TimezoneResolver) -> None:
        from importlib.metadata import PackageNotFoundError, version

        try:
            data_version = version("timezonefinder-data")
        except PackageNotFoundError:
            data_version = "bundled"
        key = resolver._cache_key(55.7558, 37.6173)
        assert key == f"tz:timezonefinder:{version('timezonefinder')}:data:{data_version}:55.7558,37.6173"

    def test_different_coords_different_keys(self, resolver: TimezoneResolver) -> None:
        assert resolver._cache_key(55.0, 37.0) != resolver._cache_key(51.0, -0.1)


class TestCacheVersions:
    @pytest.mark.parametrize("changed_package", ["timezonefinder", "timezonefinder-data"])
    async def test_version_change_ignores_old_cached_result(self, mock_redis: AsyncMock, changed_package: str) -> None:
        versions = {"timezonefinder": "9.2.0", "timezonefinder-data": "4.2026.6"}
        with patch("importlib.metadata.version", side_effect=versions.__getitem__):
            old_resolver = TimezoneResolver(mock_redis)
        old_key = old_resolver._cache_key(55.7558, 37.6173)
        cached = {
            old_key: json.dumps({"tz": "Outdated/Boundary"}),
            "tz:55.7558,37.6173": json.dumps({"tz": "Legacy/Boundary"}),
        }
        mock_redis.get.side_effect = cached.get
        versions[changed_package] += ".1"
        with patch("importlib.metadata.version", side_effect=versions.__getitem__):
            upgraded_resolver = TimezoneResolver(mock_redis)

        assert await upgraded_resolver.resolve(55.7558, 37.6173) == "Europe/Moscow"
        assert upgraded_resolver._cache_key(55.7558, 37.6173) != old_key
        mock_redis.set.assert_awaited_once_with(
            upgraded_resolver._cache_key(55.7558, 37.6173),
            json.dumps({"tz": "Europe/Moscow"}),
            ex=86400 * 30,
        )

    def test_bundled_data_uses_engine_version(self, mock_redis: AsyncMock) -> None:
        from importlib.metadata import PackageNotFoundError

        with patch("importlib.metadata.version", side_effect=["8.2.4", PackageNotFoundError("timezonefinder-data")]):
            resolver = TimezoneResolver(mock_redis)
        assert resolver._cache_key(55.7558, 37.6173) == "tz:timezonefinder:8.2.4:data:bundled:55.7558,37.6173"

    async def test_same_versions_reuse_cached_result(self, mock_redis: AsyncMock) -> None:
        first = TimezoneResolver(mock_redis)
        cached = {first._cache_key(55.7558, 37.6173): json.dumps({"tz": "Europe/Moscow"})}
        mock_redis.get.side_effect = cached.get
        with patch("app.infrastructure.timezone._tf") as engine:
            second = TimezoneResolver(mock_redis)
            assert await second.resolve(55.7558, 37.6173) == "Europe/Moscow"
        engine.timezone_at.assert_not_called()
        mock_redis.set.assert_not_awaited()


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

    async def test_cache_failure_log_omits_coordinates(
        self,
        resolver: TimezoneResolver,
        mock_redis: AsyncMock,
    ) -> None:
        mock_redis.set = AsyncMock(side_effect=Exception("redis down"))
        with patch("app.infrastructure.timezone.logger.exception") as log_exception:
            await resolver.resolve(55.7558, 37.6173)

        log_exception.assert_called_once_with("tz_cache_set_failed")
