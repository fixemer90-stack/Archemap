"""Calendar-correct, server-owned age resolution for child artifacts."""

from __future__ import annotations

import calendar
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Final, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

AGE_RULES_VERSION: Final = "child-age-mvp-1"
AgeStage = Literal["0-1", "1-3", "3-6", "6-9", "9-12", "12-15", "15-18"]


class FutureBirthDateError(ValueError):
    """Raised when a birth date is after the resolved local date."""


class UnsupportedChildAgeError(ValueError):
    """Raised when the subject is outside the under-18 Child Report scope."""


@dataclass(frozen=True, slots=True)
class ChildAgeResolution:
    """Deterministic input for one immutable age snapshot."""

    birth_date: date
    as_of_date: date
    age_years: int
    age_months: int
    age_days: int
    age_stage: AgeStage
    age_rules_version: str
    input_hash: str


def age_snapshot_input_hash(
    *,
    birth_date: date,
    as_of_date: date,
    age_rules_version: str = AGE_RULES_VERSION,
) -> str:
    """Hash canonical server-owned age inputs; callers cannot supply this value."""

    payload = {
        "age_rules_version": age_rules_version,
        "as_of_date": as_of_date.isoformat(),
        "birth_date": birth_date.isoformat(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def age_snapshot_is_current(
    *,
    snapshot_as_of_date: date,
    snapshot_rules_version: str,
    snapshot_input_hash: str,
    current: ChildAgeResolution,
) -> bool:
    """A snapshot is current only for the exact local date, rules, and DOB-derived hash."""

    return (
        snapshot_as_of_date == current.as_of_date
        and snapshot_rules_version == current.age_rules_version
        and snapshot_input_hash == current.input_hash
    )


def resolve_child_age(
    *,
    birth_date: date,
    as_of: date | datetime,
    timezone_name: str,
    age_rules_version: str = AGE_RULES_VERSION,
) -> ChildAgeResolution:
    """Resolve exact calendar age using the child's local civil date."""

    as_of_date = _local_date(as_of=as_of, timezone_name=timezone_name)
    if birth_date > as_of_date:
        raise FutureBirthDateError("Birth date cannot be in the future")

    total_months = (as_of_date.year - birth_date.year) * 12 + (as_of_date.month - birth_date.month)
    if _add_months_clamped(birth_date, total_months) > as_of_date:
        total_months -= 1
    if total_months >= 18 * 12:
        raise UnsupportedChildAgeError("Child Report supports ages under 18 only")

    years, months = divmod(total_months, 12)
    month_anniversary = _add_months_clamped(birth_date, total_months)
    days = (as_of_date - month_anniversary).days
    stage = _age_stage(years)

    return ChildAgeResolution(
        birth_date=birth_date,
        as_of_date=as_of_date,
        age_years=years,
        age_months=months,
        age_days=days,
        age_stage=stage,
        age_rules_version=age_rules_version,
        input_hash=age_snapshot_input_hash(
            birth_date=birth_date,
            as_of_date=as_of_date,
            age_rules_version=age_rules_version,
        ),
    )


def _local_date(*, as_of: date | datetime, timezone_name: str) -> date:
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {timezone_name}") from exc
    if isinstance(as_of, datetime):
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of datetime must be timezone-aware")
        return as_of.astimezone(timezone).date()
    return as_of


def _add_months_clamped(value: date, months: int) -> date:
    absolute_month = value.year * 12 + (value.month - 1) + months
    target_year, zero_based_month = divmod(absolute_month, 12)
    target_month = zero_based_month + 1
    target_day = min(value.day, calendar.monthrange(target_year, target_month)[1])
    return date(target_year, target_month, target_day)


def _age_stage(age_years: int) -> AgeStage:
    if age_years < 1:
        return "0-1"
    if age_years < 3:
        return "1-3"
    if age_years < 6:
        return "3-6"
    if age_years < 9:
        return "6-9"
    if age_years < 12:
        return "9-12"
    if age_years < 15:
        return "12-15"
    return "15-18"
