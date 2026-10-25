"""Native mock regressions at the real Self v2 structured-provider boundary."""

from __future__ import annotations

import socket
import uuid
from datetime import UTC, datetime, time

import pytest
from pydantic import BaseModel

from app.chart_engine.chart import build_chart
from app.config import Settings
from app.modules.astrotype_v2.chart_adapter import NatalTimingProvenance, build_natal_chart_rows
from app.modules.astrotype_v2.fact_extractor import build_balance_pattern_fact_rows, build_placement_fact_rows
from app.modules.astrotype_v2.llm_segments import StructuredSegmentProviderAdapter, run_segment_generation_v2
from app.modules.astrotype_v2.outline import build_report_outline_v2
from app.modules.astrotype_v2.schemas import ReportSegmentOutputV2, SectionRenderInputV2
from app.modules.astrotype_v2.segment_inputs import build_section_render_inputs_v2
from app.modules.astrotype_v2.segment_validation import validate_segment_output_v2
from app.modules.astrotype_v2.synthesis import build_natal_synthesis_v2
from app.modules.llm.provider import get_llm_provider
from app.modules.llm.providers.mock import MockLLMProvider


@pytest.fixture
def canonical_inputs() -> list[SectionRenderInputV2]:
    # Existing reference profile: 1991-08-29 15:30 Moscow (11:30 UTC).
    chart = build_chart(
        birth_datetime=datetime(1991, 8, 29, 11, 30, tzinfo=UTC),
        latitude=55.7505412,
        longitude=37.6174782,
        timezone_name="Europe/Moscow",
    )
    rows = build_natal_chart_rows(
        chart_data=chart,
        user_id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        engine_version="0.1.6",
        input_hash="native-mock-self-v2-regression",
        timing_provenance=NatalTimingProvenance(birth_time_accuracy="exact", birth_time=time(15, 30)),
    )
    placements, _ = build_placement_fact_rows(chart_id=rows.chart.id, positions=rows.planet_positions)
    balances, _ = build_balance_pattern_fact_rows(
        chart_id=rows.chart.id, balances=rows.balances, patterns=rows.patterns
    )
    synthesis = build_natal_synthesis_v2(chart_id=rows.chart.id, facts=[*placements, *balances])
    outline = build_report_outline_v2(synthesis=synthesis)
    return build_section_render_inputs_v2(outline=outline, synthesis=synthesis)


def _no_network(*args: object, **kwargs: object) -> None:
    pytest.fail("native mock attempted network access")


@pytest.mark.parametrize("environment", ["development", "staging"])
@pytest.mark.parametrize("section_index", range(6))
async def test_native_mock_completes_real_v2_segment_with_only_input_grounding(
    canonical_inputs: list[SectionRenderInputV2], monkeypatch: pytest.MonkeyPatch, section_index: int, environment: str
) -> None:
    monkeypatch.setattr(socket, "create_connection", _no_network)
    monkeypatch.setattr(socket.socket, "connect", _no_network)
    config = Settings(
        APP_ENV=environment, LLM_ENABLED=True, LLM_PROVIDER="mock", LLM_MODEL="mock-self-v1", LLM_API_KEY=""
    )
    provider = StructuredSegmentProviderAdapter(
        provider=get_llm_provider(config), provider_name=config.LLM_PROVIDER, model_name=config.LLM_MODEL
    )
    assert len(canonical_inputs) == 6
    section_input = canonical_inputs[section_index]
    original = section_input.to_payload()
    segment = await run_segment_generation_v2(provider=provider, section_input=section_input, outline_id=uuid.uuid4())
    assert segment.status == "ready"
    assert segment.error is None
    assert (segment.provider, segment.model) == ("mock", "mock-self-v1")
    output = ReportSegmentOutputV2.model_validate(segment.payload["response"])
    assert validate_segment_output_v2(output=output, section_input=section_input) == output
    assert output.section_id == section_input.section_id
    assert output.title == section_input.section_title
    assert "Демонстрационный текст локального mock-провайдера" in output.body
    assert "not real-provider quality evidence" in output.notes[0]
    assert output.evidence_ids == section_input.evidence_ids
    assert output.covered_theme_ids == [theme.id for theme in section_input.owned_themes]
    assert not set(output.covered_theme_ids) & set(section_input.forbidden_theme_ids)
    assert output.continuation_complete is True
    assert section_input.to_payload() == original
    repeated = await run_segment_generation_v2(provider=provider, section_input=section_input, outline_id=uuid.uuid4())
    assert repeated.payload == segment.payload


def _thin_input(section: SectionRenderInputV2) -> SectionRenderInputV2:
    payload = section.to_payload()
    for theme in [*payload["owned_themes"], *payload["reference_themes"]]:
        for field in (
            "psychological_mechanism",
            "lived_manifestation",
            "inner_tension",
            "protective_strategy",
            "immature_expression",
            "mature_expression",
            "integration_question",
        ):
            theme.pop(field, None)
    return SectionRenderInputV2.model_validate(payload)


@pytest.mark.parametrize("section_index", range(6))
async def test_native_mock_accepts_cached_themes_without_optional_depth_fields(
    canonical_inputs: list[SectionRenderInputV2], monkeypatch: pytest.MonkeyPatch, section_index: int
) -> None:
    monkeypatch.setattr(socket, "create_connection", _no_network)
    monkeypatch.setattr(socket.socket, "connect", _no_network)
    section = _thin_input(canonical_inputs[section_index])
    config = Settings(APP_ENV="staging", LLM_ENABLED=True, LLM_PROVIDER="mock")
    provider = StructuredSegmentProviderAdapter(
        provider=get_llm_provider(config), provider_name="mock", model_name="mock-self-v1"
    )
    segment = await run_segment_generation_v2(provider=provider, section_input=section, outline_id=uuid.uuid4())
    assert segment.status == "ready"
    output = ReportSegmentOutputV2.model_validate(segment.payload["response"])
    assert validate_segment_output_v2(output=output, section_input=section) == output
    assert output.evidence_ids == section.evidence_ids
    assert output.covered_theme_ids == [theme.id for theme in section.owned_themes]
    assert "Демонстрационный текст локального mock-провайдера" in output.body
    assert "not real-provider quality evidence" in output.notes[0]


async def test_native_mock_assembles_all_thin_cached_sections_without_duplicate_bodies(
    canonical_inputs: list[SectionRenderInputV2], monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.modules.astrotype_v2 import models
    from app.modules.astrotype_v2.report_assembler import assemble_natal_report_v2

    monkeypatch.setattr(socket, "create_connection", _no_network)
    monkeypatch.setattr(socket.socket, "connect", _no_network)
    inputs = [_thin_input(section) for section in canonical_inputs]
    chart_id, outline_id = inputs[0].chart_id, uuid.uuid4()
    provider = StructuredSegmentProviderAdapter(
        provider=get_llm_provider(Settings(APP_ENV="staging", LLM_ENABLED=True, LLM_PROVIDER="mock")),
        provider_name="mock",
        model_name="mock-self-v1",
    )
    segments = [
        await run_segment_generation_v2(provider=provider, section_input=s, outline_id=outline_id) for s in inputs
    ]
    report = assemble_natal_report_v2(
        chart_id=chart_id,
        synthesis_row=models.NatalSynthesis(
            chart_id=chart_id,
            facts_version="facts:v2.0",
            source_version="v2.0",
            payload={"dominant_themes": [t.model_dump(mode="json") for s in inputs for t in s.owned_themes]},
        ),
        outline_row=models.ReportOutline(
            id=outline_id,
            chart_id=chart_id,
            section_keys=[s.section_id for s in inputs],
            outline={"sections": [{"id": s.section_id, "title": s.section_title} for s in inputs]},
            source_version="v2.0",
        ),
        infographic_row=models.NatalInfographicData(chart_id=chart_id, calculation_layer={}, source_version="v2.0"),
        segment_rows=segments,
        version=1,
    )
    assert report.status == "complete"
    assert len(report.narrative_sections) == 6
    assert len({" ".join(s.body.lower().split()) for s in report.narrative_sections}) == 6
    assert set(report.evidence_index) == {e for s in inputs for e in s.evidence_ids}


async def test_native_mock_rejects_incompatible_v2_schema(canonical_inputs: list[SectionRenderInputV2]) -> None:
    with pytest.raises(TypeError, match="segment output contract"):
        await MockLLMProvider().generate_structured(prompt="", narrative_input=canonical_inputs[0], schema=BaseModel)


async def test_native_mock_body_excludes_reference_only_content(canonical_inputs: list[SectionRenderInputV2]) -> None:
    section = canonical_inputs[0]
    sentinel = "REFERENCE_ONLY_CONTENT_MUST_NOT_APPEAR"
    fields = (
        "title",
        "summary",
        "psychological_mechanism",
        "lived_manifestation",
        "inner_tension",
        "protective_strategy",
        "immature_expression",
        "mature_expression",
        "integration_question",
    )
    reference = section.owned_themes[0].model_copy(
        update={
            **dict.fromkeys(fields, sentinel),
            "id": "reference-only-theme",
            "evidence_ids": ["reference-only-evidence"],
        }
    )
    modified = section.model_copy(update={"reference_themes": [reference]})
    output = await MockLLMProvider().generate_structured(
        prompt=sentinel, narrative_input=modified, schema=ReportSegmentOutputV2
    )
    assert sentinel not in output.body
    assert output.evidence_ids == section.evidence_ids
    assert "reference-only-theme" not in output.covered_theme_ids
    assert "reference-only-evidence" not in output.evidence_ids


async def test_production_factory_cannot_publish_native_v2_mock(
    canonical_inputs: list[SectionRenderInputV2],
) -> None:
    config = Settings(LLM_ENABLED=True, LLM_PROVIDER="mock").model_copy(update={"APP_ENV": "production"})
    provider = StructuredSegmentProviderAdapter(
        provider=get_llm_provider(config), provider_name="mock", model_name="mock-self-v1"
    )
    with pytest.raises(ValueError, match="production"):
        await run_segment_generation_v2(provider=provider, section_input=canonical_inputs[0], outline_id=uuid.uuid4())
