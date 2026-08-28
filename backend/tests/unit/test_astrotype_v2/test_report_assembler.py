"""Contract tests for Astrotype v2 final report assembly."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.schemas import ReportSegmentOutputV2

_BODY_CORE = (
    "Первый развёрнутый абзац ядра личности опирается на evidence ev:sun и сохраняет полный смысл сегмента.\n\n"
    "Второй абзац раскрывает внутренний механизм theme:core:sun без переписывания фактического содержания.\n\n"
    "Третий абзац добавляет нюанс, отделяя техническую основу от верхнего повествования."
)
_BODY_MIND = (
    "Первый развёрнутый абзац мышления опирается на evidence ev:mercury и показывает способ восприятия.\n\n"
    "Второй абзац раскрывает theme:mind:mercury без общего гороскопного текста и без сокращения.\n\n"
    "Третий абзац сохраняет самостоятельный фокус раздела и не дублирует ядро личности."
)


def _segment(
    section_key: str, body: str, theme_id: str, evidence_id: str, status: str = "ready"
) -> models.ReportSegmentGeneration:
    return models.ReportSegmentGeneration(
        chart_id=uuid.uuid4(),
        outline_id=uuid.uuid4(),
        section_key=section_key,
        status=status,
        provider="fake",
        model="fake-model",
        prompt_version="astrotype_v2_segment_v1",
        payload={
            "request": {"section_id": section_key, "owned_themes": [{"id": theme_id}], "evidence_ids": [evidence_id]},
            "request_hash": f"request:{section_key}",
            "prompt_hash": f"prompt:{section_key}",
            "response": ReportSegmentOutputV2(
                section_id=section_key,
                title={"core_pattern": "Ядро личности", "perception_and_mind": "Восприятие и мышление"}.get(
                    section_key, section_key
                ),
                body=body,
                covered_theme_ids=[theme_id],
                evidence_ids=[evidence_id],
            ).model_dump(mode="json"),
            "response_hash": f"response:{section_key}",
        },
        error=None,
    )


def _outline_row(chart_id: uuid.UUID) -> models.ReportOutline:
    return models.ReportOutline(
        chart_id=chart_id,
        status="ready",
        outline={
            "contract_version": "report_outline_v2",
            "source_version": "v2.0",
            "sections": [
                {"id": "core_pattern", "title": "Ядро личности", "owned_theme_ids": ["theme:core:sun"]},
                {
                    "id": "perception_and_mind",
                    "title": "Восприятие и мышление",
                    "owned_theme_ids": ["theme:mind:mercury"],
                },
            ],
        },
        section_keys=["core_pattern", "perception_and_mind"],
        source_version="v2.0",
    )


def _synthesis_row(chart_id: uuid.UUID) -> models.NatalSynthesis:
    return models.NatalSynthesis(
        chart_id=chart_id,
        status="ready",
        facts_version="facts:v1",
        payload={
            "contract_version": "natal_synthesis_v2",
            "input_fact_keys": ["fact:sun", "fact:mercury"],
            "dominant_themes": [
                {"id": "theme:core:sun", "evidence_ids": ["ev:sun"]},
                {"id": "theme:mind:mercury", "evidence_ids": ["ev:mercury"]},
            ],
        },
        source_version="v2.0",
    )


def _infographic_row(chart_id: uuid.UUID) -> models.NatalInfographicData:
    return models.NatalInfographicData(
        chart_id=chart_id,
        status="ready",
        calculation_layer={
            "contract_version": "natal_infographic_data_v2",
            "planet_positions": [{"body": "Sun", "sign": "Aries", "house": 1}],
            "aspect_network": [{"body_a": "Sun", "body_b": "Mercury", "aspect": "conjunction"}],
            "balance_summary": {"elements": {"fire": 0.6}},
        },
        source_version="v2.0",
    )


def test_assemble_natal_report_v2_preserves_validated_segment_text_and_stable_order() -> None:
    from app.modules.astrotype_v2.report_assembler import assemble_natal_report_v2

    chart_id = uuid.uuid4()
    report = assemble_natal_report_v2(
        chart_id=chart_id,
        synthesis_row=_synthesis_row(chart_id),
        outline_row=_outline_row(chart_id),
        infographic_row=_infographic_row(chart_id),
        segment_rows=[
            _segment("perception_and_mind", _BODY_MIND, "theme:mind:mercury", "ev:mercury"),
            _segment("core_pattern", _BODY_CORE, "theme:core:sun", "ev:sun"),
        ],
        version=3,
    )

    assert report.contract_version == "natal_report_v2"
    assert report.chart_id == chart_id
    assert report.version == 3
    assert [section.section_id for section in report.narrative_sections] == ["core_pattern", "perception_and_mind"]
    assert report.narrative_sections[0].body == _BODY_CORE
    assert report.narrative_sections[1].body == _BODY_MIND
    assert report.status == "complete"
    assert report.technical_basis["calculation_layer"]["planet_positions"][0]["body"] == "Sun"


def test_assemble_natal_report_v2_builds_evidence_index_separate_from_narrative_first_sections() -> None:
    from app.modules.astrotype_v2.report_assembler import assemble_natal_report_v2

    chart_id = uuid.uuid4()
    report = assemble_natal_report_v2(
        chart_id=chart_id,
        synthesis_row=_synthesis_row(chart_id),
        outline_row=_outline_row(chart_id),
        infographic_row=_infographic_row(chart_id),
        segment_rows=[
            _segment("core_pattern", _BODY_CORE, "theme:core:sun", "ev:sun"),
            _segment("perception_and_mind", _BODY_MIND, "theme:mind:mercury", "ev:mercury"),
        ],
        version=1,
    )

    assert set(report.evidence_index) == {"ev:sun", "ev:mercury"}
    assert report.evidence_index["ev:sun"]["section_ids"] == ["core_pattern"]
    assert "calculation_layer" not in report.narrative_sections[0].model_dump()
    assert "technical_basis" not in report.narrative_sections[0].body.lower()


def test_assemble_natal_report_v2_rejects_missing_not_ready_or_duplicate_sections() -> None:
    from app.modules.astrotype_v2.report_assembler import ReportAssemblyError, assemble_natal_report_v2

    chart_id = uuid.uuid4()
    synthesis_row = _synthesis_row(chart_id)
    outline_row = _outline_row(chart_id)
    infographic_row = _infographic_row(chart_id)

    with pytest.raises(ReportAssemblyError, match="missing required sections"):
        assemble_natal_report_v2(
            chart_id=chart_id,
            synthesis_row=synthesis_row,
            outline_row=outline_row,
            infographic_row=infographic_row,
            segment_rows=[_segment("core_pattern", _BODY_CORE, "theme:core:sun", "ev:sun")],
            version=1,
        )

    with pytest.raises(ReportAssemblyError, match="not ready"):
        assemble_natal_report_v2(
            chart_id=chart_id,
            synthesis_row=synthesis_row,
            outline_row=outline_row,
            infographic_row=infographic_row,
            segment_rows=[
                _segment("core_pattern", _BODY_CORE, "theme:core:sun", "ev:sun"),
                _segment("perception_and_mind", _BODY_MIND, "theme:mind:mercury", "ev:mercury", status="failed"),
            ],
            version=1,
        )

    with pytest.raises(ReportAssemblyError, match="duplicate section"):
        assemble_natal_report_v2(
            chart_id=chart_id,
            synthesis_row=synthesis_row,
            outline_row=outline_row,
            infographic_row=infographic_row,
            segment_rows=[
                _segment("core_pattern", _BODY_CORE, "theme:core:sun", "ev:sun"),
                _segment("core_pattern", _BODY_CORE, "theme:core:sun", "ev:sun"),
                _segment("perception_and_mind", _BODY_MIND, "theme:mind:mercury", "ev:mercury"),
            ],
            version=1,
        )


def test_assemble_natal_report_v2_quality_gates_reject_repeated_or_ungrounded_sections() -> None:
    from app.modules.astrotype_v2.report_assembler import ReportAssemblyError, assemble_natal_report_v2

    chart_id = uuid.uuid4()
    with pytest.raises(ReportAssemblyError, match="duplicate narrative"):
        assemble_natal_report_v2(
            chart_id=chart_id,
            synthesis_row=_synthesis_row(chart_id),
            outline_row=_outline_row(chart_id),
            infographic_row=_infographic_row(chart_id),
            segment_rows=[
                _segment("core_pattern", _BODY_CORE, "theme:core:sun", "ev:sun"),
                _segment("perception_and_mind", _BODY_CORE, "theme:mind:mercury", "ev:mercury"),
            ],
            version=1,
        )

    with pytest.raises(ReportAssemblyError, match="missing evidence"):
        assemble_natal_report_v2(
            chart_id=chart_id,
            synthesis_row=_synthesis_row(chart_id),
            outline_row=_outline_row(chart_id),
            infographic_row=_infographic_row(chart_id),
            segment_rows=[
                _segment("core_pattern", _BODY_CORE, "theme:core:sun", "ev:sun"),
                _segment("perception_and_mind", _BODY_MIND, "theme:mind:mercury", "ev:unknown"),
            ],
            version=1,
        )


def test_build_deterministic_natal_report_row_exposes_calculation_layer_before_segments() -> None:
    from app.modules.astrotype_v2.report_assembler import build_deterministic_natal_report_row

    chart_id = uuid.uuid4()
    report = build_deterministic_natal_report_row(
        chart_id=chart_id,
        synthesis_row=_synthesis_row(chart_id),
        outline_row=_outline_row(chart_id),
        infographic_row=_infographic_row(chart_id),
        previous_version=2,
    )

    assert report.chart_id == chart_id
    assert report.version == 3
    assert report.status == "deterministic_ready"
    assert report.deterministic_payload["synthesis"]["contract_version"] == "natal_synthesis_v2"
    assert report.deterministic_payload["outline"]["contract_version"] == "report_outline_v2"
    assert (
        report.deterministic_payload["technical_basis"]["calculation_layer"]["contract_version"]
        == "natal_infographic_data_v2"
    )
    assert report.narrative_payload == {"sections": [], "section_order": ["core_pattern", "perception_and_mind"]}
    assert report.assembled_payload["status"] == "deterministic_ready"


def test_build_natal_report_row_versions_without_overwriting_prior_artifacts() -> None:
    from app.modules.astrotype_v2.report_assembler import build_natal_report_row

    chart_id = uuid.uuid4()
    report = build_natal_report_row(
        chart_id=chart_id,
        synthesis_row=_synthesis_row(chart_id),
        outline_row=_outline_row(chart_id),
        infographic_row=_infographic_row(chart_id),
        segment_rows=[
            _segment("core_pattern", _BODY_CORE, "theme:core:sun", "ev:sun"),
            _segment("perception_and_mind", _BODY_MIND, "theme:mind:mercury", "ev:mercury"),
        ],
        previous_version=7,
    )

    assert report.chart_id == chart_id
    assert report.version == 8
    assert report.status == "complete"
    assert report.deterministic_payload["synthesis"]["contract_version"] == "natal_synthesis_v2"
    assert report.narrative_payload["sections"][0]["section_id"] == "core_pattern"
    assert report.assembled_payload["version_lineage"] == {"previous_version": 7, "version": 8}
    assert report.assembled_payload["input_hashes"]["segments"]


def test_report_assembler_source_is_legacy_isolated_and_does_not_import_llm_runtime() -> None:
    source = Path("app/modules/astrotype_v2/report_assembler.py").read_text()

    forbidden_fragments = (
        "report_narratives",
        "socionics",
        "model_a",
        "generate_segment",
        "provider",
        "openai",
        "anthropic",
    )
    for fragment in forbidden_fragments:
        assert fragment not in source
