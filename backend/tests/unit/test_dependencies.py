"""Unit tests for FastAPI dependencies."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies import get_current_user


@pytest.mark.asyncio
async def test_get_current_user_rejects_unverified_user() -> None:
    user_id = uuid4()
    request = MagicMock()
    request.cookies = {}
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="token",
    )

    user = SimpleNamespace(is_active=True, is_verified=False)
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = AsyncMock()
    db.execute.return_value = result

    with (
        patch("app.dependencies.decode_access_token", return_value={"sub": str(user_id), "jti": "jti"}),
        patch("app.dependencies.is_token_blacklisted", new=AsyncMock(return_value=False)),
        pytest.raises(HTTPException) as exc_info,
    ):
        await get_current_user(request=request, credentials=credentials, db=db)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Email не подтверждён. Проверьте почту и перейдите по ссылке подтверждения."


@pytest.mark.asyncio
async def test_get_current_user_accepts_verified_user() -> None:
    user_id = uuid4()
    request = MagicMock()
    request.cookies = {}
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="token",
    )

    user = SimpleNamespace(is_active=True, is_verified=True)
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = AsyncMock()
    db.execute.return_value = result

    with (
        patch("app.dependencies.decode_access_token", return_value={"sub": str(user_id), "jti": "jti"}),
        patch("app.dependencies.is_token_blacklisted", new=AsyncMock(return_value=False)),
    ):
        current_user_id = await get_current_user(
            request=request,
            credentials=credentials,
            db=db,
        )

    assert current_user_id == user_id


@pytest.mark.asyncio
async def test_get_current_user_falls_back_to_cookie_when_authorization_header_is_stale() -> None:
    user_id = uuid4()
    request = MagicMock()
    request.cookies = {"access_token": "fresh-cookie-token"}
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="stale-header-token",
    )

    user = SimpleNamespace(is_active=True, is_verified=True)
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = AsyncMock()
    db.execute.return_value = result

    def decode_token(token: str) -> dict[str, str] | None:
        if token == "fresh-cookie-token":
            return {"sub": str(user_id), "jti": "fresh-jti"}
        return None

    with (
        patch("app.dependencies.decode_access_token", side_effect=decode_token),
        patch("app.dependencies.is_token_blacklisted", new=AsyncMock(return_value=False)),
    ):
        current_user_id = await get_current_user(
            request=request,
            credentials=credentials,
            db=db,
        )

    assert current_user_id == user_id
