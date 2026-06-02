"""Health check endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    checks: dict[str, Any] = {"status": "ok"}

    # database ping
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        checks["status"] = "degraded"

    # redis ping
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        checks["status"] = "degraded"

    return checks


@router.get("/health/secrets")
async def secrets_status() -> dict[str, Any]:
    """Check which secrets are configured (without revealing values).

    Only available in development/staging.
    """
    from app.config import settings
    from app.core.secrets import get_secret_status

    if settings.APP_ENV == "production":
        return {"error": "Not available in production"}

    status = get_secret_status()
    return {
        "configured": {k: v for k, v in status.items() if v},
        "missing": [k for k, v in status.items() if not v],
    }
