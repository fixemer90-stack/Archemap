"""Contract tests for Astrotype v2 database foundation models."""

from __future__ import annotations

FORBIDDEN_COLUMN_FRAGMENTS = (
    "socionics",
    "function_strength",
    "model_a",
    "narrative_input",
    "archetype",
)


def test_astrotype_v2_foundation_models_use_isolated_table_prefix() -> None:
    from app.modules.astrotype_v2 import models

    expected = {
        models.AspectDefinition: "astrotype_v2_aspect_definitions",
        models.AspectPairInterpretation: "astrotype_v2_aspect_pair_interpretations",
        models.NatalChart: "astrotype_v2_natal_charts",
        models.NatalPlanetPosition: "astrotype_v2_natal_planet_positions",
        models.NatalHouse: "astrotype_v2_natal_houses",
        models.NatalAspect: "astrotype_v2_natal_aspects",
        models.NatalChartBalance: "astrotype_v2_natal_chart_balances",
        models.NatalChartPattern: "astrotype_v2_natal_chart_patterns",
    }

    for model, table_name in expected.items():
        assert model.__tablename__ == table_name
        assert model.__table__.name.startswith("astrotype_v2_")


def test_astrotype_v2_foundation_models_do_not_contain_legacy_socionics_fields() -> None:
    from app.modules.astrotype_v2 import models

    model_classes = (
        models.AspectDefinition,
        models.AspectPairInterpretation,
        models.NatalChart,
        models.NatalPlanetPosition,
        models.NatalHouse,
        models.NatalAspect,
        models.NatalChartBalance,
        models.NatalChartPattern,
    )

    for model in model_classes:
        column_names = {column.name for column in model.__table__.columns}
        for column_name in column_names:
            assert not any(fragment in column_name for fragment in FORBIDDEN_COLUMN_FRAGMENTS), (
                f"{model.__name__}.{column_name} leaks a legacy v1/socionics field"
            )


def test_natal_chart_references_platform_user_and_profile_only() -> None:
    from app.modules.astrotype_v2.models import NatalChart

    foreign_key_targets = {str(fk.column) for fk in NatalChart.__table__.foreign_keys}

    assert foreign_key_targets == {"users.id", "person_profiles.id"}


def test_child_chart_rows_reference_only_v2_natal_chart() -> None:
    from app.modules.astrotype_v2 import models

    child_models = (
        models.NatalPlanetPosition,
        models.NatalHouse,
        models.NatalAspect,
        models.NatalChartBalance,
        models.NatalChartPattern,
    )

    for model in child_models:
        foreign_key_targets = {str(fk.column) for fk in model.__table__.foreign_keys}
        assert "astrotype_v2_natal_charts.id" in foreign_key_targets
        assert "reports.id" not in foreign_key_targets
        assert "report_versions.id" not in foreign_key_targets
        assert "report_narratives.id" not in foreign_key_targets
        assert "chart_snapshots.id" not in foreign_key_targets
