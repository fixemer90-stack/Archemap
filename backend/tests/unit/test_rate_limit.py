"""Unit tests for rate limiting middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.middleware import _get_client_ip, _get_rate_limit_key


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
        assert "rate_limit:/api/v1/auth/login:1.2.3.4" == key
        assert max_req == 5
        assert window == 900

    def test_geocode_endpoint(self) -> None:
        request = MagicMock()
        request.url.path = "/api/v1/profiles/geocode"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"

        key, max_req, window = _get_rate_limit_key(request)
        assert "rate_limit:/api/v1/profiles/geocode:10.0.0.1" == key
        assert max_req == 30
        assert window == 60

    def test_authenticated_global(self) -> None:
        request = MagicMock()
        request.url.path = "/api/v1/profiles"
        request.headers = {"Authorization": "Bearer abcdef1234567890"}
        request.client = MagicMock()
        request.client.host = "1.2.3.4"

        key, max_req, window = _get_rate_limit_key(request)
        assert "rate_limit:global:user:abcdef1234567890" == key
        assert max_req == 100
        assert window == 60

    def test_anonymous_global(self) -> None:
        request = MagicMock()
        request.url.path = "/api/v1/profiles"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "1.2.3.4"

        key, max_req, window = _get_rate_limit_key(request)
        assert "rate_limit:global:ip:1.2.3.4" == key
        assert max_req == 20
        assert window == 60
