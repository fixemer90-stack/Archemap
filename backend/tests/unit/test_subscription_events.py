"""E6.S15 subscription event, logging, and metric contracts."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from app.modules.subscriptions.models import Subscription, SubscriptionEvent, SubscriptionPlan
from app.modules.subscriptions.observability import SubscriptionTelemetry
from app.modules.subscriptions.service import SubscriptionsService

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


class _Counter:
    def __init__(self) -> None:
        self.calls: list[tuple[float, Mapping[str, str] | None]] = []

    def add(self, amount: float, attributes: Mapping[str, str] | None = None) -> None:
        self.calls.append((amount, attributes))


class _Repo:
    def __init__(self, subscription: Subscription) -> None:
        self.subscription = subscription
        self.events: dict[str, SubscriptionEvent] = {}

    async def ensure_plan(self, **_values: Any) -> SubscriptionPlan:
        raise AssertionError("not used")

    async def create_subscription(self, **_values: Any) -> Subscription:
        raise AssertionError("not used")

    async def get_subscription(self, subscription_id: UUID, *, for_update: bool = False) -> Subscription | None:
        del for_update
        return self.subscription if self.subscription.id == subscription_id else None

    async def get_latest_for_user(self, user_id: UUID) -> Subscription | None:
        return self.subscription if self.subscription.user_id == user_id else None

    async def append_event(self, **values: Any) -> tuple[SubscriptionEvent, bool]:
        key = str(values["event_key"])
        if key in self.events:
            return self.events[key], False
        event = SubscriptionEvent(**values)
        event.id = uuid4()
        self.events[key] = event
        return event, True


def _subscription(*, status: str = "active") -> Subscription:
    subscription = Subscription(
        user_id=uuid4(),
        plan_id=uuid4(),
        provider="yookassa",
        status=status,
        current_period_start=NOW - timedelta(days=5),
        current_period_end=NOW + timedelta(days=25),
        cancel_at_period_end=status == "cancel_scheduled",
        metadata_json={"plan_code": "astrotype_plus_monthly"},
    )
    subscription.id = uuid4()
    return subscription


async def test_cancel_and_resume_each_append_audited_transition_event() -> None:
    subscription = _subscription()
    repo = _Repo(subscription)
    service = SubscriptionsService(None, repository=repo)  # type: ignore[arg-type]

    await service.cancel_at_period_end(
        subscription_id=subscription.id,
        user_id=subscription.user_id,
        reason="user_request",
        now=NOW,
    )
    await service.resume(
        subscription_id=subscription.id,
        user_id=subscription.user_id,
        now=NOW + timedelta(seconds=1),
    )

    assert [event.event_type for event in repo.events.values()] == ["cancel_requested", "resume_requested"]
    assert repo.events[next(iter(repo.events))].payload_json["reason"] == "user_request"


def test_subscription_telemetry_rejects_unbounded_failure_codes() -> None:
    transitions = _Counter()
    failures = _Counter()
    telemetry = SubscriptionTelemetry(transitions=transitions, failures=failures)

    telemetry.record_transition(event_type="renewal_failed", old_status="active", new_status="past_due")
    telemetry.record_failure("renewal_failed")
    telemetry.record_failure("user@example.com")

    assert transitions.calls == [
        (1, {"event_type": "renewal_failed", "old_status": "active", "new_status": "past_due"})
    ]
    assert failures.calls == [(1, {"code": "renewal_failed"})]
