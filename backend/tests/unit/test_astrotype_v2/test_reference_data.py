"""Contract tests for Astrotype v2 reference data."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.astrotype_v2 import models

ROOT = Path(__file__).resolve().parents[3]

FORBIDDEN_REFERENCE_FRAGMENTS = (
    "socionics",
    "function_strength",
    "model_a",
    "report_narrative",
    "chart_snapshots",
    "ChartSnapshot",
)

EXPECTED_MAJOR_ASPECTS = {
    "conjunction": (0.0, 8.0, True),
    "sextile": (60.0, 4.0, True),
    "square": (90.0, 6.0, True),
    "trine": (120.0, 6.0, True),
    "opposition": (180.0, 8.0, True),
    "quincunx": (150.0, 3.0, False),
}


class _ScalarResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def scalars(self) -> _ScalarResult:
        return self

    def all(self) -> list[object]:
        return self._values

    def scalar_one_or_none(self) -> object | None:
        return self._values[0] if self._values else None


def test_canonical_aspect_definitions_include_v2_required_aspects_once() -> None:
    from app.modules.astrotype_v2.reference_data import CANONICAL_ASPECT_DEFINITIONS

    definitions_by_code = {definition.code: definition for definition in CANONICAL_ASPECT_DEFINITIONS}

    assert set(definitions_by_code) == set(EXPECTED_MAJOR_ASPECTS)
    assert len(CANONICAL_ASPECT_DEFINITIONS) == len(definitions_by_code)

    for code, (angle, orb, major) in EXPECTED_MAJOR_ASPECTS.items():
        definition = definitions_by_code[code]
        assert definition.angle_degrees == angle
        assert definition.default_orb_degrees == orb
        assert definition.major is major
        assert definition.name
        assert definition.description
        assert definition.sort_order >= 0


def test_build_aspect_definition_rows_returns_v2_orm_rows_without_duplicates() -> None:
    from app.modules.astrotype_v2.reference_data import build_aspect_definition_rows

    rows = build_aspect_definition_rows()

    assert {row.code for row in rows} == set(EXPECTED_MAJOR_ASPECTS)
    assert all(isinstance(row, models.AspectDefinition) for row in rows)
    assert all(cast(Any, row).__table__.name == "astrotype_v2_aspect_definitions" for row in rows)
    assert len({row.code for row in rows}) == len(rows)


@pytest.mark.asyncio
async def test_repository_lists_and_gets_aspect_definitions_from_v2_table() -> None:
    from app.modules.astrotype_v2.repository import AstrotypeV2Repository

    conjunction = models.AspectDefinition(
        code="conjunction",
        name="Conjunction",
        angle_degrees=0.0,
        default_orb_degrees=8.0,
        major=True,
        sort_order=10,
        description="Merged emphasis.",
    )
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[_ScalarResult([conjunction]), _ScalarResult([conjunction])])
    repository = AstrotypeV2Repository(session)

    assert await repository.list_aspect_definitions() == [conjunction]
    assert await repository.get_aspect_definition("conjunction") is conjunction

    statement_text = "\n".join(str(call.args[0]) for call in session.execute.await_args_list)
    assert "astrotype_v2_aspect_definitions" in statement_text
    assert "chart_snapshots" not in statement_text
    assert "report_narratives" not in statement_text


def test_reference_data_source_does_not_import_legacy_v1_or_typology_modules() -> None:
    reference_path = ROOT / "app" / "modules" / "astrotype_v2" / "reference_data.py"
    reference_text = reference_path.read_text()

    for fragment in FORBIDDEN_REFERENCE_FRAGMENTS:
        assert fragment not in reference_text
