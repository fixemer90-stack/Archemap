"""Pure serializers for the async Career API contract."""

from __future__ import annotations

from typing import Any

from app.modules.career.models import CareerGeneration, CareerReport, CareerSegmentGeneration
from app.modules.career.narrative import CAREER_SECTION_ORDER


def build_locked_career_payload(*, reason: str) -> dict[str, str]:
    """Return a locked response with no protected Career fields."""

    return {
        "contract_version": "career_locked_v1",
        "access_state": "locked",
        "required_product": "plus",
        "reason": reason,
    }


def build_generation_status_payload(
    *,
    generation: CareerGeneration,
    report: CareerReport | None,
    segments: list[CareerSegmentGeneration],
) -> dict[str, Any]:
    section_states = _section_states(segments)
    progress = _progress(section_states)
    return {
        "contract_version": "career_generation_status_v1",
        "generation_id": str(generation.generation_id),
        "report_id": str(report.id) if report is not None else None,
        "status": generation.status,
        "deterministic_status": _deterministic_status(generation=generation, report=report),
        "narrative_status": _narrative_status(report=report, progress=progress),
        "progress": progress,
        "sections": section_states,
        "diagnostics": dict(generation.diagnostics),
    }


def build_progressive_report_payload(
    *,
    report: CareerReport,
    segments: list[CareerSegmentGeneration],
) -> dict[str, Any]:
    ordered_segments = _ordered_segments(segments)
    ready_sections = [
        dict(segment.output_payload)
        for segment in ordered_segments
        if segment.status == "ready" and segment.output_payload
    ]
    return {
        "contract_version": "career_report_read_v1",
        "report_id": str(report.id),
        "generation_id": str(report.generation_id),
        "status": report.status,
        "version": report.version,
        "versions": {
            "scoring": report.scoring_version,
            "reference": report.reference_version,
            "questionnaire": report.questionnaire_version,
            "prompt": report.prompt_version,
        },
        "deterministic_payload": dict(report.deterministic_payload),
        "sections": ready_sections,
        "section_states": _section_states(ordered_segments),
        "assembled_payload": dict(report.assembled_payload),
    }


def build_sections_payload(*, segments: list[CareerSegmentGeneration]) -> dict[str, Any]:
    ordered_segments = _ordered_segments(segments)
    return {
        "contract_version": "career_sections_v1",
        "sections": [
            {
                **state,
                "payload": dict(segment.output_payload) if segment.status == "ready" else None,
            }
            for segment, state in zip(ordered_segments, _section_states(ordered_segments), strict=True)
        ],
    }


def _ordered_segments(segments: list[CareerSegmentGeneration]) -> list[CareerSegmentGeneration]:
    order = {section_key: index for index, section_key in enumerate(CAREER_SECTION_ORDER)}
    return sorted(segments, key=lambda segment: (order.get(segment.section_key, len(order)), segment.section_key))


def _section_states(segments: list[CareerSegmentGeneration]) -> list[dict[str, Any]]:
    return [
        {"section_key": segment.section_key, "status": segment.status, "error": segment.error} for segment in segments
    ]


def _progress(section_states: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(section_states),
        "ready": sum(item["status"] == "ready" for item in section_states),
        "failed": sum(item["status"] == "failed" for item in section_states),
        "running": sum(item["status"] in {"pending", "queued", "generating"} for item in section_states),
    }


def _deterministic_status(*, generation: CareerGeneration, report: CareerReport | None) -> str:
    if report is not None:
        return "ready"
    if generation.status == "failed":
        return "failed"
    return "pending"


def _narrative_status(*, report: CareerReport | None, progress: dict[str, int]) -> str:
    if report is None:
        return "pending"
    if report.status == "ready":
        return "ready"
    if progress["failed"] and progress["ready"]:
        return "partial_failure"
    if report.status == "narrative_failed" or progress["failed"]:
        return "failed"
    if progress["ready"] or progress["running"]:
        return "generating"
    return "pending"
