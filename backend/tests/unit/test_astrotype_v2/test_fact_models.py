"""Contract tests for Astrotype v2 natal fact storage models."""

from __future__ import annotations

from typing import Any, cast

FORBIDDEN_COLUMN_FRAGMENTS = (
    "socionics",
    "function_strength",
    "model_a",
    "narrative_input",
    "archetype",
    "report_narrative",
)


def test_natal_fact_models_use_isolated_v2_tables() -> None:
    from app.modules.astrotype_v2 import models

    assert models.NatalFact.__tablename__ == "astrotype_v2_natal_facts"
    assert models.NatalFactEvidence.__tablename__ == "astrotype_v2_natal_fact_evidence"

    assert cast(Any, models.NatalFact).__table__.name.startswith("astrotype_v2_")
    assert cast(Any, models.NatalFactEvidence).__table__.name.startswith("astrotype_v2_")


def test_natal_fact_model_has_deterministic_report_building_columns() -> None:
    from app.modules.astrotype_v2.models import NatalFact

    column_names = {column.name for column in NatalFact.__table__.columns}

    assert {
        "chart_id",
        "fact_type",
        "fact_key",
        "title",
        "summary",
        "weight",
        "confidence",
        "polarity",
        "section_hint",
        "payload",
        "source_version",
    }.issubset(column_names)

    for column_name in column_names:
        assert not any(fragment in column_name for fragment in FORBIDDEN_COLUMN_FRAGMENTS), (
            f"NatalFact.{column_name} leaks a legacy v1/socionics field"
        )


def test_natal_fact_references_only_v2_chart() -> None:
    from app.modules.astrotype_v2.models import NatalFact

    foreign_key_targets = {str(fk.column) for fk in NatalFact.__table__.foreign_keys}

    assert foreign_key_targets == {"astrotype_v2_natal_charts.id"}
    assert "reports.id" not in foreign_key_targets
    assert "report_versions.id" not in foreign_key_targets
    assert "report_narratives.id" not in foreign_key_targets
    assert "chart_snapshots.id" not in foreign_key_targets


def test_natal_fact_evidence_links_facts_to_deterministic_chart_entities_only() -> None:
    from app.modules.astrotype_v2.models import NatalFactEvidence

    foreign_key_targets = {str(fk.column) for fk in NatalFactEvidence.__table__.foreign_keys}

    assert "astrotype_v2_natal_facts.id" in foreign_key_targets
    assert "astrotype_v2_natal_charts.id" in foreign_key_targets
    assert "reports.id" not in foreign_key_targets
    assert "report_versions.id" not in foreign_key_targets
    assert "report_narratives.id" not in foreign_key_targets
    assert "chart_snapshots.id" not in foreign_key_targets

    column_names = {column.name for column in NatalFactEvidence.__table__.columns}
    assert {"fact_id", "chart_id", "source_table", "source_id", "source_key", "payload"}.issubset(column_names)
    for column_name in column_names:
        assert not any(fragment in column_name for fragment in FORBIDDEN_COLUMN_FRAGMENTS), (
            f"NatalFactEvidence.{column_name} leaks a legacy v1/socionics field"
        )
