"""Low-cardinality metrics for monthly subscription operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from opentelemetry import metrics

_ALLOWED_EVENT_TYPES = frozenset(
    {
        "checkout_created",
        "initial_payment_succeeded",
        "renewal_succeeded",
        "renewal_failed",
        "cancel_requested",
        "resume_requested",
        "subscription_suspended",
        "manual_reconciliation_requested",
    }
)
_ALLOWED_STATUSES = frozenset(
    {
        "none",
        "incomplete",
        "active",
        "renewal_pending",
        "past_due",
        "cancel_scheduled",
        "suspended",
        "expired",
        "cancelled",
    }
)
_ALLOWED_FAILURE_CODES = frozenset(
    {
        "renewal_failed",
        "webhook_provider_reconciliation_failed",
        "pending_payment_reconciliation_mismatch",
        "webhook_payment_mismatch",
    }
)


class _Counter(Protocol):
    def add(self, amount: float, attributes: Mapping[str, str] | None = None) -> None: ...


class SubscriptionTelemetry:
    """Record bounded lifecycle labels without user/provider identifiers."""

    def __init__(self, *, transitions: _Counter, failures: _Counter) -> None:
        self.transitions = transitions
        self.failures = failures

    def record_transition(self, *, event_type: str, old_status: str, new_status: str) -> None:
        if (
            event_type not in _ALLOWED_EVENT_TYPES
            or old_status not in _ALLOWED_STATUSES
            or new_status not in _ALLOWED_STATUSES
        ):
            return
        self.transitions.add(
            1,
            {
                "event_type": event_type,
                "old_status": old_status,
                "new_status": new_status,
            },
        )

    def record_failure(self, code: str) -> None:
        if code in _ALLOWED_FAILURE_CODES:
            self.failures.add(1, {"code": code})


_meter = metrics.get_meter("archemap.subscriptions")
subscription_telemetry = SubscriptionTelemetry(
    transitions=_meter.create_counter(
        "subscription_state_transitions",
        description="Monthly subscription lifecycle transitions by bounded state and event type",
    ),
    failures=_meter.create_counter(
        "subscription_operation_failures",
        description="Monthly subscription provider and renewal failures by bounded code",
    ),
)
