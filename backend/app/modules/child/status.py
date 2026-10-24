"""State machine and retry policy for asynchronous Child Report generation."""

from __future__ import annotations

from enum import StrEnum


class ChildGenerationOperation(StrEnum):
    FULL_REPORT = "full_report"
    NARRATIVE_RETRY = "narrative_retry"
    AGE_UPDATE = "age_update"


class ChildGenerationStatus(StrEnum):
    QUEUED = "queued"
    CALCULATING_PAIR = "calculating_pair"
    DETERMINISTIC_READY = "deterministic_ready"
    GENERATING_SECTIONS = "generating_sections"
    NARRATIVE_RETRY_WAITING = "narrative_retry_waiting"
    READY = "ready"
    NARRATIVE_FAILED = "narrative_failed"
    FAILED = "failed"
    AGE_UPDATE_QUEUED = "age_update_queued"
    AGE_UPDATE_RUNNING = "age_update_running"
    AGE_UPDATE_READY = "age_update_ready"
    AGE_UPDATE_FAILED = "age_update_failed"


class ChildGenerationEventCode(StrEnum):
    ACCEPTED = "accepted"
    DISPATCH_CLAIMED = "dispatch_claimed"
    DISPATCH_SUCCEEDED = "dispatch_succeeded"
    DISPATCH_FAILED = "dispatch_failed"
    WORKER_CLAIMED = "worker_claimed"
    STATUS_TRANSITIONED = "status_transitioned"
    RETRY_RELEASED = "retry_released"
    RECONCILIATION_REQUEUED = "reconciliation_requeued"
    RECONCILIATION_EXHAUSTED = "reconciliation_exhausted"
    TERMINAL_FAILED = "terminal_failed"


FULL_ACTIVE_STATUSES = frozenset(
    {
        ChildGenerationStatus.CALCULATING_PAIR,
        ChildGenerationStatus.DETERMINISTIC_READY,
        ChildGenerationStatus.GENERATING_SECTIONS,
    }
)
FULL_TERMINAL_STATUSES = frozenset(
    {
        ChildGenerationStatus.READY,
        ChildGenerationStatus.NARRATIVE_FAILED,
        ChildGenerationStatus.FAILED,
    }
)
CLAIMABLE_STATUSES = frozenset(
    {
        ChildGenerationStatus.QUEUED,
        ChildGenerationStatus.NARRATIVE_RETRY_WAITING,
        ChildGenerationStatus.AGE_UPDATE_QUEUED,
    }
)
AGE_TERMINAL_STATUSES = frozenset({ChildGenerationStatus.AGE_UPDATE_READY, ChildGenerationStatus.AGE_UPDATE_FAILED})

_ALLOWED_TRANSITIONS = {
    ChildGenerationStatus.QUEUED: frozenset({ChildGenerationStatus.CALCULATING_PAIR, ChildGenerationStatus.FAILED}),
    ChildGenerationStatus.CALCULATING_PAIR: frozenset(
        {ChildGenerationStatus.DETERMINISTIC_READY, ChildGenerationStatus.FAILED}
    ),
    ChildGenerationStatus.DETERMINISTIC_READY: frozenset(
        {ChildGenerationStatus.GENERATING_SECTIONS, ChildGenerationStatus.NARRATIVE_FAILED}
    ),
    ChildGenerationStatus.GENERATING_SECTIONS: frozenset(
        {ChildGenerationStatus.READY, ChildGenerationStatus.NARRATIVE_FAILED}
    ),
    ChildGenerationStatus.AGE_UPDATE_QUEUED: frozenset(
        {ChildGenerationStatus.AGE_UPDATE_RUNNING, ChildGenerationStatus.AGE_UPDATE_FAILED}
    ),
    ChildGenerationStatus.AGE_UPDATE_RUNNING: frozenset(
        {ChildGenerationStatus.AGE_UPDATE_READY, ChildGenerationStatus.AGE_UPDATE_FAILED}
    ),
}


class InvalidChildGenerationTransitionError(ValueError):
    """Raised when lifecycle code attempts an undocumented state transition."""


def require_transition(current: str, target: str) -> None:
    """Validate an ordinary forward transition."""

    try:
        current_status = ChildGenerationStatus(current)
        target_status = ChildGenerationStatus(target)
    except ValueError as exc:
        raise InvalidChildGenerationTransitionError("unknown child generation status") from exc
    if target_status not in _ALLOWED_TRANSITIONS.get(current_status, frozenset()):
        raise InvalidChildGenerationTransitionError(f"invalid child generation transition: {current} -> {target}")


def terminal_failure_status(*, report_id_present: bool) -> ChildGenerationStatus:
    """Preserve a published deterministic report when later narrative work fails."""

    return ChildGenerationStatus.NARRATIVE_FAILED if report_id_present else ChildGenerationStatus.FAILED
