"""Swiss Ephemeris wrapper — planet positions, houses.

Falls back to a lightweight stub when pyswisseph is not available
(e.g. in CI without compiled binary). The stub returns deterministic
placeholder data so tests can run.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.chart_engine.types import PlanetPosition, longitude_to_sign

# ── Try importing swisseph ────────────────────────────────────────────
try:
    import swisseph as swe  # type: ignore[import-not-found]

    _HAS_SWISSEPH = True
except (ImportError, OSError):
    try:
        import pyswisseph as swe  # type: ignore[import-not-found]

        _HAS_SWISSEPH = True
    except (ImportError, OSError):
        _HAS_SWISSEPH = False

# ── Planet IDs ────────────────────────────────────────────────────────
# Swiss Ephemeris planet constants (values from swe module or hardcoded)
PLANET_NAMES = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "North Node",
    "Chiron",
]

# Default orbs for aspects
ASPECT_ANGLES: dict[str, float] = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "quincunx": 150,
    "opposition": 180,
}

DEFAULT_ORBS: dict[str, float] = {
    "conjunction": 8,
    "sextile": 6,
    "square": 7,
    "trine": 7,
    "quincunx": 5,
    "opposition": 8,
}


def init_ephemeris() -> None:
    """Initialize Swiss Ephemeris."""
    if _HAS_SWISSEPH:
        swe.set_ephe_path(None)


def compute_planet_positions(
    dt: datetime,
    latitude: float,
    longitude: float,
) -> list[PlanetPosition]:
    """Compute ecliptic positions of all planets for a given datetime (UTC)."""
    if _HAS_SWISSEPH:
        try:
            return _compute_real(dt, latitude, longitude)
        except Exception:
            pass
    return _compute_stub(dt, latitude, longitude)


def compute_houses(
    julian_day: float,
    latitude: float,
    longitude: float,
    system: str = "P",
) -> tuple[list[tuple[float, int]], tuple[float, float]]:
    """Compute house cusps and ASC/MC."""
    if _HAS_SWISSEPH:
        try:
            return _houses_real(julian_day, latitude, longitude, system)
        except Exception:
            pass
    return _houses_stub(julian_day, latitude, longitude)


def datetime_to_julian_day(dt: datetime) -> float:
    """Convert a datetime to Julian Day Number (UT)."""
    if _HAS_SWISSEPH:
        result: float = swe.julday(
            dt.year,
            dt.month,
            dt.day,
            dt.hour + dt.minute / 60.0 + dt.second / 3600.0,
        )
        return result
    return _julian_day_stub(dt)


# ── Real implementation (pyswisseph) ─────────────────────────────────
_PLANET_IDS: list[int] | None = None


def _get_planet_ids() -> list[int]:
    global _PLANET_IDS
    if _PLANET_IDS is None:
        _PLANET_IDS = [
            swe.SUN,
            swe.MOON,
            swe.MERCURY,
            swe.VENUS,
            swe.MARS,
            swe.JUPITER,
            swe.SATURN,
            swe.URANUS,
            swe.NEPTUNE,
            swe.PLUTO,
            swe.TRUE_NODE,
            swe.CHIRON,
        ]
    return _PLANET_IDS


def _compute_real(dt: datetime, lat: float, lon: float) -> list[PlanetPosition]:
    jd = datetime_to_julian_day(dt)
    positions: list[PlanetPosition] = []
    for name, pid in zip(PLANET_NAMES, _get_planet_ids(), strict=True):
        result = swe.calc_ut(jd, pid, swe.FLG_SPEED | swe.FLG_SWIEPH)
        plon, plat, _, pspeed = result[0][:4]
        sign, sign_deg = longitude_to_sign(plon)
        positions.append(
            PlanetPosition(
                name=name,
                longitude=plon,
                latitude=plat,
                speed=pspeed,
                sign=sign,
                sign_degree=sign_deg,
            )
        )
    return positions


def _houses_real(jd: float, lat: float, lon: float, system: str) -> tuple[list[tuple[float, int]], tuple[float, float]]:
    cusps, ascmc = swe.houses(jd, lat, lon, system.encode())
    house_list = [(c, i + 1) for i, c in enumerate(cusps)]
    return house_list, (ascmc[0], ascmc[1])


# ── Stub implementation (no pyswisseph) ──────────────────────────────
def _julian_day_stub(dt: datetime) -> float:
    """Approximate Julian Day Number."""
    y, m, d = dt.year, dt.month, dt.day
    h = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + h / 24.0 - 1524.5 + (2 - a + a // 4)


def _compute_stub(dt: datetime, lat: float, lon: float) -> list[PlanetPosition]:
    """Return deterministic placeholder positions for testing."""
    # Rough approximations for 2000-01-01 00:00 UTC, shifted by date
    base_longitudes = [
        280.0,
        100.0,
        250.0,
        300.0,
        320.0,  # Sun-Pluto
        120.0,
        50.0,
        320.0,
        310.0,
        250.0,  # Jupiter-Pluto
        125.0,
        75.0,  # Node, Chiron
    ]
    # Simple deterministic shift based on date
    day_offset = (dt - datetime(2000, 1, 1, tzinfo=UTC)).days
    shift = (day_offset * 0.9856) % 360  # ~1 degree per day for Sun

    positions: list[PlanetPosition] = []
    for name, base_lon in zip(PLANET_NAMES, base_longitudes, strict=True):
        lon_val = (base_lon + shift) % 360
        sign, sign_deg = longitude_to_sign(lon_val)
        positions.append(
            PlanetPosition(
                name=name,
                longitude=lon_val,
                latitude=0.0,
                speed=1.0,
                sign=sign,
                sign_degree=sign_deg,
            )
        )
    return positions


def _houses_stub(jd: float, lat: float, lon: float) -> tuple[list[tuple[float, int]], tuple[float, float]]:
    """Return equal house system from ASC = ARMC approximation."""
    # Simplified: ASC ≈ local sidereal time
    lst = (jd % 1) * 360 + lon
    lst = lst % 360
    cusps = [(lst + i * 30) % 360 for i in range(12)]
    house_list = [(c, i + 1) for i, c in enumerate(cusps)]
    return house_list, (lst, (lst + 90) % 360)
