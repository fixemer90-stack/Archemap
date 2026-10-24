from __future__ import annotations

import pytest

from app.modules.child.status import (
    AGE_TERMINAL_STATUSES,
    CLAIMABLE_STATUSES,
    FULL_TERMINAL_STATUSES,
    ChildGenerationStatus,
    InvalidChildGenerationTransitionError,
    require_transition,
    terminal_failure_status,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("queued", "calculating_pair"),
        ("queued", "failed"),
        ("calculating_pair", "deterministic_ready"),
        ("calculating_pair", "failed"),
        ("deterministic_ready", "generating_sections"),
        ("deterministic_ready", "narrative_failed"),
        ("generating_sections", "ready"),
        ("generating_sections", "narrative_failed"),
        ("age_update_queued", "age_update_running"),
        ("age_update_running", "age_update_ready"),
        ("age_update_running", "age_update_failed"),
    ],
)
def test_generation_transition_matrix_accepts_only_documented_edges(current: str, target: str) -> None:
    require_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("queued", "ready"),
        ("calculating_pair", "generating_sections"),
        ("deterministic_ready", "failed"),
        ("ready", "queued"),
        ("narrative_failed", "generating_sections"),
        ("failed", "calculating_pair"),
        ("age_update_queued", "calculating_pair"),
        ("age_update_queued", "age_update_ready"),
        ("queued", "age_update_ready"),
        ("unknown", "ready"),
    ],
)
def test_generation_transition_matrix_rejects_cross_stage_and_terminal_edges(current: str, target: str) -> None:
    with pytest.raises(InvalidChildGenerationTransitionError):
        require_transition(current, target)


def test_failure_status_preserves_published_deterministic_report() -> None:
    assert terminal_failure_status(report_id_present=False) is ChildGenerationStatus.FAILED
    assert terminal_failure_status(report_id_present=True) is ChildGenerationStatus.NARRATIVE_FAILED
    assert ChildGenerationStatus.READY in FULL_TERMINAL_STATUSES
    assert ChildGenerationStatus.AGE_UPDATE_READY in AGE_TERMINAL_STATUSES
    assert {
        ChildGenerationStatus.QUEUED,
        ChildGenerationStatus.NARRATIVE_RETRY_WAITING,
        ChildGenerationStatus.AGE_UPDATE_QUEUED,
    } == CLAIMABLE_STATUSES
