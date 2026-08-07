"""Contract tests for Astrotype v2 report artifact storage models."""

from __future__ import annotations

FORBIDDEN_COLUMN_FRAGMENTS = (
    "socionics",
    "function_strength",
    "model_a",
    "narrative_input",
    "archetype",
    "report_narrative",
)


def test_report_artifact_models_use_isolated_v2_tables() -> None:
    from app.modules.astrotype_v2 import models

    expected = {
        models.NatalSynthesis: "astrotype_v2_natal_syntheses",
        models.ReportOutline: "astrotype_v2_report_outlines",
        models.ReportSegmentGeneration: "astrotype_v2_report_segment_generations",
        models.NatalInfographicData: "astrotype_v2_natal_infographic_data",
        models.NatalReport: "astrotype_v2_natal_reports",
    }

    for model, table_name in expected.items():
        assert model.__tablename__ == table_name
        assert model.__table__.name.startswith("astrotype_v2_")


def test_report_artifact_models_do_not_contain_legacy_socionics_fields() -> None:
    from app.modules.astrotype_v2 import models

    model_classes = (
        models.NatalSynthesis,
        models.ReportOutline,
        models.ReportSegmentGeneration,
        models.NatalInfographicData,
        models.NatalReport,
    )

    for model in model_classes:
        column_names = {column.name for column in model.__table__.columns}
        for column_name in column_names:
            assert not any(fragment in column_name for fragment in FORBIDDEN_COLUMN_FRAGMENTS), (
                f"{model.__name__}.{column_name} leaks a legacy v1/socionics field"
            )


def test_synthesis_outline_and_infographic_rows_reference_only_v2_chart() -> None:
    from app.modules.astrotype_v2 import models

    for model in (models.NatalSynthesis, models.ReportOutline, models.NatalInfographicData):
        foreign_key_targets = {str(fk.column) for fk in model.__table__.foreign_keys}
        assert foreign_key_targets == {"astrotype_v2_natal_charts.id"}
        assert "reports.id" not in foreign_key_targets
        assert "report_versions.id" not in foreign_key_targets
        assert "report_narratives.id" not in foreign_key_targets
        assert "chart_snapshots.id" not in foreign_key_targets


def test_segment_generation_and_report_reference_only_v2_report_artifacts() -> None:
    from app.modules.astrotype_v2 import models

    segment_targets = {str(fk.column) for fk in models.ReportSegmentGeneration.__table__.foreign_keys}
    assert "astrotype_v2_report_outlines.id" in segment_targets
    assert "astrotype_v2_natal_charts.id" in segment_targets

    report_targets = {str(fk.column) for fk in models.NatalReport.__table__.foreign_keys}
    assert "astrotype_v2_natal_charts.id" in report_targets
    assert "astrotype_v2_natal_syntheses.id" in report_targets
    assert "astrotype_v2_report_outlines.id" in report_targets
    assert "astrotype_v2_natal_infographic_data.id" in report_targets

    for targets in (segment_targets, report_targets):
        assert "reports.id" not in targets
        assert "report_versions.id" not in targets
        assert "report_narratives.id" not in targets
        assert "chart_snapshots.id" not in targets


def test_report_artifact_models_have_progressive_delivery_columns() -> None:
    from app.modules.astrotype_v2 import models

    assert {"chart_id", "status", "facts_version", "payload", "source_version"}.issubset(
        {column.name for column in models.NatalSynthesis.__table__.columns}
    )
    assert {"chart_id", "status", "outline", "section_keys", "source_version"}.issubset(
        {column.name for column in models.ReportOutline.__table__.columns}
    )
    assert {"chart_id", "outline_id", "section_key", "status", "provider", "model", "payload"}.issubset(
        {column.name for column in models.ReportSegmentGeneration.__table__.columns}
    )
    assert {"chart_id", "status", "calculation_layer", "source_version"}.issubset(
        {column.name for column in models.NatalInfographicData.__table__.columns}
    )
    assert {
        "chart_id",
        "synthesis_id",
        "outline_id",
        "infographic_data_id",
        "status",
        "version",
        "deterministic_payload",
        "narrative_payload",
        "assembled_payload",
    }.issubset({column.name for column in models.NatalReport.__table__.columns})
