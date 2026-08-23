"""Contract tests for Astrotype v2 API and async runtime surface."""

from __future__ import annotations

import uuid
from datetime import date, time
from pathlib import Path
from unittest.mock import MagicMock

from app.modules.astrotype_v2 import models

ROOT = Path(__file__).resolve().parents[3]


def _report(chart_id: uuid.UUID) -> models.NatalReport:
    return models.NatalReport(
        id=uuid.uuid4(),
        chart_id=chart_id,
        status="complete",
        version=2,
        deterministic_payload={"synthesis": {"contract_version": "natal_synthesis_v2"}},
        narrative_payload={"sections": [{"section_id": "core_pattern", "body": "Long text"}]},
        assembled_payload={"contract_version": "natal_report_v2", "input_hashes": {"segments": {}}},
    )


def _outline(chart_id: uuid.UUID) -> models.ReportOutline:
    return models.ReportOutline(
        id=uuid.uuid4(),
        chart_id=chart_id,
        status="ready",
        outline={"sections": [{"id": "core_pattern"}, {"id": "perception_and_mind"}]},
        section_keys=["core_pattern", "perception_and_mind"],
        source_version="v2.0",
    )


def _segment(chart_id: uuid.UUID, outline_id: uuid.UUID, key: str, status: str) -> models.ReportSegmentGeneration:
    return models.ReportSegmentGeneration(
        chart_id=chart_id,
        outline_id=outline_id,
        section_key=key,
        status=status,
        provider="fake",
        model="fake-model",
        prompt_version="astrotype_v2_segment_v1",
        payload={"response_hash": f"hash:{key}", "retry_scope": "section_only"},
        error=None if status == "ready" else "provider timeout",
    )


def test_build_generation_accepted_response_enqueues_profile_job_without_running_pipeline_inline() -> None:
    from app.modules.astrotype_v2.api_runtime import build_generation_accepted_response, enqueue_v2_report_generation

    profile_id = uuid.uuid4()
    user_id = uuid.uuid4()
    queue = MagicMock()

    response = enqueue_v2_report_generation(profile_id=profile_id, user_id=user_id, queue=queue, force=False)

    assert response.status_code == 202
    assert response.payload["status"] == "queued"
    assert response.payload["profile_id"] == str(profile_id)
    assert response.payload["generation_id"]
    queue.delay.assert_called_once_with(
        profile_id=str(profile_id),
        user_id=str(user_id),
        generation_id=response.payload["generation_id"],
        force=False,
    )

    accepted = build_generation_accepted_response(
        profile_id=profile_id,
        user_id=user_id,
        generation_id=uuid.UUID(response.payload["generation_id"]),
        force=True,
    )
    assert accepted["force"] is True
    assert accepted["links"]["progress"].startswith("/api/v1/astrotype-v2/reports/generations/")


def test_build_report_progress_v2_exposes_segment_level_state_and_overall_status() -> None:
    from app.modules.astrotype_v2.api_runtime import build_report_progress_v2

    chart_id = uuid.uuid4()
    outline = _outline(chart_id)
    report = _report(chart_id)
    segments = [
        _segment(chart_id, outline.id, "core_pattern", "ready"),
        _segment(chart_id, outline.id, "perception_and_mind", "failed"),
    ]

    progress = build_report_progress_v2(report=report, outline=outline, segments=segments)

    assert progress == {
        "contract_version": "astrotype_v2_report_progress_v1",
        "report_id": str(report.id),
        "chart_id": str(chart_id),
        "status": "failed",
        "total_segments": 2,
        "ready_segments": 1,
        "failed_segments": 1,
        "running_segments": 0,
        "segments": [
            {
                "section_key": "core_pattern",
                "status": "ready",
                "provider": "fake",
                "model": "fake-model",
                "prompt_version": "astrotype_v2_segment_v1",
                "error": None,
            },
            {
                "section_key": "perception_and_mind",
                "status": "failed",
                "provider": "fake",
                "model": "fake-model",
                "prompt_version": "astrotype_v2_segment_v1",
                "error": "provider timeout",
            },
        ],
    }


def test_build_report_read_payload_v2_includes_report_facts_infographics_segments() -> None:
    from app.modules.astrotype_v2.api_runtime import build_report_read_payload_v2

    chart_id = uuid.uuid4()
    report = _report(chart_id)
    outline = _outline(chart_id)
    infographic = models.NatalInfographicData(
        chart_id=chart_id,
        status="ready",
        calculation_layer={"contract_version": "natal_infographic_data_v2", "planet_positions": []},
        source_version="v2.0",
    )
    facts = [
        {
            "fact_key": "placement:sun:aries:house_1",
            "title": "Sun in Aries",
            "evidence": [],
        }
    ]
    profile = MagicMock()
    profile.id = uuid.uuid4()
    profile.name = "Алина"
    profile.birth_date = date(1991, 8, 1)
    profile.birth_time = time(9, 30)
    profile.birth_time_accuracy = "exact"
    profile.birth_place = "Москва, Россия"
    profile.timezone = "Europe/Moscow"
    profile.latitude = 55.7558
    profile.longitude = 37.6173
    segments = [_segment(chart_id, outline.id, "core_pattern", "ready")]

    payload = build_report_read_payload_v2(
        report=report,
        outline=outline,
        infographic=infographic,
        facts=facts,
        segments=segments,
        profile=profile,
    )

    assert payload["contract_version"] == "astrotype_v2_report_api_v1"
    assert payload["report"]["assembled_payload"]["contract_version"] == "natal_report_v2"
    assert payload["infographic"]["calculation_layer"]["contract_version"] == "natal_infographic_data_v2"
    assert payload["facts"] == facts
    assert payload["segments"][0]["section_key"] == "core_pattern"
    assert payload["profile"] == {
        "id": str(profile.id),
        "name": "Алина",
        "birth_date": "1991-08-01",
        "birth_time": "09:30:00",
        "birth_time_accuracy": "exact",
        "birth_place": "Москва, Россия",
        "timezone": "Europe/Moscow",
        "latitude": 55.7558,
        "longitude": 37.6173,
    }
    assert "socionics" not in str(payload).lower()


def test_v2_report_payload_exposes_canonical_reader_hero_and_narrative_contract() -> None:
    from app.modules.astrotype_v2.qa_smoke import build_smoke_report_bundle_v2

    payload = build_smoke_report_bundle_v2()["report_payload"]
    assembled = payload["report"]["assembled_payload"]
    narrative = payload["report"]["narrative_payload"]

    assert assembled["reader_view"]["hero"] == {
        "eyebrow": "Astrotype v2 · натальный отчёт",
        "title": "Натальный портрет личности",
        "status_label": "Полный отчёт готов",
        "calculation_label": "Карта и расчёт ниже",
        "pdf_label": "Предпросмотр PDF",
    }
    assert assembled["reader_view"]["layout_order"] == ["hero", "narrative", "calculation_layer"]
    assert narrative["section_order"] == [
        "core_pattern",
        "perception_and_mind",
        "emotional_regulation",
        "agency_and_desire",
        "relationships_and_intimacy",
        "growth_vector",
    ]
    for index, section in enumerate(narrative["sections"], start=1):
        assert section["reader_display"]["eyebrow"].startswith(f"{index:02d} · ")
        assert section["reader_display"]["subtitle"]
        assert section["reader_display"]["aside_title"]
        assert section["reader_display"]["aside_bullets"]


def test_v2_infographic_payload_exposes_canonical_calculation_layer_contract() -> None:
    from app.modules.astrotype_v2.qa_smoke import build_smoke_report_bundle_v2

    calculation_layer = build_smoke_report_bundle_v2()["report_payload"]["infographic"]["calculation_layer"]

    assert calculation_layer["reader_blocks"] == [
        "key_indicators",
        "planet_positions",
        "balance_bars",
        "house_emphasis",
        "aspect_network",
        "key_aspects",
        "calculation_matrix",
    ]
    assert set(calculation_layer["key_indicators"]) >= {"ascendant", "mc", "ascendant_ruler"}
    assert calculation_layer["planet_positions"][0].keys() >= {
        "body",
        "sign",
        "house_number",
        "sign_degree",
        "degree_label",
        "retrograde",
        "sampled_aspects",
    }
    assert set(calculation_layer["balance_bars"]) >= {"elements", "modalities"}
    assert len(calculation_layer["house_emphasis"]["bars"]) == 12
    assert calculation_layer["house_emphasis"]["top_houses"]
    assert calculation_layer["aspect_network"]["nodes"]
    assert calculation_layer["aspect_network"]["edges"]
    assert calculation_layer["key_aspects"]
    assert set(calculation_layer["calculation_matrix"]) >= {
        "house_mode",
        "hemispheres",
        "quadrants",
        "aspect_profile",
    }


def test_router_is_registered_with_authenticated_multi_client_endpoints() -> None:
    api_init = (ROOT / "app" / "api" / "v1" / "__init__.py").read_text()
    router_source = (ROOT / "app" / "modules" / "astrotype_v2" / "router.py").read_text()

    assert "astrotype_v2_router" in api_init
    assert "api_router.include_router(astrotype_v2_router)" in api_init
    for marker in [
        'prefix="/astrotype-v2"',
        '@router.post("/reports"',
        '@router.get("/reports/generations/{generation_id}"',
        '@router.get("/reports/{report_id}"',
        '@router.get("/reports/{report_id}/progress"',
        '@router.get("/reports/{report_id}/facts"',
        '@router.get("/reports/{report_id}/infographic"',
        '@router.get("/reports/{report_id}/segments"',
        '@router.post("/reports/{report_id}/regenerate"',
        "Depends(get_current_user)",
    ]:
        assert marker in router_source


def test_repository_ownership_queries_join_v2_chart_user_and_profile() -> None:
    source = (ROOT / "app" / "modules" / "astrotype_v2" / "repository.py").read_text()

    for marker in [
        "get_report_for_user",
        "get_latest_report_for_profile",
        "models.NatalChart.user_id == user_id",
        "models.NatalChart.profile_id == profile_id",
        ".join(models.NatalChart",
    ]:
        assert marker in source


def test_deterministic_worker_core_segment_is_reader_prose_not_raw_fact_dump() -> None:
    from app.modules.astrotype_v2.outline import build_report_outline_v2
    from app.modules.astrotype_v2.synthesis import NatalSynthesisV2, SynthesisThemeV2
    from workers.tasks.astrotype_v2 import _segment_output

    chart_id = uuid.uuid4()
    themes = (
        SynthesisThemeV2(
            id="theme:placement:asc",
            title="Ascendant in Gemini, house 1",
            summary="Ascendant is in Gemini in house 1.",
            primary_section="core_pattern",
            fact_keys=("placement:ascendant:gemini:house_1",),
            evidence_ids=("fact:asc",),
            weight=1.0,
            confidence=1.0,
        ),
        SynthesisThemeV2(
            id="theme:placement:sun",
            title="Sun in Taurus, house 12",
            summary="Sun is in Taurus in house 12.",
            primary_section="core_pattern",
            fact_keys=("placement:sun:taurus:house_12",),
            evidence_ids=("fact:sun",),
            weight=1.0,
            confidence=1.0,
        ),
        SynthesisThemeV2(
            id="theme:aspect:moon_mercury",
            title="Moon sextile Mercury",
            summary="Moon sextile Mercury with orb 0.1°.",
            primary_section="core_pattern",
            fact_keys=("aspect:moon:mercury:sextile",),
            evidence_ids=("fact:aspect",),
            weight=0.99,
            confidence=1.0,
        ),
    )
    synthesis = NatalSynthesisV2(chart_id=chart_id, source_version="v2.0", dominant_themes=themes)
    section = build_report_outline_v2(synthesis=synthesis).to_payload()["sections"][0]

    output = _segment_output(section=section, synthesis=synthesis)

    assert output.section_id == "core_pattern"
    assert output.title == "Ядро личности"
    assert "Ядро личности:" not in output.body
    assert "Ascendant is in" not in output.body
    assert "with orb" not in output.body
    assert "Асцендент в Близнецах в 1 доме" in output.body
    assert "Солнце в Тельце в 12 доме" in output.body
    assert "Луна секстиль Меркурий" in output.body
    assert len(output.body.split("\n\n")) >= 3


def test_worker_task_is_registered_but_runtime_module_does_not_import_legacy_pipeline() -> None:
    task_source = (ROOT / "workers" / "tasks" / "astrotype_v2.py").read_text()
    runtime_source = (ROOT / "app" / "modules" / "astrotype_v2" / "api_runtime.py").read_text()

    assert '@app.task(name="astrotype_v2.generate_natal_report"' in task_source
    assert "def generate_natal_report_v2" in task_source
    assert "run_async_in_worker" in task_source
    assert "build_natal_chart_rows" in task_source
    assert "build_natal_report_row" in task_source
    for fragment in ("report_narratives", "socionics", "model_a", "function_strength"):
        assert fragment not in runtime_source
