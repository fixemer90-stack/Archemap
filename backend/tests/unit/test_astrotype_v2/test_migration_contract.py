"""Migration contract tests for Astrotype v2 database foundation."""

from __future__ import annotations

import re
from pathlib import Path

FORBIDDEN_MUTATION_TARGETS = (
    "users",
    "person_profiles",
    "reports",
    "report_versions",
    "report_narratives",
    "chart_snapshots",
    "billing",
    "payments",
    "subscriptions",
    "entitlements",
)

DESTRUCTIVE_OR_MUTATING_OPS = (
    "op.drop_table",
    "op.drop_column",
    "op.alter_column",
    "op.rename_table",
    "op.execute",
    "op.bulk_insert",
)

EXPECTED_TABLES = (
    "astrotype_v2_aspect_definitions",
    "astrotype_v2_aspect_pair_interpretations",
    "astrotype_v2_natal_charts",
    "astrotype_v2_natal_planet_positions",
    "astrotype_v2_natal_houses",
    "astrotype_v2_natal_aspects",
    "astrotype_v2_natal_chart_balances",
    "astrotype_v2_natal_chart_patterns",
)

ROOT = Path(__file__).resolve().parents[3]


def test_astrotype_v2_models_are_registered_for_metadata() -> None:
    registry = ROOT / "app" / "infrastructure" / "model_registry.py"
    env = ROOT / "alembic" / "env.py"

    assert "astrotype_v2" in registry.read_text()
    assert "astrotype_v2" in env.read_text()


def test_foundation_migration_creates_only_v2_tables() -> None:
    migration_files = sorted((ROOT / "alembic" / "versions").glob("*_add_astrotype_v2_foundation.py"))

    assert len(migration_files) == 1
    migration_text = migration_files[0].read_text()

    for table_name in EXPECTED_TABLES:
        assert re.search(rf'op\.create_table\(\s*["\']{table_name}["\']', migration_text)

    for target in FORBIDDEN_MUTATION_TARGETS:
        for op_name in DESTRUCTIVE_OR_MUTATING_OPS:
            assert f'{op_name}("{target}"' not in migration_text
            assert f"{op_name}('{target}'" not in migration_text


def test_foundation_migration_downgrade_drops_only_v2_tables() -> None:
    migration_files = sorted((ROOT / "alembic" / "versions").glob("*_add_astrotype_v2_foundation.py"))

    assert len(migration_files) == 1
    migration_text = migration_files[0].read_text()

    downgrade_text = migration_text.split("def downgrade()", maxsplit=1)[1]
    for table_name in EXPECTED_TABLES:
        assert f'op.drop_table("{table_name}")' in downgrade_text

    for target in FORBIDDEN_MUTATION_TARGETS:
        assert f'op.drop_table("{target}")' not in downgrade_text
        assert f"op.drop_table('{target}')" not in downgrade_text
