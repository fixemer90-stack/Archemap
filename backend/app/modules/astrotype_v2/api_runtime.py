"""API payload and queue helpers for Astrotype v2 report runtime."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from app.modules.astrotype_v2 import models

PROGRESS_CONTRACT_VERSION = "astrotype_v2_report_progress_v1"
REPORT_API_CONTRACT_VERSION = "astrotype_v2_report_api_v1"


class SupportsDelay(Protocol):
    """Queue task object exposing Celery-like delay."""

    def delay(self, **kwargs: str | bool) -> object:
        """Enqueue work and return a backend-specific task handle."""


@dataclass(frozen=True)
class EnqueuedGenerationResponse:
    """Accepted async generation response plus HTTP status metadata."""

    payload: dict[str, Any]
    status_code: int = 202


def build_generation_accepted_response(
    *,
    profile_id: uuid.UUID,
    user_id: uuid.UUID,
    generation_id: uuid.UUID,
    force: bool,
) -> dict[str, Any]:
    """Build multi-client response for queued v2 report generation."""

    generation_id_text = str(generation_id)
    return {
        "contract_version": "astrotype_v2_generation_job_v1",
        "generation_id": generation_id_text,
        "profile_id": str(profile_id),
        "user_id": str(user_id),
        "status": "queued",
        "force": force,
        "links": {
            "progress": f"/api/v1/astrotype-v2/reports/generations/{generation_id_text}",
        },
    }


def enqueue_v2_report_generation(
    *,
    profile_id: uuid.UUID,
    user_id: uuid.UUID,
    queue: SupportsDelay,
    force: bool,
) -> EnqueuedGenerationResponse:
    """Enqueue v2 generation without running the long pipeline in the request."""

    generation_id = uuid.uuid4()
    payload = build_generation_accepted_response(
        profile_id=profile_id,
        user_id=user_id,
        generation_id=generation_id,
        force=force,
    )
    queue.delay(
        profile_id=str(profile_id),
        user_id=str(user_id),
        generation_id=payload["generation_id"],
        force=force,
    )
    return EnqueuedGenerationResponse(payload=payload)


def build_report_progress_v2(
    *,
    report: models.NatalReport,
    outline: models.ReportOutline | None,
    segments: list[models.ReportSegmentGeneration],
) -> dict[str, Any]:
    """Build segment-level progress for polling clients."""

    segment_items = [_segment_progress(segment) for segment in _ordered_segments(outline=outline, segments=segments)]
    failed_segments = sum(1 for segment in segment_items if segment["status"] == "failed")
    ready_segments = sum(1 for segment in segment_items if segment["status"] == "ready")
    running_segments = sum(1 for segment in segment_items if segment["status"] in {"queued", "running", "pending"})
    status = _overall_status(report=report, failed_segments=failed_segments, running_segments=running_segments)
    return {
        "contract_version": PROGRESS_CONTRACT_VERSION,
        "report_id": str(report.id),
        "chart_id": str(report.chart_id),
        "status": status,
        "total_segments": len(segment_items),
        "ready_segments": ready_segments,
        "failed_segments": failed_segments,
        "running_segments": running_segments,
        "segments": segment_items,
    }


def build_report_read_payload_v2(
    *,
    report: models.NatalReport,
    outline: models.ReportOutline | None,
    infographic: models.NatalInfographicData | None,
    facts: list[dict[str, Any]],
    segments: list[models.ReportSegmentGeneration],
) -> dict[str, Any]:
    """Build full v2 report API payload for web/mobile clients."""

    return {
        "contract_version": REPORT_API_CONTRACT_VERSION,
        "report": _report_payload(report),
        "progress": build_report_progress_v2(report=report, outline=outline, segments=segments),
        "outline": outline.outline if outline is not None else None,
        "infographic": _infographic_payload(infographic),
        "facts": facts,
        "segments": [_segment_payload(segment) for segment in _ordered_segments(outline=outline, segments=segments)],
    }


def build_generation_status_payload(*, generation_id: uuid.UUID) -> dict[str, Any]:
    """Return status for an accepted generation id before a report row exists."""

    return {
        "contract_version": "astrotype_v2_generation_status_v1",
        "generation_id": str(generation_id),
        "status": "queued_or_running",
    }


def _overall_status(*, report: models.NatalReport, failed_segments: int, running_segments: int) -> str:
    if failed_segments:
        return "failed"
    if report.status in {"complete", "ready"}:
        return "ready"
    if running_segments:
        return "running"
    return report.status


def _ordered_segments(
    *,
    outline: models.ReportOutline | None,
    segments: list[models.ReportSegmentGeneration],
) -> list[models.ReportSegmentGeneration]:
    by_key = {segment.section_key: segment for segment in segments}
    if outline is None or not outline.section_keys:
        return sorted(segments, key=lambda segment: segment.section_key)
    ordered = [by_key[key] for key in outline.section_keys if key in by_key]
    extras = sorted(
        (segment for segment in segments if segment.section_key not in outline.section_keys),
        key=lambda item: item.section_key,
    )
    return ordered + extras


def _segment_progress(segment: models.ReportSegmentGeneration) -> dict[str, Any]:
    return {
        "section_key": segment.section_key,
        "status": segment.status,
        "provider": segment.provider,
        "model": segment.model,
        "prompt_version": segment.prompt_version,
        "error": segment.error,
    }


def _segment_payload(segment: models.ReportSegmentGeneration) -> dict[str, Any]:
    return {
        **_segment_progress(segment),
        "payload": segment.payload,
    }


def _report_payload(report: models.NatalReport) -> dict[str, Any]:
    return {
        "id": str(report.id),
        "chart_id": str(report.chart_id),
        "status": report.status,
        "version": report.version,
        "deterministic_payload": report.deterministic_payload,
        "narrative_payload": report.narrative_payload,
        "assembled_payload": report.assembled_payload,
    }


def _infographic_payload(infographic: models.NatalInfographicData | None) -> dict[str, Any] | None:
    if infographic is None:
        return None
    return {
        "id": str(infographic.id),
        "status": infographic.status,
        "source_version": infographic.source_version,
        "calculation_layer": infographic.calculation_layer,
    }
