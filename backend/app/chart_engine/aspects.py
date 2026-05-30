"""Aspect detection — finds aspects between planets with orb checking."""

from __future__ import annotations

from app.chart_engine.ephemeris import ASPECT_ANGLES, DEFAULT_ORBS
from app.chart_engine.types import Aspect, PlanetPosition


def _angular_distance(lon_a: float, lon_b: float) -> float:
    """Shortest angular distance between two longitudes (0-180°)."""
    diff = abs(lon_a - lon_b) % 360
    return min(diff, 360 - diff)


def _is_applying(
    lon_a: float,
    speed_a: float,
    lon_b: float,
    speed_b: float,
    aspect_angle: float,
) -> bool:
    """Determine if aspect is applying (orb decreasing).

    Simplified: if the faster planet is catching up to the exact angle.
    """
    current_orb = abs(_angular_distance(lon_a, lon_b) - aspect_angle)

    # Project 1 day forward
    future_a = lon_a + speed_a
    future_b = lon_b + speed_b
    future_orb = abs(_angular_distance(future_a, future_b) - aspect_angle)

    return future_orb < current_orb


def find_aspects(
    planets: list[PlanetPosition],
    custom_orbs: dict[str, float] | None = None,
) -> list[Aspect]:
    """Detect aspects between all planet pairs.

    Args:
        planets: list of computed planet positions
        custom_orbs: optional override for default orb values

    Returns:
        list of Aspect objects, sorted by orb (tightest first)
    """
    orbs = {**DEFAULT_ORBS, **(custom_orbs or {})}
    aspects: list[Aspect] = []

    for i, pa in enumerate(planets):
        for pb in planets[i + 1 :]:
            distance = _angular_distance(pa.longitude, pb.longitude)

            for aspect_name, exact_angle in ASPECT_ANGLES.items():
                max_orb = orbs.get(aspect_name, 6)
                orb = abs(distance - exact_angle)

                if orb <= max_orb:
                    applying = _is_applying(
                        pa.longitude,
                        pa.speed,
                        pb.longitude,
                        pb.speed,
                        exact_angle,
                    )
                    aspects.append(
                        Aspect(
                            planet_a=pa.name,
                            planet_b=pb.name,
                            aspect_type=aspect_name,
                            angle=distance,
                            orb=orb,
                            is_applying=applying,
                        )
                    )
                    break  # one aspect per pair (closest match)

    aspects.sort(key=lambda a: a.orb)
    return aspects
