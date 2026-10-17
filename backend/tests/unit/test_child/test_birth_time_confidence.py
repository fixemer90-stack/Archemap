from __future__ import annotations

import hashlib
import json
from dataclasses import fields
from datetime import UTC, date, datetime, time, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.chart_engine.types import Aspect, ChartData, HousePosition, PlanetPosition

GOLDEN_FIXTURES = Path(__file__).with_name("fixtures") / "birth_time_golden.json"


def _chart_at(birth_datetime: datetime, *, moon_sign: str = "Cancer") -> ChartData:
    moon_longitude = 95.0 if moon_sign == "Cancer" else 125.0
    return ChartData(
        birth_datetime=birth_datetime,
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        planets=[
            PlanetPosition("Sun", 45.0, 0.0, 1.0, "Taurus", 15.0, 10),
            PlanetPosition("Moon", moon_longitude, 0.0, 13.0, moon_sign, 5.0, 12),
            PlanetPosition("Ascendant", 10.0, 0.0, 0.0, "Aries", 10.0, 1),
            PlanetPosition("MC", 280.0, 0.0, 0.0, "Capricorn", 10.0, 10),
        ],
        houses=[
            HousePosition(1, 10.0, "Aries"),
            HousePosition(10, 280.0, "Capricorn"),
        ],
        aspects=[Aspect("Sun", "Moon", "sextile", 60.0, 1.0, True)],
        house_system="P",
    )


def test_unknown_time_uses_technical_noon_but_excludes_houses_angles_and_overlays() -> None:
    from app.modules.child.chart_adapter import ChildChartInput, build_child_chart

    calls: list[datetime] = []

    def chart_builder(
        birth_datetime: datetime,
        latitude: float,
        longitude: float,
        timezone_name: str,
        house_system: str = "P",
    ) -> ChartData:
        calls.append(birth_datetime)
        return _chart_at(birth_datetime)

    result = build_child_chart(
        ChildChartInput(
            birth_date=date(2021, 5, 12),
            birth_time=None,
            birth_time_confidence="unknown",
            latitude=55.7558,
            longitude=37.6173,
            timezone="Europe/Moscow",
        ),
        engine_version="child-chart-test-1",
        chart_builder=chart_builder,
    )

    payload = result.calculation_payload
    assert payload["technical_reference"]["synthetic_noon"] is True
    assert payload["technical_reference"]["user_supplied_time"] is False
    assert payload["houses"] == []
    assert {point["body"] for point in payload["planet_positions"]}.isdisjoint({"Ascendant", "MC"})
    assert all(point["house_number"] is None for point in payload["planet_positions"])
    assert all(point["longitude"] is None for point in payload["planet_positions"])
    assert {"houses", "angles", "house_assignments", "house_overlays"} <= set(result.excluded_fact_families)
    assert result.allowed_fact_families == ("stable_planet_signs", "stable_aspects")
    assert "planet_positions" not in result.allowed_fact_families
    assert "house_overlays" not in result.allowed_fact_families
    assert calls
    assert all(call.tzinfo is UTC for call in calls)


def test_approximate_time_retains_only_facts_stable_across_versioned_sixty_minute_window() -> None:
    from app.modules.child.birth_time_policy import resolve_birth_time_policy
    from app.modules.child.chart_adapter import ChildChartInput, build_child_chart

    center_utc = datetime(2021, 5, 12, 7, 0, tzinfo=UTC)

    def chart_builder(
        birth_datetime: datetime,
        latitude: float,
        longitude: float,
        timezone_name: str,
        house_system: str = "P",
    ) -> ChartData:
        offset_minutes = int((birth_datetime - center_utc).total_seconds() / 60)
        moon_sign = "Leo" if offset_minutes == 60 else "Cancer"
        chart = _chart_at(birth_datetime, moon_sign=moon_sign)
        chart.planets[0] = PlanetPosition("Sun", 45.0, 0.0, 1.0, "Taurus", 15.0, 10)
        chart.planets[1] = PlanetPosition("Moon", 119.9 + offset_minutes / 60, 0.0, 13.0, moon_sign, 29.9, 12)
        chart.planets[2] = PlanetPosition(
            "Ascendant",
            10.0 + offset_minutes,
            0.0,
            0.0,
            "Aries" if offset_minutes <= 0 else "Taurus",
            10.0,
            1,
        )
        return chart

    result = build_child_chart(
        ChildChartInput(
            birth_date=date(2021, 5, 12),
            birth_time=datetime.strptime("10:00", "%H:%M").time(),
            birth_time_confidence="approximate",
            latitude=55.7558,
            longitude=37.6173,
            timezone="Europe/Moscow",
        ),
        engine_version="child-chart-test-1",
        chart_builder=chart_builder,
    )

    payload = result.calculation_payload
    assert payload["stability_evidence"]["window_minutes"] == 60
    assert payload["stability_evidence"]["sample_offsets_minutes"] == [-60, -30, 0, 30, 60]
    assert payload["stability_evidence"]["facts"]["planet_sign:Sun"]["stable"] is True
    assert payload["stability_evidence"]["facts"]["planet_sign:Moon"]["stable"] is False
    assert payload["stability_evidence"]["facts"]["planet_sign:Moon"]["confidence"] == 0.8
    assert payload["stability_evidence"]["facts"]["angle_sign:Ascendant"]["stable"] is False
    assert {point["body"] for point in payload["planet_positions"]} == {"Sun"}
    assert payload["planet_positions"][0]["longitude"] is None
    assert payload["planet_positions"][0]["sign_degree"] is None
    assert payload["houses"] == []
    assert payload["aspects"] == []
    assert "planet_sign:Moon" in payload["exclusions"]
    assert "angle_sign:Ascendant" in payload["exclusions"]
    unstable = sorted(
        key for key, evidence in payload["stability_evidence"]["facts"].items() if evidence["stable"] is False
    )
    expected_exclusions = [*resolve_birth_time_policy("approximate").excluded_fact_families, *unstable]
    assert payload["exclusions"] == expected_exclusions
    assert list(result.excluded_fact_families) == expected_exclusions
    assert result.uncertainty_reason


def test_exact_time_retains_full_chart_and_gender_is_not_a_chart_input() -> None:
    from app.modules.child.chart_adapter import ChildChartInput, build_child_chart

    chart_input = ChildChartInput(
        birth_date=date(2021, 5, 12),
        birth_time=datetime.strptime("10:00", "%H:%M").time(),
        birth_time_confidence="exact",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
    )
    result = build_child_chart(
        chart_input,
        engine_version="child-chart-test-1",
        chart_builder=lambda birth_datetime, *_: _chart_at(birth_datetime),
    )

    payload = result.calculation_payload
    assert len(payload["houses"]) == 2
    assert {point["body"] for point in payload["planet_positions"]} == {
        "Sun",
        "Moon",
        "Ascendant",
        "MC",
    }
    assert {point["body"]: point["house_number"] for point in payload["planet_positions"]} == {
        "Sun": 10,
        "Moon": 12,
        "Ascendant": 1,
        "MC": 10,
    }
    assert result.excluded_fact_families == ()
    assert result.uncertainty_reason is None
    assert result.source_input == chart_input
    assert "child_gender" not in {field.name for field in fields(ChildChartInput)}


def test_exact_time_rejects_nonexistent_dst_wall_time() -> None:
    import pytest

    from app.modules.child.chart_adapter import ChildChartInput, build_child_chart

    with pytest.raises(ValueError, match="nonexistent"):
        build_child_chart(
            ChildChartInput(
                birth_date=date(2021, 3, 14),
                birth_time=time(2, 30),
                birth_time_confidence="exact",
                latitude=40.7128,
                longitude=-74.006,
                timezone="America/New_York",
            ),
            engine_version="child-chart-test-1",
            chart_builder=lambda birth_datetime, *_: _chart_at(birth_datetime),
        )


def test_exact_time_rejects_ambiguous_dst_wall_time() -> None:
    import pytest

    from app.modules.child.chart_adapter import ChildChartInput, build_child_chart

    with pytest.raises(ValueError, match="ambiguous"):
        build_child_chart(
            ChildChartInput(
                birth_date=date(2021, 11, 7),
                birth_time=time(1, 30),
                birth_time_confidence="exact",
                latitude=40.7128,
                longitude=-74.006,
                timezone="America/New_York",
            ),
            engine_version="child-chart-test-1",
            chart_builder=lambda birth_datetime, *_: _chart_at(birth_datetime),
        )


def test_approximate_time_rejects_window_crossing_dst_gap() -> None:
    import pytest

    from app.modules.child.chart_adapter import ChildChartInput, build_child_chart

    with pytest.raises(ValueError, match="nonexistent"):
        build_child_chart(
            ChildChartInput(
                birth_date=date(2021, 3, 14),
                birth_time=time(3, 30),
                birth_time_confidence="approximate",
                latitude=40.7128,
                longitude=-74.006,
                timezone="America/New_York",
            ),
            engine_version="child-chart-test-1",
            chart_builder=lambda birth_datetime, *_: _chart_at(birth_datetime),
        )


def test_approximate_time_rejects_window_crossing_dst_fold() -> None:
    import pytest

    from app.modules.child.chart_adapter import ChildChartInput, build_child_chart

    with pytest.raises(ValueError, match="ambiguous"):
        build_child_chart(
            ChildChartInput(
                birth_date=date(2021, 11, 7),
                birth_time=time(2, 0),
                birth_time_confidence="approximate",
                latitude=40.7128,
                longitude=-74.006,
                timezone="America/New_York",
            ),
            engine_version="child-chart-test-1",
            chart_builder=lambda birth_datetime, *_: _chart_at(birth_datetime),
        )


def test_offset_aware_birth_time_is_rejected() -> None:
    import pytest

    from app.modules.child.chart_adapter import ChildChartInput, build_child_chart

    with pytest.raises(ValueError, match="offset-aware"):
        build_child_chart(
            ChildChartInput(
                birth_date=date(2021, 5, 12),
                birth_time=time(10, 0, tzinfo=timezone(timedelta(hours=3))),
                birth_time_confidence="exact",
                latitude=55.7558,
                longitude=37.6173,
                timezone="Europe/Moscow",
            ),
            engine_version="child-chart-test-1",
            chart_builder=lambda birth_datetime, *_: _chart_at(birth_datetime),
        )


def test_unknown_time_excludes_moon_sign_when_local_day_crosses_a_sign_boundary() -> None:
    from app.modules.child.chart_adapter import ChildChartInput, build_child_chart

    def chart_builder(
        birth_datetime: datetime,
        latitude: float,
        longitude: float,
        timezone_name: str,
        house_system: str = "P",
    ) -> ChartData:
        moon_sign = "Leo" if birth_datetime.hour >= 18 else "Cancer"
        return _chart_at(birth_datetime, moon_sign=moon_sign)

    result = build_child_chart(
        ChildChartInput(
            birth_date=date(2021, 5, 12),
            birth_time=None,
            birth_time_confidence="unknown",
            latitude=55.7558,
            longitude=37.6173,
            timezone="UTC",
        ),
        engine_version="child-chart-test-1",
        chart_builder=chart_builder,
    )

    payload = result.calculation_payload
    assert payload["stability_evidence"]["facts"]["planet_sign:Moon"]["stable"] is False
    assert {point["body"] for point in payload["planet_positions"]} == {"Sun"}
    assert payload["aspects"] == []
    assert "planet_sign:Moon" in payload["exclusions"]


def test_unknown_time_fail_closed_excludes_moon_even_when_discrete_samples_agree() -> None:
    from app.modules.child.birth_time_policy import BIRTH_TIME_POLICY_VERSION
    from app.modules.child.chart_adapter import ChildChartInput, build_child_chart

    chart_input = ChildChartInput(
        birth_date=date(2021, 5, 12),
        birth_time=None,
        birth_time_confidence="unknown",
        latitude=55.7558,
        longitude=37.6173,
        timezone="UTC",
    )
    result = build_child_chart(
        chart_input,
        engine_version="child-chart-test-1",
        chart_builder=lambda birth_datetime, *_: _chart_at(birth_datetime, moon_sign="Cancer"),
    )

    payload = result.calculation_payload
    assert payload["stability_evidence"]["facts"]["planet_sign:Moon"]["stable"] is False
    assert payload["stability_evidence"]["facts"]["planet_sign:Moon"]["reason"] == "unknown_time_moon"
    assert {point["body"] for point in payload["planet_positions"]} == {"Sun"}
    assert payload["aspects"] == []
    assert "planet_sign:Moon" in payload["exclusions"]
    assert "stable_moon_sign" not in result.allowed_fact_families
    assert BIRTH_TIME_POLICY_VERSION == "child-birth-time-policy-v3"

    legacy_hash_payload = {
        "birth_date": chart_input.birth_date.isoformat(),
        "birth_time": None,
        "birth_time_confidence": chart_input.birth_time_confidence,
        "latitude": chart_input.latitude,
        "longitude": chart_input.longitude,
        "timezone": chart_input.timezone,
        "house_system": chart_input.house_system,
        "engine_version": "child-chart-test-1",
        "policy_version": "child-birth-time-policy-v2",
    }
    legacy_canonical = json.dumps(legacy_hash_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    legacy_hash = hashlib.sha256(legacy_canonical.encode()).hexdigest()
    assert result.input_hash != legacy_hash


async def test_chart_version_persistence_allocates_next_immutable_lineage_idempotently() -> None:
    from app.modules.child.chart_adapter import ChildChartBuild
    from app.modules.child.models import ChildProfile
    from app.modules.child.repository import ChildRepository

    owner_id = uuid4()
    child = ChildProfile(
        owner_user_id=owner_id,
        parent_profile_id=uuid4(),
        display_name="Child",
        relationship_type="child",
        child_gender=None,
        birth_date=date(2021, 5, 12),
        birth_time=None,
        birth_time_confidence="unknown",
        birth_place="Moscow",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        caregiver_context={},
        birth_data_hash="a" * 64,
        idempotency_key="child-1",
        status="active",
        version=1,
    )
    build = ChildChartBuild(
        engine_version="child-chart-test-1",
        input_hash="b" * 64,
        birth_time_confidence="unknown",
        allowed_fact_families=("planet_signs",),
        excluded_fact_families=("houses",),
        uncertainty_reason="unknown time",
        calculation_payload={"contract_version": "child-birth-time-policy-v3"},
    )
    inserted = MagicMock(version=3, child_profile_id=child.id, input_hash=build.input_hash)
    session = MagicMock()
    session.scalar = AsyncMock(side_effect=[child, None, 2])
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(),
            MagicMock(scalar_one_or_none=MagicMock(return_value=inserted)),
        ]
    )

    result = await ChildRepository(session).create_chart_version_idempotently(
        owner_user_id=owner_id,
        child_profile_id=child.id,
        chart=build,
    )

    assert result.created is True
    assert result.chart is inserted
    insert_statement = str(session.execute.await_args_list[1].args[0])
    assert "child_chart_versions" in insert_statement
    assert "version" in insert_statement


def test_real_engine_golden_exact_approximate_unknown_and_moon_boundary() -> None:
    from app.modules.child.chart_adapter import ChildChartInput, build_child_chart

    fixtures = json.loads(GOLDEN_FIXTURES.read_text(encoding="utf-8"))
    assert [fixture["name"] for fixture in fixtures] == [
        "exact_full_chart",
        "approximate_moon_boundary",
        "unknown_moon_boundary",
    ]

    for fixture in fixtures:
        birth_time = (
            datetime.fromisoformat(f"2000-01-01T{fixture['birth_time']}").time() if fixture["birth_time"] else None
        )
        result = build_child_chart(
            ChildChartInput(
                birth_date=date.fromisoformat(fixture["birth_date"]),
                birth_time=birth_time,
                birth_time_confidence=fixture["confidence"],
                latitude=55.7558,
                longitude=37.6173,
                timezone="UTC",
            ),
            engine_version="child-chart-golden-1",
        )
        positions = {point["body"]: point for point in result.calculation_payload["planet_positions"]}

        assert ("Moon" in positions) is fixture["expected_moon_included"], fixture["name"]
        if fixture["expected_moon_sign"] is not None:
            assert positions["Moon"]["sign"] == fixture["expected_moon_sign"]
        assert bool(result.calculation_payload["houses"]) is fixture["expected_houses"], fixture["name"]
