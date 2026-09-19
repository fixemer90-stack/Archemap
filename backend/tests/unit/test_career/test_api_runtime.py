from __future__ import annotations

import uuid

from app.modules.career.models import CareerGeneration, CareerReport, CareerSegmentGeneration


def _generation(*, status: str = "queued", report_id: uuid.UUID | None = None) -> CareerGeneration:
    return CareerGeneration(
        generation_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        career_profile_id=uuid.uuid4(),
        chart_id=uuid.uuid4(),
        report_id=report_id,
        operation="create",
        idempotency_key="create-1",
        status=status,
        diagnostics={},
    )


def _report(*, status: str = "deterministic_ready") -> CareerReport:
    return CareerReport(
        career_profile_id=uuid.uuid4(),
        chart_id=uuid.uuid4(),
        generation_id=uuid.uuid4(),
        idempotency_key="report-1",
        version=1,
        status=status,
        scoring_version="career-mvp-1",
        reference_version="career-ref-1",
        questionnaire_version="career-q-1",
        prompt_version="career-prompt-1",
        deterministic_payload={"top_dimensions": [{"fact_key": "dimension:systems"}]},
        narrative_payload={"sections": []},
        assembled_payload={"contract_version": "career_report_v1"},
    )


def _segment(report: CareerReport, *, section_key: str, status: str) -> CareerSegmentGeneration:
    return CareerSegmentGeneration(
        career_profile_id=report.career_profile_id,
        chart_id=report.chart_id,
        generation_id=report.generation_id,
        section_key=section_key,
        status=status,
        prompt_version="career-prompt-1",
        provider="mock",
        model_version="mock-1",
        input_payload={},
        output_payload={
            "contract_version": "career_segment_output_v1",
            "section_key": section_key,
            "title": "Раздел",
            "body": "Проверяемая интерпретация.",
            "cited_fact_keys": ["dimension:systems"],
            "continuation_complete": True,
            "continuation_cursor": None,
        }
        if status == "ready"
        else {},
        error="career_provider_failure" if status == "failed" else None,
    )


def test_generation_status_separates_deterministic_and_narrative_progress() -> None:
    from app.modules.career.api_runtime import build_generation_status_payload

    report = _report(status="generating_sections")
    generation = _generation(status="generating_sections", report_id=report.id)
    segments = [
        _segment(report, section_key="professional_summary", status="ready"),
        _segment(report, section_key="work_style", status="failed"),
    ]

    payload = build_generation_status_payload(generation=generation, report=report, segments=segments)

    assert payload["contract_version"] == "career_generation_status_v1"
    assert payload["generation_id"] == str(generation.generation_id)
    assert payload["report_id"] == str(report.id)
    assert payload["deterministic_status"] == "ready"
    assert payload["narrative_status"] == "partial_failure"
    assert payload["progress"] == {"total": 2, "ready": 1, "failed": 1, "running": 0}
    assert payload["sections"][1]["error"] == "career_provider_failure"


def test_progressive_report_exposes_deterministic_data_and_only_ready_sections() -> None:
    from app.modules.career.api_runtime import build_progressive_report_payload

    report = _report(status="generating_sections")
    segments = [
        _segment(report, section_key="professional_summary", status="ready"),
        _segment(report, section_key="work_style", status="generating"),
    ]

    payload = build_progressive_report_payload(report=report, segments=segments)

    assert payload["status"] == "generating_sections"
    assert payload["deterministic_payload"] == report.deterministic_payload
    assert [section["section_key"] for section in payload["sections"]] == ["professional_summary"]
    assert payload["section_states"] == [
        {"section_key": "professional_summary", "status": "ready", "error": None},
        {"section_key": "work_style", "status": "generating", "error": None},
    ]


def test_locked_payload_never_contains_protected_career_data() -> None:
    from app.modules.career.api_runtime import build_locked_career_payload

    payload = build_locked_career_payload(reason="missing_career_access")

    assert payload == {
        "contract_version": "career_locked_v1",
        "access_state": "locked",
        "required_product": "plus",
        "reason": "missing_career_access",
    }
    serialized = repr(payload)
    for protected in ("score", "fact", "section", "answer", "artifact", "report_id"):
        assert protected not in serialized
