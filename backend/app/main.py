"""Archemap — FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.middleware import RequestLoggingMiddleware
from app.api.v1 import api_router
from app.config import settings

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown events."""
    logger.info("Starting Archemap", env=settings.APP_ENV)
    # ── startup ──
    from app.infrastructure.database import engine
    from app.infrastructure.redis import get_redis_client

    # verify redis connection
    redis_client = get_redis_client()
    try:
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception:
        logger.warning("Redis unavailable on startup")
    finally:
        await redis_client.aclose()

    yield

    # ── shutdown ──
    await engine.dispose()
    logger.info("Archemap stopped")


def create_app() -> FastAPI:
    application = FastAPI(
        title="Archemap API",
        version="0.1.0",
        docs_url="/docs" if settings.APP_DEBUG else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # ── middleware (order matters: last added = first executed) ──
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── routes ──
    application.include_router(api_router, prefix="/api/v1")

    # ── observability ──
    if settings.SENTRY_DSN:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE)

    FastAPIInstrumentor.instrument_app(application)

    return application


app = create_app()


def run() -> None:  # pragma: no cover
    """CLI entry point invoked via `archemap` command."""
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    run()
