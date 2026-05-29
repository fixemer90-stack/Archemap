"""Shared pytest fixtures for the Archemap test suite."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.dependencies import get_db, get_redis
from app.infrastructure.database import Base
from app.main import app

# ── Use a separate test database ──────────────────────────────────────
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/archemap", "/archemap_test")
TEST_REDIS_URL = settings.REDIS_URL.replace("/0", "/15")

test_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():  # type: ignore[no-untyped-def]
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def _setup_database() -> AsyncGenerator[None, None]:
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        yield session


@pytest.fixture
async def test_redis() -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
    client = aioredis.from_url(TEST_REDIS_URL, decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()  # type: ignore[union-attr]


@pytest.fixture
async def client(db_session: AsyncSession, test_redis: aioredis.Redis) -> AsyncGenerator[AsyncClient, None]:  # type: ignore[type-arg]
    """Async test client with overridden dependencies."""

    async def _override_db():
        yield db_session

    async def _override_redis():
        yield test_redis

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
