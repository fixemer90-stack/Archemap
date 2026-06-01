"""FastAPI dependency injection helpers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.core.token_blacklist import is_token_blacklisted
from app.infrastructure.database import async_session_factory
from app.infrastructure.redis import get_redis_client

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


# ── Current user ──────────────────────────────────────────────────────
async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)] = None,
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """Validate JWT and return the user's UUID.

    Checks token from:
    1. Authorization header (Bearer token)
    2. HttpOnly cookie (access_token)
    """
    token = None

    # Try Authorization header first
    if credentials:
        token = credentials.credentials

    # Fallback to HttpOnly cookie (CRIT-01)
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    # Check if token is blacklisted (logged out)
    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    return UUID(user_id)
