from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.modules.child.age_resolver import (
    AGE_RULES_VERSION,
    FutureBirthDateError,
    UnsupportedChildAgeError,
    age_snapshot_input_hash,
    age_snapshot_is_current,
    resolve_child_age,
)


@pytest.mark.parametrize(
    ("birth_date", "as_of_date", "expected"),
    [
        (date(2025, 10, 16), date(2026, 10, 15), (0, 11, 29, "0-1")),
        (date(2025, 10, 16), date(2026, 10, 16), (1, 0, 0, "1-3")),
        (date(2023, 10, 16), date(2026, 10, 15), (2, 11, 29, "1-3")),
        (date(2023, 10, 16), date(2026, 10, 16), (3, 0, 0, "3-6")),
        (date(2020, 10, 16), date(2026, 10, 16), (6, 0, 0, "6-9")),
        (date(2017, 10, 16), date(2026, 10, 16), (9, 0, 0, "9-12")),
        (date(2014, 10, 16), date(2026, 10, 16), (12, 0, 0, "12-15")),
        (date(2011, 10, 16), date(2026, 10, 16), (15, 0, 0, "15-18")),
        (date(2008, 10, 17), date(2026, 10, 16), (17, 11, 29, "15-18")),
    ],
)
def test_resolver_uses_exact_calendar_stage_boundaries(
    birth_date: date,
    as_of_date: date,
    expected: tuple[int, int, int, str],
) -> None:
    resolved = resolve_child_age(birth_date=birth_date, as_of=as_of_date, timezone_name="UTC")

    assert (resolved.age_years, resolved.age_months, resolved.age_days, resolved.age_stage) == expected
    assert resolved.age_rules_version == AGE_RULES_VERSION


def test_resolver_handles_leap_day_and_month_end_by_clamping_calendar_anniversaries() -> None:
    leap_day = resolve_child_age(
        birth_date=date(2024, 2, 29),
        as_of=date(2025, 2, 28),
        timezone_name="UTC",
    )
    leap_month_later = resolve_child_age(
        birth_date=date(2024, 2, 29),
        as_of=date(2025, 3, 29),
        timezone_name="UTC",
    )
    month_end = resolve_child_age(
        birth_date=date(2026, 1, 31),
        as_of=date(2026, 2, 28),
        timezone_name="UTC",
    )

    assert (leap_day.age_years, leap_day.age_months, leap_day.age_days) == (1, 0, 0)
    assert (leap_month_later.age_years, leap_month_later.age_months, leap_month_later.age_days) == (1, 1, 0)
    assert (month_end.age_years, month_end.age_months, month_end.age_days) == (0, 1, 0)


def test_resolver_derives_local_date_from_aware_datetime() -> None:
    instant = datetime(2026, 5, 12, 0, 30, tzinfo=UTC)

    new_york = resolve_child_age(
        birth_date=date(2021, 5, 12),
        as_of=instant,
        timezone_name="America/New_York",
    )
    moscow = resolve_child_age(
        birth_date=date(2021, 5, 12),
        as_of=instant,
        timezone_name="Europe/Moscow",
    )

    assert (new_york.as_of_date, new_york.age_years) == (date(2026, 5, 11), 4)
    assert (moscow.as_of_date, moscow.age_years) == (date(2026, 5, 12), 5)


def test_resolver_rejects_naive_datetime_future_dob_and_adults() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        resolve_child_age(
            birth_date=date(2021, 1, 1),
            as_of=datetime(2026, 1, 1),
            timezone_name="UTC",
        )
    with pytest.raises(FutureBirthDateError):
        resolve_child_age(
            birth_date=date(2026, 1, 2),
            as_of=date(2026, 1, 1),
            timezone_name="UTC",
        )
    with pytest.raises(UnsupportedChildAgeError):
        resolve_child_age(
            birth_date=date(2008, 10, 16),
            as_of=date(2026, 10, 16),
            timezone_name="UTC",
        )


def test_input_hash_is_canonical_and_policy_versioned() -> None:
    first = age_snapshot_input_hash(
        birth_date=date(2021, 5, 12),
        as_of_date=date(2026, 10, 16),
        age_rules_version="child-age-mvp-1",
    )
    same = age_snapshot_input_hash(
        as_of_date=date(2026, 10, 16),
        age_rules_version="child-age-mvp-1",
        birth_date=date(2021, 5, 12),
    )
    corrected_dob = age_snapshot_input_hash(
        birth_date=date(2021, 5, 13),
        as_of_date=date(2026, 10, 16),
        age_rules_version="child-age-mvp-1",
    )
    new_rules = age_snapshot_input_hash(
        birth_date=date(2021, 5, 12),
        as_of_date=date(2026, 10, 16),
        age_rules_version="child-age-mvp-2",
    )

    assert first == same
    assert len(first) == 64
    assert first != corrected_dob
    assert first != new_rules


def test_snapshot_is_current_only_for_exact_local_date_rules_and_input_hash() -> None:
    resolved = resolve_child_age(
        birth_date=date(2021, 5, 12),
        as_of=date(2026, 10, 16),
        timezone_name="UTC",
    )

    assert age_snapshot_is_current(
        snapshot_as_of_date=resolved.as_of_date,
        snapshot_rules_version=resolved.age_rules_version,
        snapshot_input_hash=resolved.input_hash,
        current=resolved,
    )
    assert not age_snapshot_is_current(
        snapshot_as_of_date=date(2026, 10, 15),
        snapshot_rules_version=resolved.age_rules_version,
        snapshot_input_hash=resolved.input_hash,
        current=resolved,
    )
    assert not age_snapshot_is_current(
        snapshot_as_of_date=resolved.as_of_date,
        snapshot_rules_version="child-age-mvp-2",
        snapshot_input_hash=resolved.input_hash,
        current=resolved,
    )
    assert not age_snapshot_is_current(
        snapshot_as_of_date=resolved.as_of_date,
        snapshot_rules_version=resolved.age_rules_version,
        snapshot_input_hash="0" * 64,
        current=resolved,
    )
