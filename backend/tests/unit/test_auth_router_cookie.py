"""Cookie-first auth router tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.modules.auth.router import login, logout, refresh
from app.modules.auth.schemas import LoginRequest

TEST_PASSWORD = "password123"
ACCESS_TOKEN = "access.jwt"
REFRESH_TOKEN = "refresh.jwt"


def _set_cookie_headers(response: object) -> list[str]:
    raw_headers = getattr(response, "raw_headers", [])
    return [value.decode() for key, value in raw_headers if key.lower() == b"set-cookie"]


class _LimiterStub:
    def _make_key(self, prefix: str, identifier: str) -> str:
        return f"{prefix}:{identifier}"

    async def check_rate_limit(self, *_: object) -> bool:
        return True

    async def get_retry_after(self, *_: object) -> int:
        return 0

    async def increment_rate_limit(self, *_: object) -> None:
        return None

    async def reset_rate_limit(self, *_: object) -> None:
        return None


@pytest.mark.asyncio
async def test_login_sets_httponly_auth_cookies() -> None:
    tokens = {
        "access_token": ACCESS_TOKEN,
        "refresh_token": REFRESH_TOKEN,
        "token_type": "bearer",
    }

    with (
        patch("app.modules.auth.router.RateLimiter", return_value=_LimiterStub()),
        patch("app.modules.auth.router.get_redis_client", return_value=object()),
        patch("app.modules.auth.router.AuthService") as service_cls,
    ):
        service_cls.return_value.login = AsyncMock(return_value=tokens)
        response = await login(
            LoginRequest(email="user@example.com", password=TEST_PASSWORD),
            db=AsyncMock(),
        )

    set_cookie = _set_cookie_headers(response)
    assert any("access_token=access.jwt" in header and "HttpOnly" in header for header in set_cookie)
    assert any("refresh_token=refresh.jwt" in header and "HttpOnly" in header for header in set_cookie)
    assert all("SameSite=lax" in header for header in set_cookie)


@pytest.mark.asyncio
async def test_refresh_uses_cookie_and_rotates_httponly_cookies() -> None:
    request = SimpleNamespace(cookies={"refresh_token": "old.refresh"})
    tokens = {
        "access_token": "new.access",
        "refresh_token": "new.refresh",
        "token_type": "bearer",
    }

    with patch("app.modules.auth.router.AuthService") as service_cls:
        service_cls.return_value.refresh_tokens = AsyncMock(return_value=tokens)
        response = await refresh(request=request, body=None, db=AsyncMock())  # type: ignore[arg-type]

    service_cls.return_value.refresh_tokens.assert_awaited_once_with("old.refresh")
    set_cookie = _set_cookie_headers(response)
    assert any("access_token=new.access" in header and "HttpOnly" in header for header in set_cookie)
    assert any("refresh_token=new.refresh" in header and "HttpOnly" in header for header in set_cookie)


@pytest.mark.asyncio
async def test_logout_reads_cookie_tokens_and_deletes_current_and_legacy_cookies() -> None:
    request = SimpleNamespace(
        cookies={
            "access_token": ACCESS_TOKEN,
            "refresh_token": REFRESH_TOKEN,
        }
    )

    with patch("app.modules.auth.router.AuthService") as service_cls:
        service_cls.return_value.logout = AsyncMock()
        response = await logout(
            request=request,  # type: ignore[arg-type]
            current_user_id=uuid4(),
            authorization=None,
            refresh_token=None,
            db=AsyncMock(),
        )

    service_cls.return_value.logout.assert_awaited_once_with(
        access_token=ACCESS_TOKEN,
        refresh_token=REFRESH_TOKEN,
    )
    set_cookie = _set_cookie_headers(response)
    for cookie_name in (
        "access_token",
        "refresh_token",
        "astrotype_token",
        "astrotype_refresh_token",
    ):
        assert any(f"{cookie_name}=" in header and "Max-Age=0" in header for header in set_cookie)
