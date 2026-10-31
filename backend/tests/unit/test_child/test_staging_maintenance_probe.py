"""Exercise the actual read-only probe algorithms with synthetic transports."""

from __future__ import annotations

import re
from typing import Any

import pytest
import sqlalchemy.ext.asyncio
from scripts import child_staging_probe as probe


class Broker:
    def scan_iter(self, *, count: int) -> list[bytes]:
        assert count == 100
        return [b"celery", b"celery\x06\x169", b"forgotten", b"unacked", b"unacked_index", b"celery"]

    def type(self, key: bytes) -> bytes:
        return b"hash" if key == b"unacked" else b"zset" if key == b"unacked_index" else b"list"

    def llen(self, key: bytes) -> int:
        return 1

    def hlen(self, key: bytes) -> int:
        return 2

    def zcard(self, key: bytes) -> int:
        return 2


def test_all_priority_and_forgotten_queues_and_unacked_are_counted_without_duplicate_scan_keys() -> None:
    assert probe.broker_state(Broker(), ["celery"]) == {"queues": ["celery"], "pending": 3, "unacked": 4}


class Context:
    def __init__(self, value: Any) -> None:
        self.value = value

    async def __aenter__(self) -> Any:
        return self.value

    async def __aexit__(self, *args: Any) -> None:
        pass


class Result:
    def __init__(self, rows: list[Any]) -> None:
        self.rows = rows

    def scalars(self) -> list[Any]:
        return self.rows

    def scalar_one(self) -> Any:
        return self.rows[0]

    def __aiter__(self) -> Any:
        async def rows() -> Any:
            for row in self.rows:
                yield (row,)

        return rows()


class Database:
    def __init__(self, *, bad: str) -> None:
        self.bad = bad
        self.statements: list[str] = []
        self.disposed = False

    def connect(self) -> Context:
        return Context(self)

    def begin(self) -> Context:
        return Context(self)

    async def dispose(self) -> None:
        self.disposed = True

    async def execute(self, statement: Any) -> Result:
        sql = str(statement)
        self.statements.append(sql)
        if "pg_tables" in sql:
            return Result(sorted(set(probe.TABLE_TERMINALS) | probe.SPECIAL_TABLES))
        if "information_schema" in sql:
            return Result([*probe.TABLE_TERMINALS, *(["unknown_generations"] if self.bad == "schema" else [])])
        if "pg_stat_activity" in sql:
            return Result([int(self.bad == "transaction")])
        return Result([])

    async def stream(self, statement: Any) -> Result:
        sql = str(statement)
        self.statements.append(sql)
        table = re.search(r'public\."([a-z0-9_]+)"', sql)
        assert table
        name = table[1]
        row: dict[str, Any] = {"status": "ready", "dispatch_status": "dispatched"}
        if name == "payments":
            row = {"status": "succeeded"}
        elif name == "payment_webhooks":
            row = {"processed": True}
        elif name == probe.EVENT_TABLE:
            row = {"event_code": "status_transitioned", "error_code": None}
            if self.bad == "event_unknown":
                row["error_code"] = "child_narrative_provider_outcome_unknown"
        elif name == "career_generations" and self.bad == "other_family":
            row["status"] = "queued"
        return Result([row])


@pytest.mark.parametrize("bad", ["none", "event_unknown", "other_family", "transaction", "schema"])
async def test_real_durable_probe_queries_all_families_readonly_and_rejects_unknowns(
    monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    database = Database(bad=bad)
    monkeypatch.setattr(sqlalchemy.ext.asyncio, "create_async_engine", lambda url: database)
    if bad == "schema":
        with pytest.raises(ValueError):
            await probe.durable_state("postgresql+asyncpg://synthetic@127.0.0.1:1/disposable")
    else:
        result = await probe.durable_state("postgresql+asyncpg://synthetic@127.0.0.1:1/disposable")
        assert result["nonterminal"] == int(bad != "none")
        assert result["unknown"] == int(bad == "event_unknown")
        assert set(result["tables"]) == set(probe.TABLE_TERMINALS) | probe.SPECIAL_TABLES
    assert database.disposed
    assert database.statements[0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
    assert all(statement.startswith(("SET ", "SELECT ")) for statement in database.statements)
    assert "to_jsonb" not in str(locals().get("result", {}))  # No raw rows/SQL in result evidence.
