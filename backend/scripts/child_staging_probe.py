"""Bundled read-only diagnostic, streamed into the exact staging backend.

No row payloads, task arguments, credentials or exception messages leave this probe.
Control inspections publish Celery pidbox diagnostics, never application tasks.
"""

from __future__ import annotations

import asyncio
import json
import socket
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

TABLE_TERMINALS = {
    "child_generations": {"ready", "narrative_failed", "failed", "age_update_ready", "age_update_failed"},
    "child_segment_generations": {"ready", "not_applicable", "failed"},
    "career_generations": {"ready", "narrative_failed", "failed"},
    "career_segment_generations": {"ready", "failed", "not_applicable"},
    "astrotype_v2_natal_report_generations": {"ready", "narrative_failed", "failed"},
    "astrotype_v2_report_segment_generations": {"ready", "failed_validation", "failed_provider", "skipped"},
    "profile_birth_data_revisions": {"ready", "failed"},
    "report_narratives": {"ready", "failed", "disabled", "narrative_failed"},
    "payments": {"succeeded", "failed", "cancelled", "refunded"},
}
EVENT_TABLE = "child_generation_events"
SPECIAL_TABLES = {EVENT_TABLE, "payment_webhooks"}
DIAGNOSTIC_FIELDS = {"error", "error_code", "last_error_code", "error_message", "diagnostics", "dispatch_error_code"}


def unknown(value: Any) -> bool:
    if isinstance(value, str):
        return "unknown" in value.lower() or "ambiguous" in value.lower()
    if isinstance(value, dict):
        return any(unknown(v) for v in value.values())
    if isinstance(value, list):
        return any(unknown(v) for v in value)
    return False


def pending_artifacts(value: Any) -> bool:
    if isinstance(value, dict):
        if "status" in value and value["status"] not in {"ready", "failed", "skipped", "disabled", "not_applicable"}:
            return True
        return any(pending_artifacts(v) for v in value.values())
    if isinstance(value, list):
        return any(pending_artifacts(v) for v in value)
    return False


def settled(table: str, row: dict[str, Any]) -> bool:
    if any(unknown(row.get(key)) for key in DIAGNOSTIC_FIELDS):
        return False
    if table == EVENT_TABLE:
        # Conservative: historical unknown diagnostics require incident review,
        # never silently infer resolution from a later terminal row.
        return True
    if table == "payment_webhooks":
        return row.get("processed") is True
    if row.get("status") not in TABLE_TERMINALS[table]:
        return False
    if table == "report_narratives" and pending_artifacts(row.get("content")):
        return False
    return not (table == "profile_birth_data_revisions" and row.get("dispatch_status") != "dispatched")


def require_endpoints(
    database: str, broker: str, endpoints: dict[str, list[str]], resolver: Callable[[str], str] = socket.gethostbyname
) -> None:
    for service, url, schemes in [("postgres", database, {"postgresql+asyncpg"}), ("redis", broker, {"redis"})]:
        parsed = urlsplit(url)
        if (
            parsed.scheme not in schemes
            or not parsed.hostname
            or not parsed.path
            or resolver(parsed.hostname) not in endpoints[service]
        ):
            raise ValueError("data endpoint not the exact inventoried staging service")


def broker_state(client: Any, queues: list[str]) -> dict[str, Any]:
    """All Redis lists + all hash/zset unacked representations, including priority keys.

    Count every list, not just queue-name LLEN: unseen priority or forgotten queues
    cannot disappear from the proof. Nonempty unrelated hash/zset is conservative STOP.
    """
    pending = unacked = 0
    for key in set(client.scan_iter(count=100)):
        kind = client.type(key)
        if kind == b"list":
            pending += client.llen(key)
        elif kind == b"hash":
            unacked += client.hlen(key)
        elif kind == b"zset":
            unacked += client.zcard(key)
    return {"queues": sorted(set(queues)), "pending": pending, "unacked": unacked}


def inspect_nodes(app: Any, nodes: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    discovered = app.control.inspect(timeout=10).ping()
    if not isinstance(discovered, dict):
        raise ValueError("node discovery failed")
    replies = {}
    for node in nodes:
        inspector = app.control.inspect(destination=[node], timeout=10)
        raw = {}
        for method in ("ping", "active_queues", "registered", "active", "reserved", "scheduled"):
            response = getattr(inspector, method)()
            if not isinstance(response, dict) or set(response) != {node}:
                raise ValueError("missing exact node response")
            raw[method] = response[node]
        replies[node] = {
            "ping": raw["ping"],
            "queues": sorted(q["name"] for q in raw["active_queues"]),
            "registered": sorted(raw["registered"]),
            # Preserve only occupancy; never task IDs/arguments.
            "active": [True] * len(raw["active"]),
            "reserved": [True] * len(raw["reserved"]),
            "scheduled": [True] * len(raw["scheduled"]),
        }
    return replies, sorted(discovered)


async def durable_state(url: str) -> dict[str, Any]:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url)
    nonterminal = unknown_count = 0
    try:
        async with engine.connect() as connection, connection.begin():
            await connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            await connection.execute(text("SET LOCAL statement_timeout = '15000ms'"))
            tables = set(
                (await connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))).scalars()
            )
            required = set(TABLE_TERMINALS) | SPECIAL_TABLES
            if not required.issubset(tables):
                raise ValueError("incomplete durable task schema")
            lifecycle = set(
                (
                    await connection.execute(
                        text(
                            "SELECT table_name FROM information_schema.columns WHERE table_schema='public' "
                            "AND column_name='status' AND (table_name LIKE '%generation%' "
                            "OR table_name LIKE '%revision%' "
                            "OR table_name LIKE '%narrative%')"
                        )
                    )
                ).scalars()
            )
            if lifecycle - set(TABLE_TERMINALS):
                raise ValueError("unreviewed durable task family")
            # Existing concurrent requests/transactions are not a quiescent API.
            nonterminal += int(
                (
                    await connection.execute(
                        text(
                            "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                            "AND pid<>pg_backend_pid() AND (state='active' OR state LIKE 'idle in transaction%')"
                        )
                    )
                ).scalar_one()
            )
            for table in sorted(required):
                # Identifiers are solely the literal source allowlist above.
                result = await connection.stream(text(f'SELECT to_jsonb(t) FROM public."{table}" t'))  # noqa: S608
                async for row in result:
                    value = row[0]
                    if any(unknown(value.get(key)) for key in DIAGNOSTIC_FIELDS):
                        unknown_count += 1
                    if not settled(table, value):
                        nonterminal += 1
    finally:
        await engine.dispose()
    return {"tables": sorted(required), "nonterminal": nonterminal, "unknown": unknown_count}


def http_connections(proc_tcp: str) -> int:
    """Conservative occupancy on the supported native Uvicorn listener (:8000)."""
    count = 0
    for line in proc_tcp.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 4:
            raise ValueError("unknown kernel TCP inventory shape")
        port = int(fields[1].rsplit(":", 1)[1], 16)
        if port == 8000 and fields[3] not in {"0A", "06", "07"}:
            # Ignore LISTEN, TIME_WAIT and CLOSED only. Never treat an accepted
            # request/half-open/close-wait socket as a confirmed quiet API.
            count += 1
    return count


def main() -> int:
    try:
        spec = json.load(sys.stdin)
        from app.config import settings

        # Must happen before importing/publishing any Celery inspections.
        require_endpoints(settings.DATABASE_URL, settings.CELERY_BROKER_URL, spec["endpoints"])
        import redis

        from workers.celery_app import app

        require_endpoints(settings.DATABASE_URL, str(app.conf.broker_url), spec["endpoints"])
        replies, discovered = inspect_nodes(app, spec["nodes"])
        queues = [q for node in spec["nodes"].values() for q in node["queues"]]
        client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        try:
            broker = broker_state(client, queues)
        finally:
            client.close()
        durable = asyncio.run(durable_state(settings.DATABASE_URL))
        inflight = sum(http_connections(Path(path).read_text()) for path in ("/proc/net/tcp", "/proc/net/tcp6"))
        print(
            "MAINTENANCE_RESULT="
            + json.dumps(
                {
                    "nodes": replies,
                    "discovered_nodes": discovered,
                    "broker": broker,
                    "durable": durable,
                    "http_inflight": inflight,
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception:
        # A remote library error can contain database URLs/row values.
        print("MAINTENANCE_PROBE_FAILED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
