"""Migration contract tests for Astrotype v2 fact storage."""

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
    "astrotype_v2_natal_facts",
    "astrotype_v2_natal_fact_evidence",
)

ROOT = Path(__file__).resolve().parents[3]


def _fact_migration_text() -> str:
    migration_files = sorted((ROOT / "alembic" / "versions").glob("*_add_astrotype_v2_fact_storage.py"))

    assert len(migration_files) == 1
    return migration_files[0].read_text()


def test_fact_storage_migration_creates_only_v2_fact_tables() -> None:
    migration_text = _fact_migration_text()

    for table_name in EXPECTED_TABLES:
        assert re.search(rf'op\.create_table\(\s*["\']{table_name}["\']', migration_text)

    for target in FORBIDDEN_MUTATION_TARGETS:
        for op_name in DESTRUCTIVE_OR_MUTATING_OPS:
            assert f'{op_name}("{target}"' not in migration_text
            assert f"{op_name}('{target}'" not in migration_text


def test_fact_storage_migration_downgrade_drops_only_v2_fact_tables() -> None:
    migration_text = _fact_migration_text()
    downgrade_text = migration_text.split("def downgrade()", maxsplit=1)[1]

    for table_name in reversed(EXPECTED_TABLES):
        assert f'op.drop_table("{table_name}")' in downgrade_text

    for target in FORBIDDEN_MUTATION_TARGETS:
        assert f'op.drop_table("{target}")' not in downgrade_text
        assert f"op.drop_table('{target}')" not in downgrade_text
