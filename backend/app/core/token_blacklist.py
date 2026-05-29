"""Token blacklist — invalidate JWTs on logout."""

from __future__ import annotations

import structlog

from app.infrastructure.redis import get_redis_client

logger = structlog.get_logger()

BLACKLIST_PREFIX = "token:blacklist:"
DEFAULT_TTL_SECONDS = 86400 * 30  # 30 days (max refresh token lifetime)


async def blacklist_token(jti: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
    """Add a token JTI to the blacklist."""
    client = get_redis_client()
    key = f"{BLACKLIST_PREFIX}{jti}"
    await client.set(key, "1", ex=ttl_seconds)
    logger.info("token_blacklisted", jti=jti)


async def is_token_blacklisted(jti: str) -> bool:
    """Check if a token JTI is blacklisted."""
    client = get_redis_client()
    key = f"{BLACKLIST_PREFIX}{jti}"
    result = await client.get(key)
    return result is not None
