"""FastAPI dependency injection helpers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated, Any
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.core.token_blacklist import is_token_blacklisted
from app.infrastructure.database import async_session_factory
from app.infrastructure.redis import get_redis_client
from app.modules.users.models import User

_bearer_scheme = HTTPBearer(auto_error=False)


# ── Database session ──────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Redis client ──────────────────────────────────────────────────────
async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()


def _candidate_access_tokens(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> list[str]:
    """Return access-token candidates from newest browser/session locations.

    The frontend can hold a stale JS-managed Authorization token while a valid
    HttpOnly OAuth cookie is also present. Treat tokens as candidates instead of
    letting one bad header shadow a good cookie-backed session.
    """
    candidates: list[str] = []
    if credentials:
        candidates.append(credentials.credentials)

    for cookie_name in ("access_token", "astrotype_token"):
        cookie_token = request.cookies.get(cookie_name)
        if cookie_token and cookie_token not in candidates:
            candidates.append(cookie_token)

    return candidates


async def _decode_valid_access_token(token: str) -> dict[str, Any] | None:
    payload = decode_access_token(token)
    if payload is None:
        return None

    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        return None

    return payload


# ── Current user ──────────────────────────────────────────────────────
async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)] = None,
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """Validate JWT and return the user's UUID.

    Checks token candidates from:
    1. Authorization header (Bearer token)
    2. HttpOnly OAuth cookie (access_token)
    3. JS-managed app cookie (astrotype_token)
    """
    payload = None
    for token in _candidate_access_tokens(request, credentials):
        payload = await _decode_valid_access_token(token)
        if payload is not None:
            break

    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    user_uuid = UUID(user_id)
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    return user_uuid
