"""Contract tests for Astrotype v2 chart-row persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.chart_engine.types import Aspect, ChartData, HousePosition, PlanetPosition
from app.modules.astrotype_v2.chart_adapter import build_natal_chart_rows
from app.modules.astrotype_v2.models import NatalChart

ROOT = Path(__file__).resolve().parents[3]

FORBIDDEN_PERSISTENCE_FRAGMENTS = (
    "socionics",
    "function_strength",
    "model_a",
    "report_narrative",
    "chart_snapshots",
    "ChartSnapshot",
)


class _RepositorySpy:
    def __init__(self) -> None:
        self.add = AsyncMock(side_effect=lambda instance: instance)
        self.add_many = AsyncMock(side_effect=lambda instances: instances)
        self.flush = AsyncMock(return_value=None)


def _sample_chart() -> ChartData:
    return ChartData(
        birth_datetime=datetime(1991, 8, 1, 9, 30, tzinfo=UTC),
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        planets=[
            PlanetPosition("Mars", 45.25, 0.1, -0.24, "Taurus", 15.25, 10),
            PlanetPosition("Venus", 165.5, -0.2, 1.1, "Virgo", 15.5, 2),
        ],
        houses=[HousePosition(1, 10.0, "Aries"), HousePosition(10, 280.0, "Capricorn")],
        aspects=[Aspect("Venus", "Mars", "trine", 120.0, 1.5, True)],
        house_system="P",
        ayanamsa=0.0,
    )


@pytest.mark.asyncio
async def test_persist_natal_chart_rows_adds_chart_then_all_child_collections_and_flushes() -> None:
    from app.modules.astrotype_v2.chart_persistence import persist_natal_chart_rows

    repository = _RepositorySpy()
    rows = build_natal_chart_rows(
        chart_data=_sample_chart(),
        user_id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        engine_version="v2-test",
        input_hash="abc123",
    )

    persisted = await persist_natal_chart_rows(repository, rows)

    assert persisted is rows
    repository.add.assert_awaited_once_with(rows.chart)
    assert repository.add.await_args is not None
    assert isinstance(repository.add.await_args.args[0], NatalChart)

    assert repository.add_many.await_count == 5
    persisted_collections = [call.args[0] for call in repository.add_many.await_args_list]
    assert persisted_collections == [
        rows.planet_positions,
        rows.houses,
        rows.aspects,
        rows.balances,
        rows.patterns,
    ]
    for collection in persisted_collections:
        assert collection
        assert all(row.__table__.name.startswith("astrotype_v2_") for row in collection)

    assert repository.flush.await_count == 2


def test_chart_persistence_source_does_not_import_legacy_v1_or_socionics_modules() -> None:
    persistence_path = ROOT / "app" / "modules" / "astrotype_v2" / "chart_persistence.py"
    persistence_text = persistence_path.read_text()

    for fragment in FORBIDDEN_PERSISTENCE_FRAGMENTS:
        assert fragment not in persistence_text
