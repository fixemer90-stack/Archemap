"""Offline numeric evidence: synthetic caller rates, never provider tariffs."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from app.modules.analytics.costs import Attempt, PinnedRate, TokenUsage, estimate_attempt


def rate(**changes: Any) -> PinnedRate:
    values: dict[str, Any] = {
        "provider": "synthetic",
        "model": "test-model",
        "version": "v1",
        "currency": "USD",
        "pinned_at": datetime(2026, 11, 21, tzinfo=UTC),
        "input_per_million": Decimal("0.25"),
        "output_per_million": Decimal("2.5"),
        "cache_pricing": "uniform",
    }
    return PinnedRate(**(values | changes))


def usage(**changes: Any) -> TokenUsage:
    values: dict[str, Any] = {"input_tokens": 12, "output_tokens": 3, "total_tokens": 15, "source": "provider"}
    return TokenUsage(**(values | changes))


@pytest.mark.parametrize("field", ["input_tokens", "output_tokens", "total_tokens", "cache_hit_tokens"])
@pytest.mark.parametrize("value", [-1, True, 1.0, "1", Decimal("1")])
def test_token_counts_are_strict_nonnegative_integers(field: str, value: Any) -> None:
    with pytest.raises(ValueError):
        usage(**{field: value})


@pytest.mark.parametrize(
    "changes",
    [
        {"total_tokens": 16},
        {"cache_hit_tokens": 13},
        {"source": "unknown"},
        {"source": True},
    ],
)
def test_usage_rejects_inconsistent_or_unclassified_evidence(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        usage(**changes)


@pytest.mark.parametrize("field", ["input_per_million", "output_per_million", "cached_input_per_million"])
@pytest.mark.parametrize(
    "value", [Decimal("-1"), Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), 0.1, 1, "1", True]
)
def test_rates_require_finite_nonnegative_decimal(field: str, value: Any) -> None:
    with pytest.raises(ValueError):
        rate(**{field: value})


@pytest.mark.parametrize(
    "changes",
    [
        {"currency": "usd"},
        {"currency": "US"},
        {"currency": "US1"},
        {"currency": " USD"},
        {"currency": True},
        {"version": ""},
        {"provider": ""},
        {"model": ""},
        {"pinned_at": datetime(2026, 11, 21)},
        {"pinned_at": "2026-11-21T00:00:00Z"},
        {"cache_pricing": "guess"},
        {"cached_input_per_million": Decimal("0")},
    ],
)
def test_rate_requires_explicit_valid_pin_and_currency(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        rate(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"attempt_id": "00000000-0000-0000-0000-000000000001"},
        {"attempt_id": True},
        {"outcome": "retry"},
        {"outcome": True},
        {"usage": {}},
        {"rate": {}},
    ],
)
def test_attempt_rejects_coercion_or_unknown_shapes(changes: dict[str, Any]) -> None:
    values: dict[str, Any] = {"attempt_id": UUID(int=1), "outcome": "unknown"}
    with pytest.raises(ValueError):
        Attempt(**(values | changes))


def test_evidence_is_immutable() -> None:
    evidence = usage()
    attribute = "input_tokens"
    with pytest.raises(FrozenInstanceError):
        setattr(evidence, attribute, 0)


@pytest.mark.parametrize("source", ["token_estimate", "character_estimate"])
def test_estimate_provenance_is_not_promoted_to_provider_observation(source: Any) -> None:
    attempt = Attempt(UUID(int=1), "unknown", usage(source=source), rate())
    result = estimate_attempt(attempt)
    assert result.attempt.usage is not None
    assert result.attempt.usage.source == source
    assert result.attempt.usage.confidence == "estimated"
    assert result.cost_confidence == "estimated"
    assert result.estimated_cost == Decimal("0.0000105")


@pytest.mark.parametrize(
    "facts, reason",
    [
        ({}, "missing_usage"),
        ({"rate": rate()}, "missing_usage"),
        ({"usage": usage()}, "missing_rate"),
        ({"usage": usage(), "rate": rate(cache_pricing="split")}, "missing_cache_usage"),
        ({"usage": usage(cache_hit_tokens=5), "rate": rate(cache_pricing="split")}, "missing_cache_rate"),
    ],
)
def test_absent_evidence_is_unknown_never_zero(facts: dict[str, Any], reason: str) -> None:
    result = estimate_attempt(Attempt(UUID(int=1), "unknown", **facts))
    assert result.estimated_cost is None
    assert result.cost_confidence == "unknown"
    assert result.unknown_reason == reason


@pytest.mark.parametrize(
    "hits, cached_rate, expected",
    [
        (5, Decimal("0.1"), Decimal("0.00000975")),
        (12, Decimal("0"), Decimal("0.0000075")),
        (0, None, Decimal("0.0000105")),
    ],
)
def test_split_cache_pricing_covers_only_proven_token_categories(
    hits: int,
    cached_rate: Decimal | None,
    expected: Decimal,
) -> None:
    attempt = Attempt(
        UUID(int=1),
        "failed",
        usage(cache_hit_tokens=hits),
        rate(cache_pricing="split", cached_input_per_million=cached_rate),
    )
    assert estimate_attempt(attempt).estimated_cost == expected


def test_validated_zero_usage_and_explicit_zero_rates_are_known_estimates() -> None:
    empty = usage(input_tokens=0, output_tokens=0, total_tokens=0)
    assert estimate_attempt(Attempt(UUID(int=1), "succeeded", empty, rate())).estimated_cost == Decimal("0")
    free = rate(input_per_million=Decimal("0"), output_per_million=Decimal("0"))
    assert estimate_attempt(Attempt(UUID(int=2), "succeeded", usage(), free)).estimated_cost == Decimal("0")


def test_summary_counts_failed_retries_and_unknown_outcomes_without_losing_coverage() -> None:
    from app.modules.analytics.costs import summarize_costs

    attempts = [
        Attempt(UUID(int=1), "failed", usage(), rate()),
        Attempt(UUID(int=2), "succeeded", usage(source="token_estimate"), rate()),
        Attempt(UUID(int=3), "unknown", usage(source="character_estimate"), rate()),
        Attempt(UUID(int=4), "unknown", rate=rate()),
        Attempt(UUID(int=5), "failed", usage()),
    ]
    summary = summarize_costs(iter(attempts), delivered_reports=2)
    assert summary.total_attempts == 5
    assert summary.observed_usage_attempts == 2
    assert summary.estimated_usage_attempts == 2
    assert summary.missing_usage_attempts == 1
    assert summary.succeeded_attempts == 1
    assert summary.failed_attempts == 2
    assert summary.unknown_outcome_attempts == 2
    assert summary.unknown_cost_attempts == 2
    assert summary.missing_rate_attempts == 1
    assert summary.usage_coverage.known == 4
    assert summary.usage_coverage.total == 5
    assert summary.usage_coverage.ratio == Decimal("0.8")
    assert summary.observed_usage_coverage.ratio == Decimal("0.4")
    assert summary.cost_coverage.ratio == Decimal("0.6")
    assert len(summary.attempt_costs) == 5
    (usd,) = summary.currencies
    assert usd.currency == "USD"
    assert usd.known_estimated_subtotal == Decimal("0.0000315")
    assert usd.complete_estimated_total is None
    assert usd.per_delivered_report is None


def test_summary_never_combines_currencies_and_deduplicates_matching_attempts() -> None:
    from app.modules.analytics.costs import summarize_costs

    first = Attempt(UUID(int=1), "failed", usage(), rate())
    second = Attempt(UUID(int=2), "succeeded", usage(), rate(currency="RUB"))
    summary = summarize_costs([first, second, replace(first)], delivered_reports=2)
    assert summary.total_attempts == 2
    assert summary.cost_coverage.ratio == Decimal("1")
    assert [group.currency for group in summary.currencies] == ["RUB", "USD"]
    for group in summary.currencies:
        assert group.known_estimated_subtotal == Decimal("0.0000105")
        assert group.complete_estimated_total == Decimal("0.0000105")
        assert group.per_delivered_report == Decimal("0.00000525")


@pytest.mark.parametrize(
    "changes",
    [
        {"outcome": "unknown"},
        {"usage": None},
        {"usage": usage(source="token_estimate")},
        {"rate": None},
        {"rate": rate(version="v2")},
        {"rate": rate(currency="RUB")},
        {"usage": usage(cache_hit_tokens=0)},
    ],
)
def test_conflicting_attempt_identity_is_rejected(changes: dict[str, Any]) -> None:
    from app.modules.analytics.costs import summarize_costs

    first = Attempt(UUID(int=1), "succeeded", usage(), rate())
    with pytest.raises(ValueError, match="conflicting attempt"):
        summarize_costs([first, replace(first, **changes)], delivered_reports=1)


@pytest.mark.parametrize("delivered", [-1, True, 1.0, "1"])
def test_delivery_denominator_is_validated(delivered: Any) -> None:
    from app.modules.analytics.costs import summarize_costs

    with pytest.raises(ValueError):
        summarize_costs([], delivered_reports=delivered)


def test_empty_evidence_and_zero_delivery_are_undefined_not_free() -> None:
    from app.modules.analytics.costs import summarize_costs

    empty = summarize_costs([], delivered_reports=0)
    assert empty.usage_coverage.ratio is None
    assert empty.cost_coverage.ratio is None
    assert empty.currencies == ()
    known = summarize_costs([Attempt(UUID(int=1), "failed", usage(), rate())], delivered_reports=0)
    assert known.currencies[0].per_delivered_report is None
    unknown = summarize_costs([Attempt(UUID(int=1), "unknown", rate=rate())], delivered_reports=1)
    assert unknown.currencies[0].known_estimated_subtotal is None
    assert unknown.currencies[0].complete_estimated_total is None
    assert unknown.cost_coverage.ratio == Decimal("0")


def test_decimal_context_cannot_round_overflow_or_trap_exact_costs() -> None:
    from decimal import Inexact, localcontext

    from app.modules.analytics.costs import summarize_costs

    evidence = Attempt(
        UUID(int=1),
        "failed",
        usage(input_tokens=1_000_000, output_tokens=0, total_tokens=1_000_000),
        rate(input_per_million=Decimal("123456789.123456789123456789")),
    )
    with localcontext() as context:
        context.prec = 3
        context.Emax = 2
        context.Emin = -2
        context.traps[Inexact] = True
        summary = summarize_costs([evidence, replace(evidence, attempt_id=UUID(int=2))], delivered_reports=3)
        (group,) = summary.currencies
        assert group.complete_estimated_total == Decimal("246913578.246913578246913578")
        assert group.per_delivered_report == Decimal("82304526.082304526082304526")
        assert context.prec == 3
    with localcontext() as context:
        context.traps[Inexact] = True
        recurring = summarize_costs([Attempt(UUID(int=1), "failed", usage(), rate())], delivered_reports=9)
        assert recurring.currencies[0].per_delivered_report == Decimal(
            "0.0000011666666666666666666666666666666666666666666666667"
        )


@pytest.mark.parametrize("known,total", [(-1, 1), (2, 1), (True, 1), (1, 1.0)])
def test_coverage_counts_cannot_be_invalid(known: Any, total: Any) -> None:
    from app.modules.analytics.costs import Coverage

    with pytest.raises(ValueError):
        Coverage(known, total)


def test_unpinned_attempt_prevents_claiming_complete_totals_in_any_currency() -> None:
    from app.modules.analytics.costs import summarize_costs

    summary = summarize_costs(
        [
            Attempt(UUID(int=1), "succeeded", usage(), rate()),
            Attempt(UUID(int=2), "unknown"),
        ],
        delivered_reports=1,
    )
    assert summary.currencies[0].known_estimated_subtotal == Decimal("0.0000105")
    assert summary.currencies[0].complete_estimated_total is None
    assert summary.currencies[0].per_delivered_report is None
    assert summary.missing_usage_attempts == 1
    assert summary.missing_rate_attempts == 1


def test_observed_tokens_produce_only_a_rate_based_estimate() -> None:
    from app.modules.analytics.costs import Attempt, PinnedRate, TokenUsage, estimate_attempt

    rate = PinnedRate(
        provider="synthetic",
        model="test-model",
        version="v1",
        currency="USD",
        pinned_at=datetime(2026, 11, 21, tzinfo=UTC),
        input_per_million=Decimal("0.123456789123456789123456789"),
        output_per_million=Decimal("2.75"),
        cache_pricing="uniform",
    )
    attempt = Attempt(
        attempt_id=UUID(int=1),
        outcome="failed",
        usage=TokenUsage(input_tokens=1_000_000, output_tokens=2, total_tokens=1_000_002, source="provider"),
        rate=rate,
    )
    result = estimate_attempt(attempt)
    assert result.estimated_cost == Decimal("0.123462289123456789123456789")
    assert result.cost_confidence == "estimated"
    assert result.attempt.usage is not None
    assert result.attempt.usage.confidence == "observed"
    assert result.attempt.rate is rate
    assert result.unknown_reason is None


@pytest.mark.parametrize("count", [2**63, 10**4300], ids=["above-int64", "huge-integer"])
def test_token_and_delivery_counts_fail_before_arithmetic(count: int) -> None:
    from app.modules.analytics.costs import Coverage, summarize_costs

    with pytest.raises(ValueError, match=r"64-bit"):
        TokenUsage(count, 0, count, "provider")
    with pytest.raises(ValueError, match=r"64-bit"):
        Coverage(0, count)
    with pytest.raises(ValueError, match=r"64-bit"):
        summarize_costs([], delivered_reports=count)


@pytest.mark.parametrize("value", ["1e39", "1e-39", "0e-39", "9" * 39, "1e999999999999999999", "1e-999999999999999999"])
def test_rate_envelope_rejects_excessive_coefficient_or_scale(value: str) -> None:
    with pytest.raises(ValueError, match=r"38"):
        rate(input_per_million=Decimal(value))


def test_cost_at_both_numeric_boundaries_remains_exact() -> None:
    from app.modules.analytics.costs import summarize_costs

    limit = 2**63 - 1
    attempt = Attempt(
        UUID(int=1),
        "failed",
        TokenUsage(limit - 1, 1, limit, "provider"),
        rate(input_per_million=Decimal("9" * 38 + "e38"), output_per_million=Decimal("1e-38")),
    )
    expected = Decimal(str((limit - 1) * (10**38 - 1)) + "0" * 32 + "." + "0" * 43 + "1")
    assert estimate_attempt(attempt).estimated_cost == expected
    summary = summarize_costs([attempt], delivered_reports=1)
    assert summary.currencies[0].complete_estimated_total == expected
    assert summary.currencies[0].per_delivered_report == expected
