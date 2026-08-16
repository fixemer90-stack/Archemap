"""Chart builder — assembles ChartData from birth data."""

from __future__ import annotations

from datetime import datetime

from app.chart_engine.aspects import find_aspects
from app.chart_engine.ephemeris import (
    compute_houses,
    compute_planet_positions,
    datetime_to_julian_day,
    init_ephemeris,
)
from app.chart_engine.types import ChartData, HousePosition, PlanetPosition, longitude_to_sign


def _assign_houses(
    planets: list[PlanetPosition],
    houses: list[tuple[float, int]],
) -> list[PlanetPosition]:
    """Assign house numbers to planets based on cusp longitudes."""
    # Build sorted cusp list for lookup
    cusps = sorted(houses, key=lambda h: h[0])

    updated: list[PlanetPosition] = []
    for planet in planets:
        house_num = _find_house(planet.longitude, cusps)
        updated.append(
            PlanetPosition(
                name=planet.name,
                longitude=planet.longitude,
                latitude=planet.latitude,
                speed=planet.speed,
                sign=planet.sign,
                sign_degree=planet.sign_degree,
                house=house_num,
            )
        )
    return updated


def _find_house(planet_lon: float, sorted_cusps: list[tuple[float, int]]) -> int:
    """Determine which house a planet falls in."""
    planet_lon = planet_lon % 360

    for i in range(len(sorted_cusps)):
        cusp_a = sorted_cusps[i][0] % 360
        cusp_b = sorted_cusps[(i + 1) % len(sorted_cusps)][0] % 360

        if cusp_a < cusp_b:
            if cusp_a <= planet_lon < cusp_b:
                return sorted_cusps[i][1]
        else:
            # Wraps around 360°
            if planet_lon >= cusp_a or planet_lon < cusp_b:
                return sorted_cusps[i][1]

    return sorted_cusps[0][1]  # fallback


def build_chart(
    birth_datetime: datetime,
    latitude: float,
    longitude: float,
    timezone_name: str,
    house_system: str = "P",
) -> ChartData:
    """Build a complete ChartData from birth information.

    Args:
        birth_datetime: UTC datetime of birth
        latitude: birth place latitude
        longitude: birth place longitude
        timezone_name: IANA timezone string
        house_system: house system code (P=Placidus, E=Equal, K=Koch)

    Returns:
        ChartData with planets, houses, and aspects
    """
    init_ephemeris()

    # Compute planets
    planets = compute_planet_positions(birth_datetime, latitude, longitude)

    # Compute houses
    jd = datetime_to_julian_day(birth_datetime)
    house_cusps, (asc_lon, mc_lon) = compute_houses(jd, latitude, longitude, house_system)

    # Build house positions
    houses: list[HousePosition] = []
    for cusp_lon, house_num in house_cusps:
        sign, _ = longitude_to_sign(cusp_lon)
        houses.append(HousePosition(number=house_num, longitude=cusp_lon, sign=sign))

    # Assign houses to planets
    planets = _assign_houses(planets, house_cusps)

    # Find aspects
    aspects = find_aspects(planets)

    # Preserve chart angles as deterministic points for v2 key indicators.
    # They are appended after aspect calculation because ASC/MC are not planets
    # in the existing aspect engine, but downstream report payloads still need
    # their exact positions from the house calculation.
    asc_sign, asc_degree = longitude_to_sign(asc_lon)
    mc_sign, mc_degree = longitude_to_sign(mc_lon)
    planets = [
        *planets,
        PlanetPosition("Ascendant", asc_lon, 0.0, 0.0, asc_sign, asc_degree, 1),
        PlanetPosition("MC", mc_lon, 0.0, 0.0, mc_sign, mc_degree, 10),
    ]

    return ChartData(
        birth_datetime=birth_datetime,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone_name,
        planets=planets,
        houses=houses,
        aspects=aspects,
        house_system=house_system,
    )
