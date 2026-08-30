"""Worker-runtime regressions for v2 segment partial persistence."""

from __future__ import annotations

import uuid
from typing import Any, cast

import pytest

from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.segment_validation import SegmentValidationError
from app.modules.astrotype_v2.synthesis import NatalSynthesisV2, SynthesisThemeV2


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class _FakeRepository:
    def __init__(self) -> None:
        self.session = _FakeSession()
        self.segments: list[models.ReportSegmentGeneration] = []
        self.generations: dict[uuid.UUID, models.NatalReportGeneration] = {}
        self.flushes = 0

    async def list_segments_for_outline(self, outline_id: uuid.UUID) -> list[models.ReportSegmentGeneration]:
        return [segment for segment in self.segments if segment.outline_id == outline_id]

    async def add_many(self, instances: list[models.ReportSegmentGeneration]) -> list[models.ReportSegmentGeneration]:
        self.segments.extend(instances)
        return instances

    async def flush(self) -> None:
        self.flushes += 1

    async def get_generation(self, generation_id: uuid.UUID) -> models.NatalReportGeneration | None:
        return self.generations.get(generation_id)


def _theme(theme_id: str, section: str, evidence_id: str) -> SynthesisThemeV2:
    return SynthesisThemeV2(
        id=theme_id,
        title=theme_id,
        summary=f"{theme_id} summary",
        primary_section=section,
        fact_keys=(f"fact:{theme_id}",),
        evidence_ids=(evidence_id,),
        weight=1.0,
        confidence=1.0,
        polarity=None,
        fact_type="placement",
    )


def _synthesis(chart_id: uuid.UUID) -> NatalSynthesisV2:
    sections = (
        ("theme:core:sun", "core_pattern", "ev:sun"),
        ("theme:mind:mercury", "perception_and_mind", "ev:mercury"),
        ("theme:emotion:moon", "emotional_regulation", "ev:moon"),
        ("theme:agency:mars", "agency_and_desire", "ev:mars"),
        ("theme:rel:venus", "relationships_and_intimacy", "ev:venus"),
        ("theme:growth:jupiter", "growth_vector", "ev:jupiter"),
    )
    return NatalSynthesisV2(
        chart_id=chart_id,
        source_version="v2.0",
        dominant_themes=tuple(_theme(*item) for item in sections),
        input_fact_keys=[f"fact:{theme_id}" for theme_id, _, _ in sections],
    )


def _outline(chart_id: uuid.UUID) -> models.ReportOutline:
    return models.ReportOutline(
        id=uuid.uuid4(),
        chart_id=chart_id,
        status="ready",
        outline={"contract_version": "report_outline_v2"},
        section_keys=[
            "core_pattern",
            "perception_and_mind",
            "emotional_regulation",
            "agency_and_desire",
            "relationships_and_intimacy",
            "growth_vector",
        ],
        source_version="v2.0",
    )


def _ready_segment(section_key: str, *, chart_id: uuid.UUID, outline_id: uuid.UUID) -> models.ReportSegmentGeneration:
    return models.ReportSegmentGeneration(
        chart_id=chart_id,
        outline_id=outline_id,
        section_key=section_key,
        status="ready",
        provider="fake",
        model="fake-model",
        prompt_version="test",
        payload={"response": {"section_id": section_key}, "response_hash": f"hash:{section_key}"},
        error=None,
    )


@pytest.mark.asyncio
async def test_llm_segments_persist_failed_validation_rows_without_losing_ready_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from workers.tasks import astrotype_v2

    chart_id = uuid.uuid4()
    outline = _outline(chart_id)
    repository = _FakeRepository()
    calls: list[str] = []

    async def fake_run_segment_generation_v2(**kwargs: Any) -> models.ReportSegmentGeneration:
        section_input = kwargs["section_input"]
        calls.append(section_input.section_id)
        if section_input.section_id == "perception_and_mind":
            raise SegmentValidationError("missing depth moves: ['lived manifestation']")
        return _ready_segment(section_input.section_id, chart_id=chart_id, outline_id=outline.id)

    monkeypatch.setattr(astrotype_v2, "get_llm_provider", lambda: object())
    monkeypatch.setattr(astrotype_v2, "run_segment_generation_v2", fake_run_segment_generation_v2)

    segments = await astrotype_v2._ensure_llm_segments(
        repository=cast(Any, repository),
        outline=outline,
        synthesis=_synthesis(chart_id),
        existing_segments=[],
    )

    by_key = {segment.section_key: segment for segment in segments}
    assert calls == [
        "core_pattern",
        "perception_and_mind",
        "emotional_regulation",
        "agency_and_desire",
        "relationships_and_intimacy",
        "growth_vector",
    ]
    assert by_key["core_pattern"].status == "ready"
    assert by_key["perception_and_mind"].status == "failed_validation"
    assert by_key["perception_and_mind"].error == "SegmentValidationError: missing depth moves: ['lived manifestation']"
    assert by_key["perception_and_mind"].payload["error"]["class"] == "SegmentValidationError"
    assert by_key["perception_and_mind"].payload["request"]["section_id"] == "perception_and_mind"
    assert repository.session.commits >= 1


@pytest.mark.asyncio
async def test_worker_generation_status_transition_persists_report_and_diagnostics() -> None:
    from workers.tasks import astrotype_v2

    generation_id = uuid.uuid4()
    report_id = uuid.uuid4()
    repository = _FakeRepository()
    repository.generations[generation_id] = models.NatalReportGeneration(
        generation_id=generation_id,
        user_id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        status="queued",
        diagnostics={"force": True},
    )

    await astrotype_v2._persist_generation_status(
        repository=cast(Any, repository),
        generation_id=generation_id,
        status="partial",
        report_id=report_id,
        diagnostics={"stage": "assembled", "failed_sections": ["perception_and_mind"]},
    )

    generation = repository.generations[generation_id]
    assert generation.status == "partial"
    assert generation.report_id == report_id
    assert generation.diagnostics == {
        "force": True,
        "stage": "assembled",
        "failed_sections": ["perception_and_mind"],
    }
    assert repository.flushes == 1
