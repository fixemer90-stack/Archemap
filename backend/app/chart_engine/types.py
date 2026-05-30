"""Chart engine data types — immutable dataclasses for astrological data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PlanetPosition:
    """A single planet/point position in the chart."""

    name: str  # e.g. "Sun", "Moon", "Mercury"
    longitude: float  # ecliptic longitude 0-360°
    latitude: float  # ecliptic latitude
    speed: float  # degrees per day (negative = retrograde)
    sign: str  # zodiac sign name
    sign_degree: float  # degree within the sign (0-30)
    house: int | None = None  # house number 1-12 (filled after house calc)

    @property
    def is_retrograde(self) -> bool:
        return self.speed < 0


@dataclass(frozen=True, slots=True)
class HousePosition:
    """A single house cusp."""

    number: int  # 1-12
    longitude: float  # ecliptic longitude of cusp
    sign: str  # zodiac sign name


@dataclass(frozen=True, slots=True)
class Aspect:
    """An aspect between two planets."""

    planet_a: str
    planet_b: str
    aspect_type: str  # e.g. "conjunction", "opposition", "trine"
    angle: float  # exact angle of the aspect
    orb: float  # difference from exact angle
    is_applying: bool  # True if aspect is applying (tightening)


@dataclass(frozen=True, slots=True)
class ChartData:
    """Complete computed chart snapshot."""

    # Input metadata
    birth_datetime: datetime
    latitude: float
    longitude: float
    timezone: str

    # Computed data
    planets: list[PlanetPosition] = field(default_factory=list)
    houses: list[HousePosition] = field(default_factory=list)
    aspects: list[Aspect] = field(default_factory=list)

    # Technical metadata
    house_system: str = "P"  # Placidus
    ayanamsa: float = 0.0  # for sidereal calculations (0 = tropical)


# ── Zodiac signs ──────────────────────────────────────────────────────
ZODIAC_SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]


def longitude_to_sign(longitude: float) -> tuple[str, float]:
    """Convert ecliptic longitude to zodiac sign and degree within sign."""
    longitude = longitude % 360
    sign_index = int(longitude / 30)
    degree = longitude % 30
    return ZODIAC_SIGNS[sign_index], degree
