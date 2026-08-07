"""Contract tests for Astrotype v2 aspect-pair reference examples."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.astrotype_v2 import models

ROOT = Path(__file__).resolve().parents[3]

EXPECTED_PAIR_KEYS = {
    ("sextile", "Mercury", "Saturn", "ru", "v2.0"),
    ("opposition", "Mars", "Uranus", "ru", "v2.0"),
}

FORBIDDEN_REFERENCE_FRAGMENTS = (
    "socionics",
    "function_strength",
    "model_a",
    "report_narrative",
    "chart_snapshots",
    "ChartSnapshot",
)


class _ScalarResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def scalars(self) -> _ScalarResult:
        return self

    def all(self) -> list[object]:
        return self._values

    def scalar_one_or_none(self) -> object | None:
        return self._values[0] if self._values else None


def test_aspect_pair_interpretation_model_has_versioned_enabled_contract() -> None:
    columns = models.AspectPairInterpretation.__table__.columns

    assert "source_version" in columns
    assert "enabled" in columns
    assert columns["enabled"].nullable is False
    index_names = {
        index.name.split("ix_astrotype_v2_aspect_pair_interpretations_")[-1]
        for index in models.AspectPairInterpretation.__table__.indexes
    }
    assert "enabled" in index_names


def test_canonical_aspect_pair_examples_include_required_enabled_rows_once() -> None:
    from app.modules.astrotype_v2.reference_data import CANONICAL_ASPECT_PAIR_INTERPRETATIONS

    examples_by_key = {
        (row.aspect_code, row.planet_a, row.planet_b, row.locale, row.source_version): row
        for row in CANONICAL_ASPECT_PAIR_INTERPRETATIONS
    }

    assert set(examples_by_key) == EXPECTED_PAIR_KEYS
    assert len(CANONICAL_ASPECT_PAIR_INTERPRETATIONS) == len(examples_by_key)
    for row in examples_by_key.values():
        assert row.enabled is True
        assert row.summary
        assert row.keywords


def test_build_aspect_pair_interpretation_rows_returns_v2_orm_rows() -> None:
    from app.modules.astrotype_v2.reference_data import build_aspect_pair_interpretation_rows

    rows = build_aspect_pair_interpretation_rows()

    assert {
        (row.aspect_code, row.planet_a, row.planet_b, row.locale, row.source_version) for row in rows
    } == EXPECTED_PAIR_KEYS
    assert all(isinstance(row, models.AspectPairInterpretation) for row in rows)
    assert all(row.__table__.name == "astrotype_v2_aspect_pair_interpretations" for row in rows)
    assert all(row.enabled is True for row in rows)


@pytest.mark.asyncio
async def test_repository_gets_enabled_pair_interpretation_from_v2_table() -> None:
    from app.modules.astrotype_v2.repository import AstrotypeV2Repository

    interpretation = models.AspectPairInterpretation(
        aspect_code="sextile",
        planet_a="Mercury",
        planet_b="Saturn",
        locale="ru",
        summary="Disciplined thought with practical structure.",
        keywords=["discipline", "thinking"],
        source_version="v2.0",
        enabled=True,
    )
    session = MagicMock()
    session.execute = AsyncMock(return_value=_ScalarResult([interpretation]))
    repository = AstrotypeV2Repository(session)

    assert (
        await repository.get_aspect_pair_interpretation(
            aspect_code="sextile",
            planet_a="Mercury",
            planet_b="Saturn",
            locale="ru",
            source_version="v2.0",
        )
        is interpretation
    )

    statement_text = str(session.execute.await_args.args[0])
    assert "astrotype_v2_aspect_pair_interpretations" in statement_text
    assert "enabled" in statement_text
    assert "chart_snapshots" not in statement_text
    assert "report_narratives" not in statement_text


def test_aspect_pair_enabled_migration_is_additive_and_v2_only() -> None:
    migration_files = sorted((ROOT / "alembic" / "versions").glob("*_add_astrotype_v2_aspect_pair_enabled.py"))

    assert len(migration_files) == 1
    migration_text = migration_files[0].read_text()
    assert 'revision: str = "a3b4c5d6e7f8"' in migration_text
    assert 'down_revision: str | None = "f2a3b4c5d6e7"' in migration_text
    assert "op.add_column(" in migration_text
    assert '"astrotype_v2_aspect_pair_interpretations"' in migration_text
    assert 'sa.Column("enabled", sa.Boolean()' in migration_text
    assert "nullable=False" in migration_text
    assert "server_default=sa.true()" in migration_text
    assert 'op.create_index("ix_astrotype_v2_aspect_pair_interpretations_enabled"' in migration_text

    for fragment in FORBIDDEN_REFERENCE_FRAGMENTS:
        assert fragment not in migration_text


def test_reference_data_source_keeps_pair_examples_inside_v2_boundary() -> None:
    reference_path = ROOT / "app" / "modules" / "astrotype_v2" / "reference_data.py"
    reference_text = reference_path.read_text()

    for fragment in FORBIDDEN_REFERENCE_FRAGMENTS:
        assert fragment not in reference_text
