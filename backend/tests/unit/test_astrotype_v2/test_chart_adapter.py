"""Contract tests for Astrotype v2 chart adapter."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.chart_engine.types import Aspect, ChartData, HousePosition, PlanetPosition

ROOT = Path(__file__).resolve().parents[3]

FORBIDDEN_ADAPTER_FRAGMENTS = (
    "socionics",
    "function_strength",
    "model_a",
    "report_narrative",
    "chart_snapshots",
    "ChartSnapshot",
)


def _sample_chart() -> ChartData:
    return ChartData(
        birth_datetime=datetime(1991, 8, 1, 9, 30, tzinfo=UTC),
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        planets=[
            PlanetPosition(
                name="Mars",
                longitude=45.25,
                latitude=0.1,
                speed=-0.24,
                sign="Taurus",
                sign_degree=15.25,
                house=10,
            ),
            PlanetPosition(
                name="Venus",
                longitude=165.5,
                latitude=-0.2,
                speed=1.1,
                sign="Virgo",
                sign_degree=15.5,
                house=2,
            ),
        ],
        houses=[
            HousePosition(number=1, longitude=10.0, sign="Aries"),
            HousePosition(number=10, longitude=280.0, sign="Capricorn"),
        ],
        aspects=[
            Aspect(
                planet_a="Venus",
                planet_b="Mars",
                aspect_type="trine",
                angle=120.0,
                orb=1.5,
                is_applying=True,
            )
        ],
        house_system="P",
        ayanamsa=0.0,
    )


def test_chart_adapter_maps_engine_chart_to_v2_rows_without_persisting() -> None:
    from app.modules.astrotype_v2.chart_adapter import build_natal_chart_rows
    from app.modules.astrotype_v2.models import NatalChart

    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()

    rows = build_natal_chart_rows(
        chart_data=_sample_chart(),
        user_id=user_id,
        profile_id=profile_id,
        engine_version="v2-test",
        input_hash="abc123",
    )

    assert isinstance(rows.chart, NatalChart)
    assert rows.chart.user_id == user_id
    assert rows.chart.profile_id == profile_id
    assert rows.chart.engine_version == "v2-test"
    assert rows.chart.input_hash == "abc123"
    assert rows.chart.birth_datetime_utc == datetime(1991, 8, 1, 9, 30, tzinfo=UTC)
    assert rows.chart.timezone == "Europe/Moscow"
    assert rows.chart.latitude == 55.7558
    assert rows.chart.longitude == 37.6173
    assert rows.chart.house_system == "P"
    assert rows.chart.calculation_payload["ayanamsa"] == 0.0


def test_chart_adapter_persists_mars_taurus_10_retrograde_style_position_rows() -> None:
    from app.modules.astrotype_v2.chart_adapter import build_natal_chart_rows

    rows = build_natal_chart_rows(
        chart_data=_sample_chart(),
        user_id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        engine_version="v2-test",
        input_hash="abc123",
    )

    mars = next(row for row in rows.planet_positions if row.body == "Mars")
    assert mars.longitude == 45.25
    assert mars.latitude == 0.1
    assert mars.speed == -0.24
    assert mars.sign == "Taurus"
    assert mars.sign_degree == 15.25
    assert mars.house_number == 10
    assert mars.retrograde is True


def test_chart_adapter_maps_houses_and_canonical_aspects() -> None:
    from app.modules.astrotype_v2.chart_adapter import build_natal_chart_rows

    rows = build_natal_chart_rows(
        chart_data=_sample_chart(),
        user_id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        engine_version="v2-test",
        input_hash="abc123",
    )

    assert [(house.house_number, house.longitude, house.sign) for house in rows.houses] == [
        (1, 10.0, "Aries"),
        (10, 280.0, "Capricorn"),
    ]

    assert len(rows.aspects) == 1
    aspect = rows.aspects[0]
    assert aspect.body_a == "Venus"
    assert aspect.body_b == "Mars"
    assert aspect.aspect_code == "trine"
    assert aspect.angle_degrees == 120.0
    assert aspect.orb_degrees == 1.5
    assert aspect.applying is True
    assert aspect.strength == 0.875


def test_chart_adapter_generates_balance_and_pattern_rows_without_legacy_fields() -> None:
    from app.modules.astrotype_v2.chart_adapter import build_natal_chart_rows

    rows = build_natal_chart_rows(
        chart_data=_sample_chart(),
        user_id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        engine_version="v2-test",
        input_hash="abc123",
    )

    balances = {(row.category, row.key): row.value for row in rows.balances}
    assert balances[("element", "earth")] == 1.0
    assert balances[("modality", "fixed")] == 0.5
    assert balances[("modality", "mutable")] == 0.5
    assert balances[("house", "10")] == 0.5
    assert balances[("house", "2")] == 0.5

    assert rows.patterns
    assert all(pattern.pattern_code.startswith("emphasis_") for pattern in rows.patterns)
    for collection in (rows.planet_positions, rows.houses, rows.aspects, rows.balances, rows.patterns):
        for row in collection:
            assert row.__table__.name.startswith("astrotype_v2_")
            assert not any(fragment in row.__table__.name for fragment in FORBIDDEN_ADAPTER_FRAGMENTS)


def test_chart_adapter_source_does_not_import_legacy_v1_or_socionics_modules() -> None:
    adapter_path = ROOT / "app" / "modules" / "astrotype_v2" / "chart_adapter.py"
    adapter_text = adapter_path.read_text()

    for fragment in FORBIDDEN_ADAPTER_FRAGMENTS:
        assert fragment not in adapter_text
