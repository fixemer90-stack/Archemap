"""Unit tests for geocoding infrastructure."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.infrastructure.geocoding import GeocodeResult, NominatimGeocoder


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    return redis


@pytest.fixture
def geocoder(mock_redis: AsyncMock) -> NominatimGeocoder:
    return NominatimGeocoder(mock_redis)


class TestCacheKey:
    def test_lowercase_and_strip(self) -> None:
        assert NominatimGeocoder._cache_key("  Moscow  ") == "geocode:moscow"

    def test_different_queries_different_keys(self) -> None:
        assert NominatimGeocoder._cache_key("Moscow") != NominatimGeocoder._cache_key("London")


class TestCacheHit:
    async def test_returns_cached_results(self, geocoder: NominatimGeocoder, mock_redis: AsyncMock) -> None:
        cached_data = json.dumps(
            [
                {
                    "display_name": "Moscow, Russia",
                    "latitude": 55.75,
                    "longitude": 37.62,
                    "city": "Moscow",
                    "country": "Russia",
                }
            ]
        )
        mock_redis.get = AsyncMock(return_value=cached_data)

        results = await geocoder.search("Moscow")

        assert len(results) == 1
        assert results[0].city == "Moscow"
        assert results[0].latitude == 55.75
        mock_redis.get.assert_awaited_once()

    async def test_cache_miss_fetches_from_nominatim(self, geocoder: NominatimGeocoder, mock_redis: AsyncMock) -> None:
        mock_redis.get = AsyncMock(return_value=None)

        nominatim_response = [
            {
                "display_name": "London, UK",
                "lat": "51.5074",
                "lon": "-0.1278",
                "address": {"city": "London", "country": "United Kingdom"},
            }
        ]

        with patch("app.infrastructure.geocoding.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = nominatim_response
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await geocoder.search("London")

        assert len(results) == 1
        assert results[0].city == "London"
        assert results[0].country == "United Kingdom"
        mock_redis.set.assert_awaited_once()


class TestCacheSerialization:
    async def test_roundtrip(self) -> None:
        original = [GeocodeResult(display_name="Test", latitude=1.0, longitude=2.0, city="City", country="Country")]
        data = json.dumps(
            [
                {
                    "display_name": r.display_name,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "city": r.city,
                    "country": r.country,
                }
                for r in original
            ]
        )
        items = json.loads(data)
        restored = [GeocodeResult(**item) for item in items]
        assert restored == original

    async def test_empty_cache_returns_none(self, geocoder: NominatimGeocoder, mock_redis: AsyncMock) -> None:
        mock_redis.get = AsyncMock(return_value=None)

        with patch("app.infrastructure.geocoding.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = []
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await geocoder.search("NonexistentPlace123")

        assert results == []
        mock_redis.set.assert_not_awaited()


class TestNominatimParsing:
    async def test_address_fallback(self, geocoder: NominatimGeocoder, mock_redis: AsyncMock) -> None:
        """When city is missing, town/village/municipality should be used."""
        mock_redis.get = AsyncMock(return_value=None)

        nominatim_response = [
            {
                "display_name": "Small Village",
                "lat": "50.0",
                "lon": "30.0",
                "address": {"town": "Smalltown", "country": "Testland"},
            }
        ]

        with patch("app.infrastructure.geocoding.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = nominatim_response
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await geocoder.search("Small Village")

        assert results[0].city == "Smalltown"

    async def test_http_error_returns_empty(self, geocoder: NominatimGeocoder, mock_redis: AsyncMock) -> None:
        mock_redis.get = AsyncMock(return_value=None)

        with patch("app.infrastructure.geocoding.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.HTTPError("network error"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await geocoder.search("Test")

        assert results == []
