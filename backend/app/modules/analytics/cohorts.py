"""Pure D7 cohort calculation; no queries, exports or provider side effects."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo


def _utc_instant(value: object) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("An aware datetime is required")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class Registration:
    user_id: UUID
    occurred_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UUID):
            raise ValueError("Account identity must be a UUID")
        object.__setattr__(self, "occurred_at", _utc_instant(self.occurred_at))


@dataclass(frozen=True, slots=True)
class BasicReady:
    """Caller must prove a persisted, owned, usable Self foundation transition."""

    report_id: UUID
    user_id: UUID
    occurred_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.report_id, UUID) or not isinstance(self.user_id, UUID):
            raise ValueError("Artifact and account identities must be UUIDs")
        object.__setattr__(self, "occurred_at", _utc_instant(self.occurred_at))


@dataclass(frozen=True, slots=True)
class D7Summary:
    registrations: int
    mature: int
    immature: int
    activated: int
    rate: Decimal | None
    status: Literal["available", "insufficient_history", "no_data"]


def summarize_d7(
    registrations: Iterable[Registration],
    artifacts: Iterable[BasicReady],
    *,
    cohort_from: date,
    cohort_to: date,
    as_of: datetime,
    timezone: Literal["Europe/Moscow", "UTC"] = "Europe/Moscow",
) -> D7Summary:
    """Bucket signups by calendar; observe each for seven elapsed UTC days."""
    as_of = _utc_instant(as_of)
    if timezone not in ("Europe/Moscow", "UTC"):
        raise ValueError("Unsupported business timezone")
    if type(cohort_from) is not date or type(cohort_to) is not date or cohort_from >= cohort_to:
        raise ValueError("A nonempty plain-date cohort range is required")
    zone = ZoneInfo(timezone)
    start = datetime.combine(cohort_from, time.min, tzinfo=zone).astimezone(UTC)
    end = datetime.combine(cohort_to, time.min, tzinfo=zone).astimezone(UTC)
    accounts: dict[UUID, Registration] = {}
    for account in registrations:
        if not isinstance(account, Registration):
            raise ValueError("Typed account evidence is required")
        if account.user_id in accounts and accounts[account.user_id] != account:
            raise ValueError("Conflicting registration evidence")
        accounts[account.user_id] = account
    reports: dict[UUID, BasicReady] = {}
    for artifact in artifacts:
        if not isinstance(artifact, BasicReady):
            raise ValueError("Typed basic artifact evidence is required")
        if artifact.report_id in reports and reports[artifact.report_id] != artifact:
            raise ValueError("Conflicting basic artifact evidence")
        reports[artifact.report_id] = artifact
    ready_by_user: dict[UUID, datetime] = {}
    for item in reports.values():
        previous = ready_by_user.get(item.user_id)
        if previous is None or item.occurred_at < previous:
            ready_by_user[item.user_id] = item.occurred_at
    selected = mature = activated = 0
    for account in accounts.values():
        signup = account.occurred_at.astimezone(UTC)
        if not start <= signup < end or signup > as_of:
            continue
        selected += 1
        deadline = signup + timedelta(days=7)
        if as_of < deadline:
            continue
        mature += 1
        first_ready = ready_by_user.get(account.user_id)
        if first_ready is not None and signup <= first_ready < deadline:
            activated += 1
    immature = selected - mature
    if immature:
        return D7Summary(selected, mature, immature, activated, None, "insufficient_history")
    if mature == 0:
        return D7Summary(selected, 0, 0, 0, None, "no_data")
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        rate = Decimal(activated) / mature
    return D7Summary(selected, mature, 0, activated, rate, "available")
