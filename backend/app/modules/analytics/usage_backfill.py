"""Controlled read-only plan / insert-only projection of retained Child usage.

Historical diagnostics are aggregates over one section invocation. They are not
HTTP-attempt events, do not assign outcome to individual retries, and must never
be added to live transport evidence for overlapping intervals.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Index, String, Table, func, select, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.infrastructure.database import Base
from app.modules.analytics.usage_evidence import is_model_ref
from app.modules.child.models import ChildSegmentGeneration
from app.modules.llm.usage import validated_usage_aggregate

COUNTERS = ("http_attempts", "responses_with_usage", "responses_without_usage")
TOKENS = ("prompt_tokens", "completion_tokens", "total_tokens")
CACHE = ("prompt_cache_hit_tokens", "prompt_cache_miss_tokens")
MAX_ROWS = 5_000
VERSION = "child-usage-projection-v1"

child_usage_projection = Table(
    "business_child_usage_projection",
    Base.metadata,
    Column("segment_id", PG_UUID(as_uuid=True), primary_key=True),
    Column("segment_created_at", DateTime(timezone=True), nullable=False),
    Column("section_outcome", String(6), nullable=False),
    Column("provider", String(10), nullable=False),
    Column("model_ref", String(77), nullable=False),
    Column("http_attempts", BigInteger),
    Column("responses_with_usage", BigInteger),
    Column("responses_without_usage", BigInteger),
    Column("prompt_tokens", BigInteger),
    Column("completion_tokens", BigInteger),
    Column("total_tokens", BigInteger),
    Column("prompt_cache_hit_tokens", BigInteger),
    Column("prompt_cache_miss_tokens", BigInteger),
    CheckConstraint("provider IN ('deepseek','openrouter')", name="ck_business_child_usage_provider"),
    CheckConstraint("model_ref ~ '^model-sha256:[0-9a-f]{64}$'", name="ck_business_child_usage_model"),
    CheckConstraint("section_outcome IN ('ready','failed')", name="ck_business_child_usage_outcome"),
    CheckConstraint(
        "num_nonnulls(http_attempts,responses_with_usage,responses_without_usage)=0 OR "
        "(num_nonnulls(http_attempts,responses_with_usage,responses_without_usage)=3 "
        "AND responses_with_usage>=0 AND responses_without_usage>=0 AND http_attempts::numeric >= "
        "responses_with_usage::numeric + responses_without_usage::numeric)",
        name="ck_business_child_usage_counters",
    ),
    CheckConstraint(
        # With two or more observed responses, otherwise-valid totals may overflow BIGINT.
        "(coalesce(responses_with_usage,0)<>1 AND num_nonnulls(prompt_tokens,completion_tokens,total_tokens)=0) OR "
        "(responses_with_usage IS NOT NULL AND responses_with_usage>0 AND "
        "num_nonnulls(prompt_tokens,completion_tokens,total_tokens)=3 AND prompt_tokens>=0 "
        "AND completion_tokens>=0 AND total_tokens::numeric=prompt_tokens::numeric+completion_tokens::numeric)",
        name="ck_business_child_usage_tokens",
    ),
    CheckConstraint(
        "num_nonnulls(prompt_cache_hit_tokens,prompt_cache_miss_tokens)=0 OR "
        "(num_nonnulls(prompt_cache_hit_tokens,prompt_cache_miss_tokens,prompt_tokens)=3 "
        "AND prompt_cache_hit_tokens>=0 AND prompt_cache_miss_tokens>=0 AND "
        "prompt_cache_hit_tokens::numeric+prompt_cache_miss_tokens::numeric=prompt_tokens::numeric)",
        name="ck_business_child_usage_cache",
    ),
    Index("ix_business_child_usage_created", "segment_created_at", "segment_id"),
)


@dataclass(frozen=True, slots=True)
class BackfillResult:
    plan_digest: str
    eligible_sections: int
    unclassified_sections: int
    sections_without_attempt_evidence: int
    failed_sections: int
    observed_attempts: int
    provider_usage_responses: int
    unknown_usage_attempts: int
    planned_inserts: int
    inserted: int
    already_projected: int


def _canonical(value: object) -> str:
    def encode(item: Any) -> str:
        if isinstance(item, datetime):
            return item.astimezone(UTC).isoformat()
        if isinstance(item, UUID):
            return str(item)
        raise TypeError("unexpected projection type")

    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=encode)


async def backfill_child_usage(
    connection: AsyncConnection,
    *,
    start: datetime,
    end: datetime,
    expected_database: str,
    max_rows: int = MAX_ROWS,
    apply_digest: str | None = None,
) -> BackfillResult:
    """Run in a dedicated transaction; omitted digest is a SQL read-only dry run."""
    if start.utcoffset() is None or end.utcoffset() is None:
        raise ValueError("timestamps must include an offset")
    start, end = start.astimezone(UTC), end.astimezone(UTC)
    if not timedelta(0) < end - start <= timedelta(days=31):
        raise ValueError("window must be positive and at most 31 days")
    if type(max_rows) is not int or not 1 <= max_rows <= MAX_ROWS:
        raise ValueError("invalid backfill row limit")
    if not expected_database:
        raise ValueError("database confirmation is required")
    if apply_digest is None:
        await connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
    await connection.execute(text("SET LOCAL statement_timeout = '30s'"))
    if await connection.scalar(select(func.current_database())) != expected_database:
        raise ValueError("backfill database identity mismatch")
    if await connection.scalar(text("SELECT current_schemas(false)")) != ["public"]:
        raise ValueError("backfill requires the canonical public schema")
    if apply_digest is not None:
        await connection.execute(text("SELECT pg_advisory_xact_lock(71002309)"))
    source = ChildSegmentGeneration
    provider = source.diagnostics["provider"].as_string()
    statement = (
        select(
            source.id,
            source.created_at,
            source.status,
            provider.label("provider"),
            source.model,
            source.diagnostics["provider_usage"].label("usage"),
        )
        .where(
            source.created_at >= start,
            source.created_at < end,
            source.status.in_(("ready", "failed")),
            (provider.is_(None)) | (provider.not_in(("mock", "disabled"))),
        )
        .order_by(source.created_at, source.id)
        .limit(max_rows + 1)
    )
    source_rows = (await connection.execute(statement)).mappings().all()
    if len(source_rows) > max_rows:
        raise ValueError("backfill row limit exceeded; narrow the time window")
    rows: list[dict[str, Any]] = []
    unclassified = 0
    for source_row in source_rows:
        if source_row.provider not in ("deepseek", "openrouter") or not is_model_ref(source_row.model):
            unclassified += 1
            continue
        counts = validated_usage_aggregate(source_row.usage)
        rows.append(
            {
                "segment_id": source_row.id,
                "segment_created_at": source_row.created_at,
                "section_outcome": source_row.status,
                "provider": source_row.provider,
                "model_ref": source_row.model,
                **{key: counts.get(key) for key in (*COUNTERS, *TOKENS, *CACHE)},
            }
        )
    plan_digest = hashlib.sha256(
        _canonical([VERSION, expected_database, start, end, max_rows, unclassified, rows]).encode()
    ).hexdigest()
    if apply_digest is not None and apply_digest != plan_digest:
        raise ValueError("backfill plan changed or digest is invalid")

    existing = {}
    if rows:
        statement = select(child_usage_projection).where(
            child_usage_projection.c.segment_id.in_([row["segment_id"] for row in rows])
        )
        existing = {row.segment_id: row for row in (await connection.execute(statement)).mappings()}
    missing = []
    for row in rows:
        previous = existing.get(row["segment_id"])
        if previous is None:
            missing.append(row)
        elif previous != row:
            raise ValueError("conflicting Child usage projection; no rows applied")
    if missing and apply_digest is not None:
        await connection.execute(insert(child_usage_projection), missing)
    attempts = sum(row["http_attempts"] or 0 for row in rows)
    known = sum(row["responses_with_usage"] or 0 for row in rows)
    return BackfillResult(
        plan_digest=plan_digest,
        eligible_sections=len(rows),
        unclassified_sections=unclassified,
        sections_without_attempt_evidence=sum(row["http_attempts"] is None for row in rows),
        failed_sections=sum(row["section_outcome"] == "failed" for row in rows),
        observed_attempts=attempts,
        provider_usage_responses=known,
        unknown_usage_attempts=attempts - known,
        planned_inserts=len(missing),
        inserted=len(missing) if apply_digest is not None else 0,
        already_projected=len(existing),
    )


async def _run(args: argparse.Namespace) -> None:
    dsn = os.environ.get("BUSINESS_USAGE_BACKFILL_DATABASE_URL")
    if not dsn:
        raise ValueError("explicit backfill database URL required")
    engine = create_async_engine(dsn, hide_parameters=True)
    try:
        async with engine.begin() as connection:
            result = await backfill_child_usage(
                connection,
                start=args.start,
                end=args.end,
                max_rows=args.max_rows,
                expected_database=args.expect_database,
                apply_digest=args.apply_digest,
            )
    finally:
        await engine.dispose()
    print(json.dumps(asdict(result), sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, type=datetime.fromisoformat)
    parser.add_argument("--end", required=True, type=datetime.fromisoformat)
    parser.add_argument("--expect-database", required=True)
    parser.add_argument("--max-rows", type=int, default=MAX_ROWS)
    parser.add_argument("--apply-digest", help="Apply only this prior dry-run digest; otherwise read-only")
    args = parser.parse_args()
    try:
        asyncio.run(_run(args))
    except Exception:
        # Driver exceptions can include SQL identifiers, connection details and source data.
        parser.exit(1, "Child usage backfill refused or failed; no output published.\n")


if __name__ == "__main__":
    main()
