"""Unit tests for the chart engine."""

from __future__ import annotations

from datetime import UTC, datetime

from app.chart_engine.aspects import _angular_distance, find_aspects
from app.chart_engine.chart import build_chart
from app.chart_engine.ephemeris import compute_planet_positions, init_ephemeris
from app.chart_engine.types import PlanetPosition, longitude_to_sign


class TestLongitudeToSign:
    def test_aries(self) -> None:
        sign, deg = longitude_to_sign(15.0)
        assert sign == "Aries"
        assert deg == 15.0

    def test_pisces(self) -> None:
        sign, deg = longitude_to_sign(350.0)
        assert sign == "Pisces"
        assert abs(deg - 20.0) < 0.01

    def test_boundary(self) -> None:
        sign, deg = longitude_to_sign(30.0)
        assert sign == "Taurus"
        assert abs(deg - 0.0) < 0.01

    def test_wrap_360(self) -> None:
        sign, deg = longitude_to_sign(0.0)
        assert sign == "Aries"
        assert deg == 0.0


class TestAngularDistance:
    def test_same_point(self) -> None:
        assert _angular_distance(100, 100) == 0

    def test_opposite(self) -> None:
        assert _angular_distance(0, 180) == 180

    def test_wrap(self) -> None:
        assert _angular_distance(350, 10) == 20

    def test_90_degrees(self) -> None:
        assert _angular_distance(0, 90) == 90


class TestPlanetPositions:
    def test_compute_returns_all_planets(self) -> None:
        """Standard planets should be computed for any valid datetime."""
        init_ephemeris()
        dt = datetime(1990, 5, 15, 12, 30, tzinfo=UTC)
        positions = compute_planet_positions(dt, 55.75, 37.62)

        assert len(positions) == 12  # 10 planets + North Node + Chiron
        names = {p.name for p in positions}
        assert "Sun" in names
        assert "Moon" in names
        assert "Saturn" in names

    def test_sun_in_taurus_may_1990(self) -> None:
        """Sun should be in Taurus around May 15, 1990."""
        init_ephemeris()
        dt = datetime(1990, 5, 15, 12, 0, tzinfo=UTC)
        positions = compute_planet_positions(dt, 55.75, 37.62)

        sun = next(p for p in positions if p.name == "Sun")
        assert sun.sign == "Taurus"
        assert 20 < sun.sign_degree < 30  # ~24° Taurus on May 15

    def test_positions_deterministic(self) -> None:
        """Same input → same output."""
        init_ephemeris()
        dt = datetime(2000, 1, 1, 0, 0, tzinfo=UTC)
        p1 = compute_planet_positions(dt, 0, 0)
        p2 = compute_planet_positions(dt, 0, 0)

        for a, b in zip(p1, p2, strict=True):
            assert a.name == b.name
            assert abs(a.longitude - b.longitude) < 0.0001


class TestFindAspects:
    def test_conjunction(self) -> None:
        """Two planets at same longitude → conjunction."""
        planets = [
            PlanetPosition("A", 100.0, 0, 1, "Cancer", 10.0),
            PlanetPosition("B", 102.0, 0, 1, "Cancer", 12.0),
        ]
        aspects = find_aspects(planets)
        assert len(aspects) >= 1
        assert aspects[0].aspect_type == "conjunction"
        assert aspects[0].orb < 3

    def test_opposition(self) -> None:
        """Planets 180° apart → opposition."""
        planets = [
            PlanetPosition("A", 0.0, 0, 1, "Aries", 0.0),
            PlanetPosition("B", 180.0, 0, 1, "Libra", 0.0),
        ]
        aspects = find_aspects(planets)
        assert any(a.aspect_type == "opposition" for a in aspects)

    def test_no_aspect_too_far(self) -> None:
        """Planets 50° apart → no major aspect (between sextile and square)."""
        planets = [
            PlanetPosition("A", 0.0, 0, 1, "Aries", 0.0),
            PlanetPosition("B", 50.0, 0, 1, "Taurus", 20.0),
        ]
        aspects = find_aspects(planets)
        # 50° is not a standard aspect
        assert len(aspects) == 0


class TestBuildChart:
    def test_full_chart(self) -> None:
        """Build a complete chart and verify structure."""
        dt = datetime(1990, 5, 15, 12, 30, tzinfo=UTC)
        chart = build_chart(dt, 55.75, 37.62, "Europe/Moscow")

        assert len(chart.planets) == 14
        assert len(chart.houses) == 12
        assert chart.timezone == "Europe/Moscow"
        assert chart.house_system == "P"

        # All planets should have house assignments
        for p in chart.planets:
            assert p.house is not None
            assert 1 <= p.house <= 12

    def test_full_chart_includes_angles_as_chart_points(self) -> None:
        """ASC/MC from house calculation must not be discarded."""
        dt = datetime(1990, 5, 15, 12, 30, tzinfo=UTC)
        chart = build_chart(dt, 55.75, 37.62, "Europe/Moscow")

        by_name = {point.name: point for point in chart.planets}

        assert by_name["Ascendant"].longitude == chart.houses[0].longitude
        assert by_name["Ascendant"].house == 1
        assert by_name["MC"].longitude == chart.houses[9].longitude
        assert by_name["MC"].house == 10

    def test_deterministic(self) -> None:
        """Same input → identical chart."""
        dt = datetime(2000, 6, 21, 0, 0, tzinfo=UTC)
        c1 = build_chart(dt, 48.85, 2.35, "Europe/Paris")
        c2 = build_chart(dt, 48.85, 2.35, "Europe/Paris")

        for p1, p2 in zip(c1.planets, c2.planets, strict=True):
            assert abs(p1.longitude - p2.longitude) < 0.0001
        assert len(c1.aspects) == len(c2.aspects)
