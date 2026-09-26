from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, call

import pytest

from app.modules.career.models import CareerReport
from workers.tasks.career import (
    _persist_parent_rows_before_children,
    build_career_monitor_alerts,
    build_regeneration_report_row,
    failure_status_for_generation,
)


def _source_report() -> CareerReport:
    return CareerReport(
        career_profile_id=uuid.uuid4(),
        chart_id=uuid.uuid4(),
        generation_id=uuid.uuid4(),
        idempotency_key="source",
        version=3,
        status="ready",
        scoring_version="career-mvp-1",
        reference_version="career-ref-1",
        questionnaire_version="career-q-1",
        prompt_version="career-prompt-1",
        deterministic_payload={"contract_version": "career_interpretation_facts_v1", "marker": "immutable"},
        narrative_payload={"sections": [{"section_key": "old"}]},
        assembled_payload={"status": "ready"},
    )


def test_regeneration_report_preserves_deterministic_artifacts() -> None:
    source = _source_report()
    generation_id = uuid.uuid4()

    regenerated = build_regeneration_report_row(
        source=source,
        generation_id=generation_id,
        idempotency_key="retry-1",
    )

    assert regenerated.generation_id == generation_id
    assert regenerated.version == source.version + 1
    assert regenerated.status == "deterministic_ready"
    assert source.status == "ready"
    assert regenerated.deterministic_payload == source.deterministic_payload
    assert regenerated.deterministic_payload is not source.deterministic_payload
    assert regenerated.narrative_payload["sections"] == []


def test_failure_after_deterministic_commit_is_narrative_failure() -> None:
    assert failure_status_for_generation(report_id=uuid.uuid4()) == "narrative_failed"
    assert failure_status_for_generation(report_id=None) == "failed"


@pytest.mark.asyncio
async def test_parent_artifacts_are_flushed_before_fk_children() -> None:
    repository = AsyncMock()
    parent_rows = [_source_report(), _source_report()]
    child_rows = [_source_report(), _source_report()]

    await _persist_parent_rows_before_children(
        repository=repository,
        parent_rows=parent_rows,
        child_rows=child_rows,
    )

    assert repository.mock_calls == [
        call.add_many(parent_rows),
        call.flush(),
        call.add_many(child_rows),
    ]


def test_monitor_alerts_cover_stuck_pipeline_and_validator_failure_spike() -> None:
    alerts = build_career_monitor_alerts(
        stuck_by_stage={"deterministic": 2, "narrative": 1},
        validator_failures=5,
        validator_failure_threshold=5,
    )

    assert alerts == (
        "career_stuck_generation:deterministic:2",
        "career_stuck_generation:narrative:1",
        "career_validator_failure_spike:5",
    )
