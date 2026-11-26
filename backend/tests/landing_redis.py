"""Isolated real Redis using the production landing service's server arguments."""

import asyncio
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError


def production_compose() -> dict[str, Any]:
    compose_path = Path(__file__).resolve().parents[2] / "docker-compose.prod.yml"
    return cast(dict[str, Any], yaml.safe_load(compose_path.read_text()))


@asynccontextmanager
async def disposable_landing_redis(socket: Path, data: Path) -> AsyncIterator[str]:
    executable = shutil.which("redis-server")
    if executable is None:
        pytest.skip("redis-server is not installed")
    _, *args = production_compose()["services"]["landing-redis"]["command"]
    # Change only the data path and listener for the disposable native process.
    args[args.index("--dir") + 1] = str(data)
    process = await asyncio.create_subprocess_exec(
        executable,
        *args,
        "--port",
        "0",
        "--unixsocket",
        str(socket),
        "--unixsocketperm",
        "700",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    url = f"unix://{socket}"
    try:
        async with asyncio.timeout(3), Redis.from_url(url) as client:
            while True:
                if process.returncode is not None:
                    logs, _ = await process.communicate()
                    pytest.fail(f"Landing Redis failed to start: {logs.decode(errors='replace')}")
                try:
                    if await client.ping():
                        break
                except RedisConnectionError:
                    await asyncio.sleep(0.02)
        yield url
    finally:
        if process.returncode is None:
            process.terminate()
            await process.communicate()
        await asyncio.to_thread(socket.unlink, missing_ok=True)
