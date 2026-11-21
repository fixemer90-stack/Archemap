"""D7 uses per-account elapsed time, never the registration-day bucket."""

from __future__ import annotations

import importlib.util
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from app.modules.analytics.cohorts import BasicReady, Registration, summarize_d7


def test_first_ready_artifact_controls_d7_even_with_a_later_in_window_artifact() -> None:
    signup = datetime(2026, 11, 1, 12, tzinfo=UTC)
    user_id = UUID(int=1)
    result = summarize_d7(
        [Registration(user_id, signup)],
        [
            BasicReady(UUID(int=2), user_id, signup + timedelta(hours=1)),
            BasicReady(UUID(int=3), user_id, signup - timedelta(seconds=1)),
        ],
        cohort_from=date(2026, 11, 1),
        cohort_to=date(2026, 11, 2),
        as_of=signup + timedelta(days=7),
    )
    assert result.mature == 1
    assert result.activated == 0


def test_late_day_signup_can_activate_after_registration_bucket_closes() -> None:
    assert importlib.util.find_spec("app.modules.analytics.cohorts") is not None
    from app.modules.analytics.cohorts import BasicReady, Registration, summarize_d7

    signup = datetime(2026, 11, 1, 23, 59, tzinfo=ZoneInfo("Europe/Moscow"))
    user_id = UUID(int=1)
    result = summarize_d7(
        [Registration(user_id, signup)],
        [BasicReady(UUID(int=2), user_id, signup + timedelta(hours=2))],
        cohort_from=date(2026, 11, 1),
        cohort_to=date(2026, 11, 2),
        as_of=signup.astimezone(UTC) + timedelta(days=7),
    )
    assert result.registrations == result.mature == result.activated == 1
    assert result.immature == 0
    assert result.rate == Decimal(1)
    assert result.status == "available"


def test_registration_replay_does_not_duplicate_cohort_denominator() -> None:
    signup = datetime(2026, 11, 1, tzinfo=UTC)
    account = Registration(UUID(int=1), signup)
    result = summarize_d7(
        [account, account],
        [BasicReady(UUID(int=2), account.user_id, signup)],
        cohort_from=date(2026, 11, 1),
        cohort_to=date(2026, 11, 2),
        as_of=signup + timedelta(days=8),
    )
    assert result.registrations == result.mature == result.activated == 1


def test_conflicting_registration_identity_fails_closed() -> None:
    signup = datetime(2026, 11, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match=r"[Cc]onflicting"):
        summarize_d7(
            [Registration(UUID(int=1), signup), Registration(UUID(int=1), signup + timedelta(hours=1))],
            [],
            cohort_from=date(2026, 11, 1),
            cohort_to=date(2026, 11, 2),
            as_of=signup + timedelta(days=8),
        )


def test_conflicting_ready_artifact_identity_fails_closed() -> None:
    signup = datetime(2026, 11, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match=r"[Cc]onflicting"):
        summarize_d7(
            [Registration(UUID(int=1), signup)],
            [BasicReady(UUID(int=2), UUID(int=1), signup), BasicReady(UUID(int=2), UUID(int=3), signup)],
            cohort_from=date(2026, 11, 1),
            cohort_to=date(2026, 11, 2),
            as_of=signup + timedelta(days=8),
        )


@pytest.mark.parametrize("value", [datetime(2026, 11, 1), "2026-11-01T00:00:00Z", None])
def test_evidence_requires_aware_time(value: Any) -> None:
    with pytest.raises(ValueError):
        Registration(UUID(int=1), value)
    with pytest.raises(ValueError):
        BasicReady(UUID(int=2), UUID(int=1), value)


@pytest.mark.parametrize("value", ["00000000-0000-0000-0000-000000000001", True, None])
def test_evidence_requires_uuid_identity(value: Any) -> None:
    with pytest.raises(ValueError):
        Registration(value, datetime(2026, 11, 1, tzinfo=UTC))
    with pytest.raises(ValueError):
        BasicReady(value, UUID(int=1), datetime(2026, 11, 1, tzinfo=UTC))
    with pytest.raises(ValueError):
        BasicReady(UUID(int=2), value, datetime(2026, 11, 1, tzinfo=UTC))


@pytest.mark.parametrize(
    "changes",
    [
        {"as_of": datetime(2026, 11, 9)},
        {"timezone": "Europe/London"},
        {"cohort_to": date(2026, 11, 1)},
        {"cohort_from": datetime(2026, 11, 1, tzinfo=UTC)},
    ],
)
def test_query_contract_rejects_ambiguous_or_empty_range(changes: dict[str, Any]) -> None:
    kwargs: dict[str, Any] = {
        "cohort_from": date(2026, 11, 1),
        "cohort_to": date(2026, 11, 2),
        "as_of": datetime(2026, 11, 9, tzinfo=UTC),
    }
    with pytest.raises(ValueError):
        summarize_d7([], [], **(kwargs | changes))


@pytest.mark.parametrize(
    ("ready_offset", "asof_offset", "status", "activated", "rate"),
    [
        (timedelta(microseconds=-1), timedelta(days=7), "available", 0, Decimal(0)),
        (timedelta(days=7), timedelta(days=7), "available", 0, Decimal(0)),
        (timedelta(days=7, microseconds=-1), timedelta(days=7), "available", 1, Decimal(1)),
        (timedelta(0), timedelta(days=7, microseconds=-1), "insufficient_history", 0, None),
        (timedelta(0), timedelta(days=7), "available", 1, Decimal(1)),
    ],
)
def test_personal_deadline_boundaries(
    ready_offset: timedelta, asof_offset: timedelta, status: str, activated: int, rate: Decimal | None
) -> None:
    signup = datetime(2026, 11, 1, tzinfo=UTC)
    result = summarize_d7(
        [Registration(UUID(int=1), signup)],
        [BasicReady(UUID(int=2), UUID(int=1), signup + ready_offset)],
        cohort_from=date(2026, 11, 1),
        cohort_to=date(2026, 11, 2),
        as_of=signup + asof_offset,
    )
    assert result.status == status
    assert result.activated == activated
    assert result.rate == rate


def test_mixed_maturity_never_presents_subset_rate_as_complete() -> None:
    signup = datetime(2026, 11, 1, tzinfo=UTC)
    result = summarize_d7(
        [Registration(UUID(int=1), signup), Registration(UUID(int=2), signup + timedelta(hours=1))],
        [BasicReady(UUID(int=3), UUID(int=1), signup)],
        cohort_from=date(2026, 11, 1),
        cohort_to=date(2026, 11, 2),
        as_of=signup + timedelta(days=7),
    )
    assert (result.registrations, result.mature, result.immature, result.activated) == (2, 1, 1, 1)
    assert result.rate is None
    assert result.status == "insufficient_history"


def test_upper_calendar_boundary_and_other_owner_do_not_activate() -> None:
    signup = datetime(2026, 11, 1, tzinfo=ZoneInfo("Europe/Moscow"))
    result = summarize_d7(
        [Registration(UUID(int=1), signup), Registration(UUID(int=2), signup + timedelta(days=1))],
        [BasicReady(UUID(int=3), UUID(int=2), signup)],
        cohort_from=date(2026, 11, 1),
        cohort_to=date(2026, 11, 2),
        as_of=signup + timedelta(days=8),
    )
    assert (result.registrations, result.mature, result.activated) == (1, 1, 0)
    assert result.rate == Decimal(0)


def test_empty_cohort_has_no_rate_not_zero_conversion() -> None:
    result = summarize_d7(
        [], [], cohort_from=date(2026, 11, 1), cohort_to=date(2026, 11, 2), as_of=datetime(2026, 11, 9, tzinfo=UTC)
    )
    assert result.rate is None
    assert result.status == "no_data"
