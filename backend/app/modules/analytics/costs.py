"""Pure attempt-level evidence; no persistence, tariff lookup, FX or provider I/O.

Callers supply one immutable Attempt per actual HTTP attempt (including retries).
PinnedRate is caller evidence, never a tariff discovered or inferred here.
All computed money is rate-based *estimated* cost, never an observed invoice.
Counts fit a nonnegative signed 64-bit integer. Rate evidence has at most 38
coefficient digits and a stored Decimal exponent from -38 through 38. These
limits are input validation, not rounding rules or a storage contract.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import MAX_EMAX, MIN_EMIN, ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Literal
from uuid import UUID

UsageSource = Literal["provider", "token_estimate", "character_estimate"]
Confidence = Literal["observed", "estimated", "unknown"]
CostConfidence = Literal["estimated", "unknown"]
UnknownReason = Literal["missing_usage", "missing_rate", "missing_cache_usage", "missing_cache_rate"]
Outcome = Literal["succeeded", "failed", "unknown"]

_MAX_COUNT = (1 << 63) - 1
_RATE_LIMIT = 38


def _count(value: object) -> None:
    if type(value) is not int or not 0 <= value <= _MAX_COUNT:
        raise ValueError("counts must be nonnegative strict integers in the signed 64-bit range")


def _rate(value: object) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError("rates must be finite nonnegative Decimal values")
    parts = value.as_tuple()
    assert isinstance(parts.exponent, int)
    if len(parts.digits) > _RATE_LIMIT or abs(parts.exponent) > _RATE_LIMIT:
        raise ValueError("rates must have at most 38 coefficient digits and an exponent from -38 to 38")


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Total input includes cache hits; estimates must declare their source."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    source: UsageSource
    cache_hit_tokens: int | None = None

    def __post_init__(self) -> None:
        for value in (self.input_tokens, self.output_tokens, self.total_tokens):
            _count(value)
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens must equal input_tokens + output_tokens")
        if self.cache_hit_tokens is not None:
            _count(self.cache_hit_tokens)
            if self.cache_hit_tokens > self.input_tokens:
                raise ValueError("cache hits cannot exceed input tokens")
        if self.source not in ("provider", "token_estimate", "character_estimate"):
            raise ValueError("usage source must be explicit")

    @property
    def confidence(self) -> Confidence:
        return "observed" if self.source == "provider" else "estimated"


@dataclass(frozen=True, slots=True)
class PinnedRate:
    """Amounts per million tokens, with explicit model/version/currency/time pin.

    uniform explicitly asserts all input tokens have the same tariff; split
    requires cache-hit evidence and (for positive hits) a cache rate.
    """

    provider: str
    model: str
    version: str
    currency: str
    pinned_at: datetime
    input_per_million: Decimal
    output_per_million: Decimal
    cache_pricing: Literal["uniform", "split"]
    cached_input_per_million: Decimal | None = None

    def __post_init__(self) -> None:
        for name in ("provider", "model", "version"):
            value = getattr(self, name)
            if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}", value) is None:
                raise ValueError(f"{name} must be a bounded identifier")
        if not isinstance(self.currency, str) or re.fullmatch(r"[A-Z]{3}", self.currency) is None:
            raise ValueError("currency must be an uppercase three-letter code; no FX is inferred")
        if not isinstance(self.pinned_at, datetime) or self.pinned_at.utcoffset() is None:
            raise ValueError("pinned_at must be an aware datetime")
        _rate(self.input_per_million)
        _rate(self.output_per_million)
        if self.cached_input_per_million is not None:
            _rate(self.cached_input_per_million)
        if self.cache_pricing not in ("uniform", "split"):
            raise ValueError("cache pricing must explicitly be uniform or split")
        if self.cache_pricing == "uniform" and self.cached_input_per_million is not None:
            raise ValueError("uniform pricing cannot also supply a separate cache rate")


@dataclass(frozen=True, slots=True)
class Attempt:
    """Identity is an actual transport attempt, not a report or retry group."""

    attempt_id: UUID
    outcome: Outcome
    usage: TokenUsage | None = None
    rate: PinnedRate | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.attempt_id, UUID):
            raise ValueError("attempt_id must be a UUID, not coerced text")
        if self.outcome not in ("succeeded", "failed", "unknown"):
            raise ValueError("outcome must be explicit")
        if self.usage is not None and not isinstance(self.usage, TokenUsage):
            raise ValueError("usage must be TokenUsage or None")
        if self.rate is not None and not isinstance(self.rate, PinnedRate):
            raise ValueError("rate must be PinnedRate or None")


@dataclass(frozen=True, slots=True)
class AttemptCost:
    """Preserves the input facts alongside the derived estimate."""

    attempt: Attempt
    estimated_cost: Decimal | None
    cost_confidence: CostConfidence
    unknown_reason: UnknownReason | None = None


def _exact_sum(values: list[Decimal]) -> Decimal:
    # Sufficient precision for every coefficient plus carries, independent of
    # the caller's decimal context. No currency/minor-unit rounding is applied.
    # Validated rates share a fixed 76-step exponent span before scaling.
    values = [value for value in values if not value.is_zero()]
    if not values:
        return Decimal(0)
    exponent = min(int(value.as_tuple().exponent) for value in values)
    precision = max(len(value.as_tuple().digits) + int(value.as_tuple().exponent) - exponent for value in values)
    with localcontext(Context(prec=max(precision + len(str(len(values))) + 1, 28), Emin=MIN_EMIN, Emax=MAX_EMAX)):
        return sum(values, Decimal(0))


def _token_cost(tokens: int, rate: Decimal) -> Decimal:
    if not tokens or rate.is_zero():
        return Decimal(0)
    parts = rate.as_tuple()
    assert isinstance(parts.exponent, int)
    per_token = Decimal((parts.sign, parts.digits, parts.exponent - 6))
    with localcontext(Context(prec=len(str(tokens)) + len(parts.digits), Emin=MIN_EMIN, Emax=MAX_EMAX)):
        return per_token * tokens


def estimate_attempt(attempt: Attempt) -> AttemptCost:
    """Return a rate-based estimate without relabeling usage as estimated."""
    usage, rate = attempt.usage, attempt.rate
    reason: UnknownReason | None = None
    if usage is None:
        reason = "missing_usage"
    elif rate is None:
        reason = "missing_rate"
    elif rate.cache_pricing == "split":
        if usage.cache_hit_tokens is None:
            reason = "missing_cache_usage"
        elif usage.cache_hit_tokens > 0 and rate.cached_input_per_million is None:
            reason = "missing_cache_rate"
    if reason is not None:
        return AttemptCost(attempt, None, "unknown", reason)
    assert usage is not None and rate is not None
    input_tokens = usage.input_tokens
    components = [_token_cost(usage.output_tokens, rate.output_per_million)]
    if rate.cache_pricing == "split":
        assert usage.cache_hit_tokens is not None
        input_tokens -= usage.cache_hit_tokens
        if usage.cache_hit_tokens > 0:
            assert rate.cached_input_per_million is not None
            components.append(_token_cost(usage.cache_hit_tokens, rate.cached_input_per_million))
    components.append(_token_cost(input_tokens, rate.input_per_million))
    return AttemptCost(attempt, _exact_sum(components), "estimated")


def _ratio(numerator: Decimal, denominator: int) -> Decimal | None:
    if denominator == 0:
        return None
    with localcontext(
        Context(
            prec=max(50, len(numerator.as_tuple().digits) + len(str(denominator))),
            rounding=ROUND_HALF_EVEN,
            Emin=MIN_EMIN,
            Emax=MAX_EMAX,
        )
    ):
        return numerator / denominator


@dataclass(frozen=True, slots=True)
class Coverage:
    """Exact counts; ratio is a display value rounded to >=50 significant digits."""

    known: int
    total: int

    def __post_init__(self) -> None:
        _count(self.known)
        _count(self.total)
        if self.known > self.total:
            raise ValueError("known count cannot exceed total")

    @property
    def ratio(self) -> Decimal | None:
        return _ratio(Decimal(self.known), self.total)


@dataclass(frozen=True, slots=True)
class CurrencyCost:
    """Never add these groups without an external dated FX contract.

    The known subtotal is explicitly partial, not total spend. Complete totals
    are unavailable if this currency has unknown costs OR any attempt lacks a
    currency pin. Per-report is the same complete total / caller delivery count;
    recurring division is rounded HALF_EVEN at >=50 significant digits.
    """

    currency: str
    known_estimated_subtotal: Decimal | None
    complete_estimated_total: Decimal | None
    per_delivered_report: Decimal | None
    cost_coverage: Coverage


@dataclass(frozen=True, slots=True)
class CostSummary:
    """Coverage is over deduplicated attempts, not tokens or delivered reports.

    Unknown outcomes are independent of numeric usage/cost coverage: a timeout
    does not prove no charge, and an observed response does not prove delivery.
    No all-currency monetary total is exposed. Missing-rate counts include
    attempts missing both usage and rate, regardless of their primary reason.
    """

    attempt_costs: tuple[AttemptCost, ...]
    currencies: tuple[CurrencyCost, ...]
    delivered_reports: int
    total_attempts: int
    observed_usage_attempts: int
    estimated_usage_attempts: int
    missing_usage_attempts: int
    succeeded_attempts: int
    failed_attempts: int
    unknown_outcome_attempts: int
    unknown_cost_attempts: int
    missing_rate_attempts: int
    usage_coverage: Coverage
    observed_usage_coverage: Coverage
    cost_coverage: Coverage


def summarize_costs(attempts: Iterable[Attempt], *, delivered_reports: int) -> CostSummary:
    """Deduplicate identical facts; reject conflicting UUIDs before returning.

    Caller owns report/window selection and the delivery denominator. Supplying
    no attempts means unavailable evidence, not proof of zero/free generation.
    Rates and usage provenance survive in attempt_costs for read-model adapters.
    """
    _count(delivered_reports)
    unique: dict[UUID, Attempt] = {}
    for attempt in attempts:
        previous = unique.get(attempt.attempt_id)
        if previous is not None and previous != attempt:
            raise ValueError(f"conflicting attempt facts: {attempt.attempt_id}")
        unique[attempt.attempt_id] = attempt
    results = tuple(estimate_attempt(attempt) for attempt in unique.values())
    total = len(results)
    observed = sum(item.attempt.usage is not None and item.attempt.usage.source == "provider" for item in results)
    missing = sum(item.attempt.usage is None for item in results)
    priced = sum(item.estimated_cost is not None for item in results)
    missing_rate = sum(item.attempt.rate is None for item in results)
    by_currency: dict[str, list[AttemptCost]] = {}
    for item in results:
        if item.attempt.rate is not None:
            by_currency.setdefault(item.attempt.rate.currency, []).append(item)
    groups: list[CurrencyCost] = []
    for currency, items in sorted(by_currency.items()):
        amounts = [item.estimated_cost for item in items if item.estimated_cost is not None]
        subtotal = _exact_sum(amounts) if amounts else None
        complete = subtotal if len(amounts) == len(items) and missing_rate == 0 else None
        per_report = _ratio(complete, delivered_reports) if complete is not None else None
        groups.append(CurrencyCost(currency, subtotal, complete, per_report, Coverage(len(amounts), len(items))))
    return CostSummary(
        attempt_costs=results,
        currencies=tuple(groups),
        delivered_reports=delivered_reports,
        total_attempts=total,
        observed_usage_attempts=observed,
        estimated_usage_attempts=total - observed - missing,
        missing_usage_attempts=missing,
        succeeded_attempts=sum(item.attempt.outcome == "succeeded" for item in results),
        failed_attempts=sum(item.attempt.outcome == "failed" for item in results),
        unknown_outcome_attempts=sum(item.attempt.outcome == "unknown" for item in results),
        unknown_cost_attempts=total - priced,
        missing_rate_attempts=missing_rate,
        usage_coverage=Coverage(total - missing, total),
        observed_usage_coverage=Coverage(observed, total),
        cost_coverage=Coverage(priced, total),
    )
