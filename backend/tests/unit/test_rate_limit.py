"""Unit tests for rate limiting middleware."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.api.middleware import _get_client_ip, _get_rate_limit_key, _increment_rate_limit
from app.config import settings


class TestGetClientIp:
    """Test client IP extraction."""

    def test_forwarded_for(self) -> None:
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}
        request.client = None
        assert _get_client_ip(request) == "1.2.3.4"

    def test_client_host(self) -> None:
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"
        assert _get_client_ip(request) == "10.0.0.1"

    def test_no_client(self) -> None:
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == "unknown"


class TestGetRateLimitKey:
    """Test rate limit key generation."""

    def test_login_endpoint(self) -> None:
        request = MagicMock()
        request.url.path = "/api/v1/auth/login"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "1.2.3.4"

        key, max_req, window = _get_rate_limit_key(request)
        assert key == "rate_limit:/api/v1/auth/login:1.2.3.4"
        assert max_req == settings.RATE_LIMIT_LOGIN_MAX_ATTEMPTS
        assert window == settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS

    def test_geocode_endpoint(self) -> None:
        request = MagicMock()
        request.url.path = "/api/v1/profiles/geocode"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"

        key, max_req, window = _get_rate_limit_key(request)
        assert key == "rate_limit:/api/v1/profiles/geocode:10.0.0.1"
        assert max_req == settings.RATE_LIMIT_GEOCODE_PER_MINUTE
        assert window == 60

    def test_authenticated_global(self) -> None:
        request = MagicMock()
        request.url.path = "/api/v1/profiles"
        request.headers = {"Authorization": "Bearer abcdef1234567890"}
        request.cookies = {}
        request.client = MagicMock()
        request.client.host = "1.2.3.4"

        key, max_req, window = _get_rate_limit_key(request)
        assert key == "rate_limit:global:user:840881e18cbe4007"
        assert max_req == settings.RATE_LIMIT_GLOBAL_PER_MINUTE
        assert window == 60

    def test_cookie_authenticated_global(self) -> None:
        request = MagicMock()
        request.url.path = "/api/v1/profiles"
        request.headers = {}
        request.cookies = {"access_token": "cookie-token-for-one-user"}
        request.client = MagicMock()
        request.client.host = "1.2.3.4"

        key, max_req, window = _get_rate_limit_key(request)

        assert key.startswith("rate_limit:global:user:")
        assert key != "rate_limit:global:ip:1.2.3.4"
        assert max_req == settings.RATE_LIMIT_GLOBAL_PER_MINUTE
        assert window == 60

    def test_different_bearer_tokens_do_not_share_rate_limit_key(self) -> None:
        first = MagicMock()
        first.url.path = "/api/v1/profiles"
        first.headers = {"Authorization": "Bearer identical-jwt-prefix-user-one"}
        first.cookies = {}
        first.client = MagicMock(host="1.2.3.4")
        second = MagicMock()
        second.url.path = "/api/v1/profiles"
        second.headers = {"Authorization": "Bearer identical-jwt-prefix-user-two"}
        second.cookies = {}
        second.client = MagicMock(host="1.2.3.4")

        first_key, _, _ = _get_rate_limit_key(first)
        second_key, _, _ = _get_rate_limit_key(second)

        assert first_key != second_key

    def test_anonymous_global(self) -> None:
        request = MagicMock()
        request.url.path = "/api/v1/profiles"
        request.headers = {}
        request.cookies = {}
        request.client = MagicMock()
        request.client.host = "1.2.3.4"

        key, max_req, window = _get_rate_limit_key(request)
        assert key == "rate_limit:global:ip:1.2.3.4"
        assert max_req == settings.RATE_LIMIT_ANONYMOUS_PER_MINUTE
        assert window == 60


class _RedisCounterStub:
    def __init__(self, counts: list[int]) -> None:
        self._counts = iter(counts)
        self.expirations: list[tuple[str, int]] = []

    async def incr(self, key: str) -> int:
        return next(self._counts)

    async def expire(self, key: str, window: int) -> None:
        self.expirations.append((key, window))


@pytest.mark.asyncio
async def test_increment_rate_limit_sets_expiry_only_for_new_window() -> None:
    redis = _RedisCounterStub([1, 2])

    first_count = await _increment_rate_limit(redis, "rate-limit-key", 60)
    second_count = await _increment_rate_limit(redis, "rate-limit-key", 60)

    assert first_count == 1
    assert second_count == 2
    assert redis.expirations == [("rate-limit-key", 60)]
