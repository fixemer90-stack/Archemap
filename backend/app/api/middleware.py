"""Request logging and rate limiting middleware."""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.infrastructure.redis import get_redis_client

logger = structlog.get_logger()

# ── Rate limit config ────────────────────────────────────────────────
RATE_LIMITS: dict[str, tuple[int, int]] = {
    # path_prefix: (max_requests, window_seconds)
    "/api/v1/auth/login": (5, 900),
    "/api/v1/auth/register": (5, 900),
    "/api/v1/auth/password-reset": (5, 900),
    "/api/v1/profiles/geocode": (30, 60),
}


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _get_rate_limit_key(request: Request) -> tuple[str, int, int]:
    """Get rate limit key, max requests, and window for the request.

    Returns (key, max_requests, window_seconds).
    """
    ip = _get_client_ip(request)
    path = request.url.path

    # Check per-endpoint overrides
    for prefix, (max_req, window) in RATE_LIMITS.items():
        if path.startswith(prefix):
            return f"rate_limit:{prefix}:{ip}", max_req, window

    # Global rate limit
    # Try to extract user from token (without full validation)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        # Authenticated user — use token hash as key
        token_hash = auth_header[7:23]  # first 16 chars
        return (
            f"rate_limit:global:user:{token_hash}",
            settings.RATE_LIMIT_GLOBAL_PER_MINUTE,
            60,
        )

    # Anonymous — use IP
    return (
        f"rate_limit:global:ip:{ip}",
        settings.RATE_LIMIT_ANONYMOUS_PER_MINUTE,
        60,
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID and log every request/response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # bind correlation id to structlog contextvars
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers["X-Request-ID"] = correlation_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limiting middleware using Redis.

    Supports:
    - Per-endpoint overrides (login, geocode)
    - Per-user limits (authenticated)
    - Per-IP limits (anonymous)
    - Rate limit headers in response
    - 429 with Retry-After
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health checks and static files
        path = request.url.path
        if path in ("/api/v1/health", "/health", "/favicon.ico"):
            return await call_next(request)

        try:
            redis = get_redis_client()
        except Exception:
            # If Redis is down, skip rate limiting
            logger.warning("rate_limit_redis_unavailable")
            return await call_next(request)

        key, max_requests, window = _get_rate_limit_key(request)

        # Check current count
        current = await redis.get(key)
        current_count = int(current) if current else 0

        # Set rate limit headers
        remaining = max(0, max_requests - current_count - 1)
        ttl = await redis.ttl(key)
        reset = ttl if ttl > 0 else window

        if current_count >= max_requests:
            logger.warning(
                "rate_limit_exceeded",
                path=path,
                key=key,
                current=current_count,
                max=max_requests,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": reset,
                },
                headers={
                    "Retry-After": str(reset),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                },
            )

        # Increment counter
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        await pipe.execute()

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)

        return response
