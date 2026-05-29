"""Unit tests for the Redis-backed rate limiter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.rate_limit import RateLimiter


@pytest.fixture
def mock_redis() -> MagicMock:
    """Return a mock Redis client with async methods."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    redis.delete = AsyncMock()
    redis.ttl = AsyncMock(return_value=900)
    # pipeline mock
    pipe = MagicMock()
    pipe.incr = MagicMock()
    pipe.expire = MagicMock()
    pipe.execute = AsyncMock(return_value=[1, True])
    redis.pipeline.return_value = pipe
    return redis


@pytest.fixture
def limiter(mock_redis: MagicMock) -> RateLimiter:
    return RateLimiter(mock_redis)


# ── test_rate_limit_allows_within_limit ───────────────────────────────
@pytest.mark.asyncio
async def test_rate_limit_allows_within_limit(
    limiter: RateLimiter,
    mock_redis: MagicMock,
) -> None:
    """Requests under the threshold should be allowed."""
    mock_redis.get.return_value = None  # no existing counter
    allowed = await limiter.check_rate_limit("rate_limit:login:test@example.com", 5, 900)
    assert allowed is True


# ── test_rate_limit_blocks_after_exceeded ─────────────────────────────
@pytest.mark.asyncio
async def test_rate_limit_blocks_after_exceeded(
    limiter: RateLimiter,
    mock_redis: MagicMock,
) -> None:
    """Requests at or above the threshold should be blocked."""
    mock_redis.get.return_value = "5"  # already at limit
    allowed = await limiter.check_rate_limit("rate_limit:login:test@example.com", 5, 900)
    assert allowed is False


# ── test_rate_limit_resets_on_success ─────────────────────────────────
@pytest.mark.asyncio
async def test_rate_limit_resets_on_success(
    limiter: RateLimiter,
    mock_redis: MagicMock,
) -> None:
    """After a successful login the counter should be deleted."""
    await limiter.reset_rate_limit("rate_limit:login:test@example.com")
    mock_redis.delete.assert_awaited_once_with("rate_limit:login:test@example.com")


# ── test_rate_limit_independent_keys ──────────────────────────────────
@pytest.mark.asyncio
async def test_rate_limit_independent_keys(
    limiter: RateLimiter,
    mock_redis: MagicMock,
) -> None:
    """Different identifiers should have independent counters."""
    # First key: at limit
    mock_redis.get.return_value = "5"
    blocked = await limiter.check_rate_limit("rate_limit:login:bad@example.com", 5, 900)
    assert blocked is False

    # Second key: no counter yet
    mock_redis.get.return_value = None
    allowed = await limiter.check_rate_limit("rate_limit:login:good@example.com", 5, 900)
    assert allowed is True
