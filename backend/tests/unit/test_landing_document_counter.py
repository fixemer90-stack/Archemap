import asyncio
import logging
import re
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from time import time_ns
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from redis.exceptions import NoPermissionError

from app.config import settings
from app.main import create_app
from app.modules.analytics import landing_documents as landing
from tests.landing_redis import disposable_landing_redis, production_compose


def test_production_landing_redis_is_isolated_from_persistent_redis() -> None:
    compose = production_compose()
    services = compose["services"]
    store = services["landing-redis"]
    assert set(store["networks"]) == {"landing-storage"}
    assert compose["networks"]["landing-storage"]["internal"] is True
    assert store["read_only"] is True
    assert store["mem_limit"] == store["memswap_limit"] == "64m"
    assert len(store["tmpfs"]) == 1 and store["tmpfs"][0].startswith("/data:")
    assert "ports" not in store and "volumes" not in store
    assert {name for name, svc in services.items() if "landing-storage" in svc.get("networks", [])} == {
        "landing-redis",
        "backend",
    }
    assert "ports" not in services["backend"]
    assert services["backend"]["environment"]["LANDING_DOCUMENT_REDIS_URL"] == "redis://landing-redis:6379/0"
    assert services["redis"]["command"] == ["redis-server", "--appendonly", "yes"]
    assert services["redis"]["volumes"] == ["redis_data:/data"]


@pytest.mark.parametrize("dedicated_url", [None, "invalid://sentinel"])
async def test_missing_or_invalid_dedicated_store_never_falls_back(
    dedicated_url: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "LANDING_DOCUMENT_COUNTER_ENABLED", True)
    monkeypatch.setattr(settings, "LANDING_DOCUMENT_REDIS_URL", dedicated_url)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://must-not-connect.invalid/0")
    original = Redis.from_url

    def checked_url(url: str, **kwargs: Any) -> Redis:
        assert url == dedicated_url, "landing counter must never acquire shared Redis"
        return original(url, **kwargs)

    monkeypatch.setattr(Redis, "from_url", checked_url)
    app = FastAPI()
    app.add_middleware(landing.LandingDocumentSignalMiddleware)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://backend") as client:
        response = await client.post("/_internal/landing-document", headers={"X-Astrotype-Landing-Signal": "1"})
    assert response.status_code == 503
    assert (await landing.read_landing_documents(datetime.now(UTC))).observed is None


def test_only_internal_signal_is_omitted_from_uvicorn_access_log(caplog: pytest.LogCaptureFixture) -> None:
    create_app()
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        logger = logging.getLogger("uvicorn.access")
        for path in ("/_internal/landing-document?private=sentinel", "/api/v1/health"):
            logger.info('%s - "%s %s HTTP/%s" %d', "peer", "POST", path, "1.1", 204)
    assert [record.getMessage() for record in caplog.records if record.name == "uvicorn.access"] == [
        'peer - "POST /api/v1/health HTTP/1.1" 204'
    ]


async def test_internal_signal_defaults_off_without_opening_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LANDING_DOCUMENT_COUNTER_ENABLED", False)

    def forbidden() -> None:
        pytest.fail("disabled counter must not acquire Redis")

    monkeypatch.setattr(landing, "_redis", forbidden)
    app = FastAPI()
    app.add_middleware(landing.LandingDocumentSignalMiddleware)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://backend") as client:
        signal = await client.post("/_internal/landing-document", headers={"X-Astrotype-Landing-Signal": "1"})
    assert signal.status_code == 404
    assert (await landing.read_landing_documents(datetime(2026, 11, 26, 21, tzinfo=UTC))).model_dump() == {
        "through_date": date(2026, 11, 27),
        "observed": None,
    }


async def test_malformed_internal_signals_never_touch_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LANDING_DOCUMENT_COUNTER_ENABLED", True)

    def forbidden() -> None:
        pytest.fail("non-internal signal must not acquire Redis")

    monkeypatch.setattr(landing, "_redis", forbidden)
    app = FastAPI()
    app.add_middleware(landing.LandingDocumentSignalMiddleware)
    headers = {"X-Astrotype-Landing-Signal": "1"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://backend") as client:
        for response in (
            await client.get("/_internal/landing-document", headers=headers),
            await client.post("/_internal/landing-document"),
            await client.post("/_internal/landing-document?private=1", headers=headers),
            await client.post("/_internal/landing-document", headers={**headers, "Origin": "https://astrotype.ru"}),
        ):
            assert response.status_code == 404


async def test_disposable_redis_expires_buckets_and_does_not_restore_after_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    socket = tmp_path.parent / "s05.sock"  # Unix socket paths have a small OS limit.
    url = f"unix://{socket}"
    monkeypatch.setattr(settings, "LANDING_DOCUMENT_REDIS_URL", url)
    monkeypatch.setattr(settings, "LANDING_DOCUMENT_COUNTER_ENABLED", True)
    app = FastAPI()
    app.add_middleware(landing.LandingDocumentSignalMiddleware)
    started = datetime.now(UTC)
    moscow = ZoneInfo("Europe/Moscow")
    keys = [landing._key(started.astimezone(moscow).date() + timedelta(days=i)) for i in (0, 1)]
    expired = landing._key(started.astimezone(moscow).date() - timedelta(days=1))

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://backend") as client:

            async def emit() -> int:
                return (
                    await client.post(
                        "/_internal/landing-document",
                        headers={"X-Astrotype-Landing-Signal": "1", "Referer": "https://test.invalid/sentinel"},
                    )
                ).status_code

            async with disposable_landing_redis(socket, tmp_path):
                redis = landing._redis()
                assert await redis.config_get("save", "appendonly") == {"save": "", "appendonly": "no"}
                assert (await landing.read_landing_documents(started)).observed is None
                for _ in range(5):
                    assert await asyncio.gather(*(emit() for _ in range(4))) == [204] * 4
                values = await redis.mget(keys)
                assert await redis.dbsize() == sum(value is not None for value in values)
                total = 0
                for key, value in zip(keys, values, strict=True):
                    if value is None:
                        continue
                    assert re.fullmatch(r"business:landing-documents:v1:\d{4}-\d{2}-\d{2}", key)
                    day = date.fromisoformat(key.rsplit(":", 1)[1])
                    expires = datetime.combine(day + timedelta(days=30), time.min, moscow)
                    assert await redis.expiretime(key) == int(expires.timestamp())
                    total += int(value)
                assert total == (await landing.read_landing_documents(datetime.now(UTC))).observed == 20

                expiration = int(datetime.now(UTC).timestamp()) + 2
                assert await redis.eval(landing._WRITE, 1, expired, expiration, time_ns() // 1_000 + 1_000_000) == 1
                assert await redis.mget([expired]) == ["1"]
                for _ in range(60):
                    if await redis.mget([expired]) == [None]:
                        break
                    await asyncio.sleep(0.05)
                else:
                    pytest.fail("Redis did not expire the short-lived bucket")
                for command in (
                    "SAVE",
                    "BGSAVE",
                    "BGREWRITEAOF",
                    "CONFIG SET appendonly yes",
                    "REPLICAOF localhost 1",
                    "MGET unrelated",
                ):
                    with pytest.raises(NoPermissionError):
                        await redis.execute_command(*command.split())  # type: ignore[no-untyped-call]

            assert await asyncio.to_thread(lambda: list(tmp_path.iterdir())) == []
            assert await emit() == 503
            assert (await landing.read_landing_documents(datetime.now(UTC))).observed is None
            async with disposable_landing_redis(socket, tmp_path):
                assert await redis.dbsize() == 0
                assert await redis.mget([*keys, expired]) == [None, None, None]
                assert (await landing.read_landing_documents(datetime.now(UTC))).observed is None
                assert await emit() == 204
                assert (await landing.read_landing_documents(datetime.now(UTC))).observed == 1
            assert await asyncio.to_thread(lambda: list(tmp_path.iterdir())) == []
    finally:
        if landing._redis_for_url.cache_info().currsize:
            await landing._redis().aclose()
            landing._redis_for_url.cache_clear()


async def test_queued_increment_does_not_land_on_redis_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Hold the actual wire command beyond the HTTP timeout. Keep it independently
    # of the client's socket lifetime, as a transport queue can retain sent bytes.
    store = tmp_path.parent / "s05s.sock"
    proxy = tmp_path.parent / "s05p.sock"
    captured = asyncio.Event()
    release = asyncio.Event()
    replies: asyncio.Queue[bytes] = asyncio.Queue()

    async def relay(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        upstream, connection = await asyncio.open_unix_connection(store)
        try:
            while header := await reader.readline():
                # The test proxies only the Redis handshake and EVAL, whose
                # replies each occupy a single line. Read a complete RESP command.
                chunks = [header]
                fields = []
                for _ in range(int(header[1:])):
                    length = await reader.readline()
                    field = await reader.readexactly(int(length[1:]) + 2)
                    chunks.extend((length, field))
                    fields.append(field[:-2])
                queued = fields[0].upper() == b"EVAL" and not captured.is_set()
                if queued:
                    captured.set()
                    await release.wait()
                connection.writelines(chunks)
                await connection.drain()
                reply = await upstream.readline()
                if queued:
                    await replies.put(reply)
                    return  # The sender has already timed out.
                writer.write(reply)
                await writer.drain()
        finally:
            connection.close()
            writer.close()
            await connection.wait_closed()
            await writer.wait_closed()

    monkeypatch.setattr(settings, "LANDING_DOCUMENT_COUNTER_ENABLED", True)
    monkeypatch.setattr(settings, "LANDING_DOCUMENT_REDIS_URL", f"unix://{proxy}?protocol=2")
    app = FastAPI()
    app.add_middleware(landing.LandingDocumentSignalMiddleware)

    async with disposable_landing_redis(store, tmp_path) as url, Redis.from_url(url) as redis:
        server = await asyncio.start_unix_server(relay, proxy)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://backend") as client:
                headers = {"X-Astrotype-Landing-Signal": "1"}
                response = await client.post("/_internal/landing-document", headers=headers)
                assert response.status_code == 503
                assert captured.is_set(), "the complete write was queued before the sink timed out"
                assert await redis.dbsize() == 0

                release.set()
                reply = await asyncio.wait_for(replies.get(), 2)
                assert await redis.dbsize() == 0, f"the relayed stale write changed storage: {reply!r}"
                assert reply == b":0\r\n"  # Redis itself ran the write script and rejected it.

                assert (await client.post("/_internal/landing-document", headers=headers)).status_code == 204
                key = landing._key(datetime.now(UTC).astimezone(ZoneInfo("Europe/Moscow")).date())
                assert await redis.mget([key]) == [b"1"]
                assert await redis.dbsize() == 1
        finally:
            server.close()
            release.set()
            await landing._redis().aclose()
            landing._redis_for_url.cache_clear()
            await server.wait_closed()
            proxy.unlink(missing_ok=True)
