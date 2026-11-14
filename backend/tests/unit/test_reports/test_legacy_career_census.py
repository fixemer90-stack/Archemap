"""Offline census safety: explicit credentials, aggregate output, read-only DB."""

from __future__ import annotations

import importlib
import importlib.util
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

MODULE = "scripts.legacy_career_census"


def _tool() -> Any:
    assert importlib.util.find_spec(MODULE) is not None, "E20 needs a read-only aggregate census tool"
    return importlib.import_module(MODULE)


def test_census_requires_an_explicit_database_and_does_not_load_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    tool = _tool()
    monkeypatch.delenv("E20_CENSUS_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://must-not-use@example.invalid/customer")
    with pytest.raises(ValueError, match="census_database_url_missing"):
        tool.database_url_from_env("E20_CENSUS_DATABASE_URL")
    source = (Path(__file__).resolve().parents[3] / "scripts/legacy_career_census.py").read_text()
    assert "from app.config" not in source
    assert "load_dotenv" not in source


@pytest.mark.parametrize("value", ["sqlite:///a.db", "http://example.invalid", "not a database url"])
def test_census_rejects_non_postgresql_urls_without_echoing_credentials(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    tool = _tool()
    monkeypatch.setenv("E20_CENSUS_DATABASE_URL", value)
    with pytest.raises(ValueError, match="census_database_url_invalid") as error:
        tool.database_url_from_env("E20_CENSUS_DATABASE_URL")
    assert value not in str(error.value)


class _Result:
    def __init__(self, value: Any) -> None:
        self.value = value

    def scalar_one(self) -> Any:
        return self.value


class _Connection:
    def __init__(self, *, active: bool = False, read_only: str = "on") -> None:
        self.active = active
        self.read_only = read_only
        self.commands: list[str] = []
        self.finished = False

    def in_transaction(self) -> bool:
        return self.active

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[None]:
        self.commands.append("BEGIN")
        try:
            yield
        finally:
            self.finished = True

    async def exec_driver_sql(self, statement: str) -> _Result:
        self.commands.append(statement)
        if statement == "SHOW transaction_read_only":
            return _Result(self.read_only)
        if statement == "SHOW transaction_isolation":
            return _Result("repeatable read")
        if statement.lstrip().startswith("WITH"):
            return _Result({"contract_version": "e20_legacy_career_census_v1", "reports": {"rows": 2}})
        return _Result(None)


@pytest.mark.asyncio
async def test_census_enforces_readonly_snapshot_before_its_only_aggregate_query() -> None:
    tool = _tool()
    connection = _Connection()
    result = await tool.collect_census(cast(AsyncConnection, connection))
    assert result["reports"]["rows"] == 2
    assert connection.commands[1] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
    assert connection.commands.index("SHOW transaction_read_only") < len(connection.commands) - 1
    assert connection.commands[-1].lstrip().startswith("WITH")
    assert connection.finished
    query = connection.commands[-1]
    assert "report_data" not in query and "email" not in query and "birth_date" not in query
    assert all(word not in query.upper().split() for word in ("INSERT", "UPDATE", "DELETE", "DROP"))
    assert "requires_observation_telemetry" in query
    assert "subscription_id" in query


@pytest.mark.asyncio
async def test_census_refuses_to_adopt_a_callers_existing_transaction() -> None:
    connection = _Connection(active=True)
    with pytest.raises(ValueError, match="fresh_connection_required"):
        await _tool().collect_census(cast(AsyncConnection, connection))
    assert connection.commands == []


@pytest.mark.asyncio
async def test_census_stops_if_the_database_does_not_confirm_readonly() -> None:
    connection = _Connection(read_only="off")
    with pytest.raises(ValueError, match="census_readonly_unconfirmed"):
        await _tool().collect_census(cast(AsyncConnection, connection))
    assert not any(command.lstrip().startswith("WITH") for command in connection.commands)
    assert connection.finished


def test_census_help_never_includes_the_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    tool = _tool()
    secret = "postgresql+asyncpg://private-user:private-password@private-host/private-db"
    monkeypatch.setenv("E20_CENSUS_DATABASE_URL", secret)
    assert secret not in tool.build_parser().format_help()
    assert "confirm-read-only" in tool.build_parser().format_help()
    args = vars(tool.build_parser().parse_args(["--confirm-read-only"]))
    assert args["database_url_env"] == "E20_CENSUS_DATABASE_URL"
    assert secret not in json.dumps(args)
