"""Worker-runtime regressions for v2 segment partial persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from types import SimpleNamespace
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("birth_time_accuracy", "profile_birth_time", "expected_proof"),
    [
        (
            "exact",
            time(8, 45),
            {
                "contract_version": "natal-timing-proof-v1",
                "birth_time_confidence": "exact",
                "user_supplied_time": True,
                "synthetic_noon": False,
            },
        ),
        (
            "unknown",
            time(12, 0),
            {
                "contract_version": "natal-timing-proof-v1",
                "birth_time_confidence": "unknown",
                "user_supplied_time": False,
                "synthetic_noon": True,
            },
        ),
        (
            "approximate",
            time(8, 45),
            {
                "contract_version": "natal-timing-proof-v1",
                "birth_time_confidence": "approximate",
                "user_supplied_time": True,
                "synthetic_noon": False,
            },
        ),
    ],
)
async def test_worker_persists_canonical_timing_proof_from_profile_accuracy(
    monkeypatch: pytest.MonkeyPatch,
    birth_time_accuracy: str,
    profile_birth_time: time,
    expected_proof: dict[str, object],
) -> None:
    from app.chart_engine.types import ChartData
    from workers.tasks import astrotype_v2

    class _ChartRepository:
        async def get_chart_by_profile_engine_input(self, **_: object) -> None:
            return None

    profile = SimpleNamespace(
        id=uuid.uuid4(),
        birth_date=date(1990, 1, 1),
        birth_time=profile_birth_time,
        birth_time_accuracy=birth_time_accuracy,
        birth_place="Moscow",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
    )
    chart_data = ChartData(
        birth_datetime=datetime(1990, 1, 1, 5, 45, tzinfo=UTC),
        latitude=profile.latitude,
        longitude=profile.longitude,
        timezone=profile.timezone,
        planets=[],
        houses=[],
        aspects=[],
        house_system="P",
        ayanamsa=0.0,
    )
    monkeypatch.setattr(astrotype_v2, "build_chart", lambda **_: chart_data)

    async def fake_persist(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(astrotype_v2, "persist_natal_chart_rows", fake_persist)

    chart = await astrotype_v2._get_or_create_chart(
        repository=cast(Any, _ChartRepository()),
        profile=cast(Any, profile),
        user_id=uuid.uuid4(),
    )

    assert chart.calculation_payload["birth_time_proof"] == expected_proof


@pytest.mark.asyncio
async def test_worker_does_not_reuse_legacy_pre_provenance_chart_for_same_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.chart_engine.types import ChartData
    from workers.tasks import astrotype_v2

    profile = SimpleNamespace(
        id=uuid.uuid4(),
        birth_date=date(1990, 1, 1),
        birth_time=time(8, 45),
        birth_time_accuracy="exact",
        birth_place="Moscow",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
    )
    legacy_chart = models.NatalChart(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        profile_id=profile.id,
        engine_version="0.1.5",
        input_hash="legacy-input",
        birth_datetime_utc=datetime(1990, 1, 1, 5, 45, tzinfo=UTC),
        timezone=profile.timezone,
        latitude=profile.latitude,
        longitude=profile.longitude,
        house_system="P",
        calculation_payload={},
    )

    class _ChartRepository:
        def __init__(self) -> None:
            self.requested_versions: list[str] = []

        async def get_chart_by_profile_engine_input(self, **kwargs: object) -> models.NatalChart | None:
            engine_version = cast(str, kwargs["engine_version"])
            self.requested_versions.append(engine_version)
            return legacy_chart if engine_version == legacy_chart.engine_version else None

    chart_data = ChartData(
        birth_datetime=datetime(1990, 1, 1, 5, 45, tzinfo=UTC),
        latitude=profile.latitude,
        longitude=profile.longitude,
        timezone=profile.timezone,
        planets=[],
        houses=[],
        aspects=[],
        house_system="P",
        ayanamsa=0.0,
    )
    monkeypatch.setattr(astrotype_v2, "build_chart", lambda **_: chart_data)
    persisted: list[models.NatalChart] = []

    async def fake_persist(_: object, rows: object) -> None:
        persisted.append(cast(Any, rows).chart)

    monkeypatch.setattr(astrotype_v2, "persist_natal_chart_rows", fake_persist)
    repository = _ChartRepository()

    chart = await astrotype_v2._get_or_create_chart(
        repository=cast(Any, repository),
        profile=cast(Any, profile),
        user_id=legacy_chart.user_id,
    )

    assert repository.requested_versions == ["0.1.6"]
    assert chart is persisted[0]
    assert chart.id != legacy_chart.id
    assert chart.engine_version == "0.1.6"
    assert chart.calculation_payload["birth_time_proof"] == {
        "contract_version": "natal-timing-proof-v1",
        "birth_time_confidence": "exact",
        "user_supplied_time": True,
        "synthetic_noon": False,
    }
    assert legacy_chart.calculation_payload == {}
