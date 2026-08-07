"""Contract tests for reloading Astrotype v2 chart rows into stable contracts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.astrotype_v2 import models

ROOT = Path(__file__).resolve().parents[3]

FORBIDDEN_CONTRACT_FRAGMENTS = (
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


class _RepositoryStub:
    def __init__(self, chart_id: uuid.UUID) -> None:
        self.chart = models.NatalChart(
            id=chart_id,
            user_id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            engine_version="v2-test",
            input_hash="abc123",
            birth_datetime_utc=datetime(1991, 8, 1, 9, 30, tzinfo=UTC),
            timezone="Europe/Moscow",
            latitude=55.7558,
            longitude=37.6173,
            house_system="P",
            calculation_payload={"ayanamsa": 0.0},
        )
        self.positions = [
            models.NatalPlanetPosition(
                chart_id=chart_id,
                body="Mars",
                longitude=45.25,
                latitude=0.1,
                speed=-0.24,
                sign="Taurus",
                sign_degree=15.25,
                house_number=10,
                retrograde=True,
            )
        ]
        self.houses = [models.NatalHouse(chart_id=chart_id, house_number=10, longitude=280.0, sign="Capricorn")]
        self.aspects = [
            models.NatalAspect(
                chart_id=chart_id,
                body_a="Venus",
                body_b="Mars",
                aspect_code="trine",
                angle_degrees=120.0,
                orb_degrees=1.5,
                applying=True,
                strength=0.875,
            )
        ]
        self.balances = [
            models.NatalChartBalance(chart_id=chart_id, category="element", key="earth", value=1.0, rank=1)
        ]
        self.patterns = [
            models.NatalChartPattern(
                chart_id=chart_id,
                pattern_code="emphasis_element_earth",
                label="element emphasis: earth",
                weight=1.0,
                evidence={"category": "element", "key": "earth", "value": 1.0},
            )
        ]

    async def get_chart(self, chart_id: uuid.UUID) -> models.NatalChart | None:
        return self.chart if chart_id == self.chart.id else None

    async def list_planet_positions_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalPlanetPosition]:
        return self.positions if chart_id == self.chart.id else []

    async def list_houses_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalHouse]:
        return self.houses if chart_id == self.chart.id else []

    async def list_aspects_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalAspect]:
        return self.aspects if chart_id == self.chart.id else []

    async def list_balances_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalChartBalance]:
        return self.balances if chart_id == self.chart.id else []

    async def list_patterns_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalChartPattern]:
        return self.patterns if chart_id == self.chart.id else []


@pytest.mark.asyncio
async def test_repository_lists_v2_chart_child_rows_by_chart_id() -> None:
    from app.modules.astrotype_v2.repository import AstrotypeV2Repository

    chart_id = uuid.uuid4()
    session = MagicMock()
    session.execute = AsyncMock(return_value=_ScalarResult([object()]))
    repository = AstrotypeV2Repository(session)

    calls = [
        repository.list_planet_positions_for_chart(chart_id),
        repository.list_houses_for_chart(chart_id),
        repository.list_aspects_for_chart(chart_id),
        repository.list_balances_for_chart(chart_id),
        repository.list_patterns_for_chart(chart_id),
    ]
    for call in calls:
        assert await call

    statement_text = "\n".join(str(call.args[0]) for call in session.execute.await_args_list)
    assert "astrotype_v2_natal_planet_positions" in statement_text
    assert "astrotype_v2_natal_houses" in statement_text
    assert "astrotype_v2_natal_aspects" in statement_text
    assert "astrotype_v2_natal_chart_balances" in statement_text
    assert "astrotype_v2_natal_chart_patterns" in statement_text
    assert "chart_snapshots" not in statement_text
    assert "report_narratives" not in statement_text


@pytest.mark.asyncio
async def test_load_natal_chart_contract_returns_stable_serializable_contract() -> None:
    from app.modules.astrotype_v2.chart_contract import load_natal_chart_contract

    chart_id = uuid.uuid4()
    contract = await load_natal_chart_contract(_RepositoryStub(chart_id), chart_id)

    assert contract is not None
    assert contract["chart"]["id"] == str(chart_id)
    assert contract["chart"]["engine_version"] == "v2-test"
    assert contract["chart"]["timezone"] == "Europe/Moscow"
    assert contract["planet_positions"][0] == {
        "body": "Mars",
        "longitude": 45.25,
        "latitude": 0.1,
        "speed": -0.24,
        "sign": "Taurus",
        "sign_degree": 15.25,
        "house_number": 10,
        "retrograde": True,
    }
    assert contract["houses"][0] == {"house_number": 10, "longitude": 280.0, "sign": "Capricorn"}
    assert contract["aspects"][0]["body_a"] == "Venus"
    assert contract["aspects"][0]["body_b"] == "Mars"
    assert contract["balances"][0] == {"category": "element", "key": "earth", "value": 1.0, "rank": 1}
    assert contract["patterns"][0]["pattern_code"] == "emphasis_element_earth"
    assert "socionics" not in str(contract)
    assert "function_strength" not in str(contract)


@pytest.mark.asyncio
async def test_load_natal_chart_contract_returns_none_for_missing_chart() -> None:
    from app.modules.astrotype_v2.chart_contract import load_natal_chart_contract

    class EmptyRepository(_RepositoryStub):
        async def get_chart(self, chart_id: uuid.UUID) -> None:
            return None

    assert await load_natal_chart_contract(EmptyRepository(uuid.uuid4()), uuid.uuid4()) is None


def test_chart_contract_source_does_not_import_legacy_v1_or_socionics_modules() -> None:
    contract_path = ROOT / "app" / "modules" / "astrotype_v2" / "chart_contract.py"
    contract_text = contract_path.read_text()

    for fragment in FORBIDDEN_CONTRACT_FRAGMENTS:
        assert fragment not in contract_text
