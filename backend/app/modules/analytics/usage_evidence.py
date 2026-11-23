"""Internal, privacy-bounded provider-attempt evidence. No report or customer identities."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, cast

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Index, String, Table, select
from sqlalchemy.dialects.postgresql import UUID, insert
from sqlalchemy.ext.asyncio import AsyncConnection

from app.infrastructure.database import Base
from app.modules.analytics.costs import (
    Attempt,
    CostSummary,
    Outcome,
    PinnedRate,
    TokenUsage,
    UsageSource,
    summarize_costs,
)

Provider = Literal["deepseek", "openrouter"]
_MODEL_REF = re.compile(r"model-sha256:[0-9a-f]{64}")


def model_ref(model: str) -> str:
    # Hash trusted requested configuration only, never an upstream response label.
    return "model-sha256:" + hashlib.sha256(model.encode("utf-8", errors="surrogatepass")).hexdigest()


def is_model_ref(value: object) -> bool:
    return isinstance(value, str) and _MODEL_REF.fullmatch(value) is not None


@dataclass(frozen=True, slots=True)
class TransportEvidence:
    occurred_at: datetime
    provider: Provider
    model: str
    attempt: Attempt

    def __post_init__(self) -> None:
        if self.occurred_at.utcoffset() is None or self.provider not in ("deepseek", "openrouter"):
            raise ValueError("invalid transport scope")
        if not is_model_ref(self.model):
            raise ValueError("model must be an opaque configuration reference")
        rate = self.attempt.rate
        if rate is not None and (rate.provider != self.provider or rate.model != self.model):
            raise ValueError("rate does not match attempt provider/model scope")


transport_usage = Table(
    "business_transport_usage",
    Base.metadata,
    Column("attempt_id", UUID(as_uuid=True), primary_key=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("provider", String(10), nullable=False),
    Column("model_ref", String(77), nullable=False),
    Column("outcome", String(9), nullable=False),
    Column("usage_source", String(18)),
    Column("input_tokens", BigInteger),
    Column("output_tokens", BigInteger),
    Column("total_tokens", BigInteger),
    Column("cache_hit_tokens", BigInteger),
    Column("rate_version", String(128)),
    Column("rate_pinned_at", DateTime(timezone=True)),
    Column("currency", String(3)),
    # Decimal text is machine-generated, not rounded to a fixed database scale.
    Column("input_rate", String(48)),
    Column("output_rate", String(48)),
    Column("cache_rate", String(48)),
    Column("cache_pricing", String(7)),
    CheckConstraint("provider IN ('deepseek', 'openrouter')", name="ck_business_transport_provider"),
    CheckConstraint("model_ref ~ '^model-sha256:[0-9a-f]{64}$'", name="ck_business_transport_model"),
    CheckConstraint("outcome IN ('succeeded', 'failed', 'unknown')", name="ck_business_transport_outcome"),
    CheckConstraint(
        "(usage_source IS NULL AND num_nonnulls(input_tokens,output_tokens,total_tokens,cache_hit_tokens)=0) OR "
        "(usage_source IS NOT NULL AND usage_source IN ('provider','token_estimate','character_estimate') AND "
        "num_nonnulls(input_tokens,output_tokens,total_tokens)=3 AND input_tokens>=0 AND output_tokens>=0 AND "
        "total_tokens::numeric=input_tokens::numeric+output_tokens::numeric AND "
        "(cache_hit_tokens IS NULL OR cache_hit_tokens BETWEEN 0 AND input_tokens))",
        name="ck_business_transport_tokens",
    ),
    CheckConstraint(
        "num_nonnulls(rate_version,rate_pinned_at,currency,input_rate,output_rate,cache_rate,cache_pricing)=0 OR "
        "(num_nonnulls(rate_version,rate_pinned_at,currency,input_rate,output_rate,cache_pricing)=6 AND "
        "currency ~ '^[A-Z]{3}$' AND (cache_pricing='split' OR (cache_pricing='uniform' AND cache_rate IS NULL)))",
        name="ck_business_transport_rate",
    ),
    Index("ix_business_transport_occurred", "occurred_at", "attempt_id"),
)


def _values(item: TransportEvidence) -> dict[str, object]:
    usage, rate = item.attempt.usage, item.attempt.rate
    return {
        "attempt_id": item.attempt.attempt_id,
        "occurred_at": item.occurred_at,
        "provider": item.provider,
        "model_ref": item.model,
        "outcome": item.attempt.outcome,
        "usage_source": usage.source if usage else None,
        "input_tokens": usage.input_tokens if usage else None,
        "output_tokens": usage.output_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
        "cache_hit_tokens": usage.cache_hit_tokens if usage else None,
        "rate_version": rate.version if rate else None,
        "rate_pinned_at": rate.pinned_at if rate else None,
        "currency": rate.currency if rate else None,
        "input_rate": str(rate.input_per_million) if rate else None,
        "output_rate": str(rate.output_per_million) if rate else None,
        "cache_rate": (
            str(rate.cached_input_per_million) if rate and rate.cached_input_per_million is not None else None
        ),
        "cache_pricing": rate.cache_pricing if rate else None,
    }


async def record_transport_evidence(connection: AsyncConnection, item: TransportEvidence) -> None:
    """Insert an immutable fact; a replay must match all original stored evidence."""
    values = _values(item)
    result = await connection.execute(
        insert(transport_usage).values(values).on_conflict_do_nothing().returning(transport_usage.c.attempt_id)
    )
    if result.scalar_one_or_none() is not None:
        return
    existing = (
        (
            await connection.execute(
                select(transport_usage).where(transport_usage.c.attempt_id == item.attempt.attempt_id)
            )
        )
        .mappings()
        .one()
    )
    if existing != values:
        raise ValueError("conflicting provider attempt evidence")


async def read_transport_costs(
    connection: AsyncConnection, *, start: datetime, end: datetime, delivered_reports: int
) -> CostSummary:
    """Aggregate exact attempt evidence in [start,end); never merge legacy section aggregates here."""
    if start.utcoffset() is None or end.utcoffset() is None or not start < end:
        raise ValueError("expected an aware, increasing cost window")
    statement = (
        select(transport_usage)
        .where(transport_usage.c.occurred_at >= start, transport_usage.c.occurred_at < end)
        .order_by(transport_usage.c.occurred_at, transport_usage.c.attempt_id)
    )
    attempts = []
    for row in (await connection.execute(statement)).mappings():
        usage = None
        if row.usage_source is not None:
            usage = TokenUsage(
                row.input_tokens,
                row.output_tokens,
                row.total_tokens,
                cast(UsageSource, row.usage_source),
                row.cache_hit_tokens,
            )
        rate = None
        if row.rate_version is not None:
            rate = PinnedRate(
                row.provider,
                row.model_ref,
                row.rate_version,
                row.currency,
                row.rate_pinned_at,
                Decimal(row.input_rate),
                Decimal(row.output_rate),
                row.cache_pricing,
                Decimal(row.cache_rate) if row.cache_rate is not None else None,
            )
        attempts.append(Attempt(row.attempt_id, cast(Outcome, row.outcome), usage, rate))
    return summarize_costs(attempts, delivered_reports=delivered_reports)
