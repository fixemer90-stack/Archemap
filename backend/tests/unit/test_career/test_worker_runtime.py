from __future__ import annotations

import uuid
from typing import cast
from unittest.mock import AsyncMock, MagicMock, Mock, call

import pytest

from app.config import settings
from app.modules.career.models import CareerGeneration, CareerReport
from app.modules.career.narrative_schemas import CareerSectionRenderInput
from app.modules.career.repository import CareerRepository
from workers.tasks.career import (
    _persist_parent_rows_before_children,
    _run_narrative_quality_pipeline,
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
        version=7,
    )

    assert regenerated.generation_id == generation_id
    assert regenerated.version == 7
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


@pytest.mark.asyncio
async def test_active_worker_narrative_pipeline_runs_segment_and_assembly_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _source_report()
    section_inputs = cast(
        list[CareerSectionRenderInput],
        [Mock(section_key="professional_summary"), Mock(section_key="work_style")],
    )
    segment_rows = [Mock(section_key="professional_summary"), Mock(section_key="work_style")]
    run_gate = AsyncMock(side_effect=segment_rows)
    assembled = Mock(status="ready")
    assembly_gate = Mock(return_value=assembled)
    monkeypatch.setattr("workers.tasks.career.run_career_segment_generation", run_gate)
    monkeypatch.setattr("workers.tasks.career.assemble_career_report_row", assembly_gate)

    rows, result = await _run_narrative_quality_pipeline(
        provider=Mock(),
        report=report,
        section_inputs=section_inputs,
    )

    assert rows == segment_rows
    assert result is assembled
    assert run_gate.await_count == 2
    assembly_gate.assert_called_once_with(report=report, segment_rows=segment_rows)


@pytest.mark.asyncio
async def test_active_worker_narrative_pipeline_reruns_a_section_rejected_by_the_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _source_report()
    section_inputs = cast(
        list[CareerSectionRenderInput],
        [Mock(section_key="professional_summary")],
    )
    rejected = Mock(status="failed", error="career_validation_failure")
    accepted = Mock(status="ready", error=None)
    run_gate = AsyncMock(side_effect=[rejected, accepted])
    monkeypatch.setattr("workers.tasks.career.run_career_segment_generation", run_gate)
    monkeypatch.setattr("workers.tasks.career.assemble_career_report_row", Mock(return_value=Mock(status="ready")))

    rows, _ = await _run_narrative_quality_pipeline(
        provider=Mock(),
        report=report,
        section_inputs=section_inputs,
    )

    assert rows == [accepted]
    assert run_gate.await_count == 2


@pytest.mark.asyncio
async def test_active_worker_narrative_pipeline_keeps_a_section_that_failed_for_another_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _source_report()
    section_inputs = cast(
        list[CareerSectionRenderInput],
        [Mock(section_key="professional_summary")],
    )
    unsupported = Mock(status="failed", error="career_contract_mismatch")
    run_gate = AsyncMock(side_effect=[unsupported])
    monkeypatch.setattr("workers.tasks.career.run_career_segment_generation", run_gate)
    monkeypatch.setattr("workers.tasks.career.assemble_career_report_row", Mock(return_value=Mock(status="ready")))

    rows, _ = await _run_narrative_quality_pipeline(
        provider=Mock(),
        report=report,
        section_inputs=section_inputs,
    )

    assert rows == [unsupported]
    assert run_gate.await_count == 1


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


@pytest.mark.asyncio
async def test_generation_claim_allows_only_queued_worker() -> None:
    claimed = CareerGeneration(
        generation_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        career_profile_id=uuid.uuid4(),
        chart_id=uuid.uuid4(),
        operation="create",
        idempotency_key="claim-1",
        status="calculating_dimensions",
        diagnostics={"stage": "deterministic"},
    )
    first_result = AsyncMock()
    first_result.scalar_one_or_none = lambda: claimed
    second_result = AsyncMock()
    second_result.scalar_one_or_none = lambda: None
    session = AsyncMock()
    session.execute.side_effect = [first_result, second_result]
    repository = CareerRepository(session)

    assert await repository.claim_generation(uuid.uuid4()) is claimed
    assert await repository.claim_generation(uuid.uuid4()) is None


@pytest.mark.asyncio
async def test_monitor_pipeline_emits_safe_alerts_without_live_infrastructure(monkeypatch: pytest.MonkeyPatch) -> None:
    from workers.tasks import career as career_tasks

    stuck_result = MagicMock()
    stuck_result.all.return_value = [("queued", 2), ("deterministic_ready", 1)]
    validator_result = MagicMock()
    validator_result.scalar_one.return_value = 5

    db = AsyncMock()
    db.execute.side_effect = [stuck_result, validator_result]
    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=db)
    session_context.__aexit__ = AsyncMock(return_value=False)

    telemetry = MagicMock()
    alert_logger = MagicMock()
    monkeypatch.setattr(career_tasks, "async_session_factory", MagicMock(return_value=session_context))
    monkeypatch.setattr(settings, "CAREER_VALIDATOR_ALERT_THRESHOLD", 5)
    monkeypatch.setattr(career_tasks, "career_telemetry", telemetry)
    monkeypatch.setattr(career_tasks, "logger", alert_logger)

    result = await career_tasks._monitor_career_pipeline_async()

    assert result == {
        "stuck_by_stage": {"deterministic": 2, "narrative": 1},
        "validator_failures": 5,
        "alerts": [
            "career_stuck_generation:deterministic:2",
            "career_stuck_generation:narrative:1",
            "career_validator_failure_spike:5",
        ],
    }
    assert telemetry.record.call_args_list == [
        call(
            stage="deterministic",
            outcome="stuck",
            operation="scan",
            error_code="career_stuck_generation",
            amount=2,
        ),
        call(
            stage="narrative",
            outcome="stuck",
            operation="scan",
            error_code="career_stuck_generation",
            amount=1,
        ),
    ]
    assert alert_logger.warning.call_args_list == [
        call("career_pipeline_alert", alert="career_stuck_generation:deterministic:2"),
        call("career_pipeline_alert", alert="career_stuck_generation:narrative:1"),
        call("career_pipeline_alert", alert="career_validator_failure_spike:5"),
    ]
