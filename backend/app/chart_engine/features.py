"""Feature extraction — normalized features from chart data.

Converts a ChartData snapshot into a FeatureVector with values
in [0.0, 1.0] range for use by the rule engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.chart_engine.types import ChartData, PlanetPosition

# ── Element mapping ───────────────────────────────────────────────────
SIGN_ELEMENTS: dict[str, str] = {
    "Aries": "fire",
    "Leo": "fire",
    "Sagittarius": "fire",
    "Taurus": "earth",
    "Virgo": "earth",
    "Capricorn": "earth",
    "Gemini": "air",
    "Libra": "air",
    "Aquarius": "air",
    "Cancer": "water",
    "Scorpio": "water",
    "Pisces": "water",
}

# ── Modality mapping ─────────────────────────────────────────────────
SIGN_MODALITIES: dict[str, str] = {
    "Aries": "cardinal",
    "Cancer": "cardinal",
    "Libra": "cardinal",
    "Capricorn": "cardinal",
    "Taurus": "fixed",
    "Leo": "fixed",
    "Scorpio": "fixed",
    "Aquarius": "fixed",
    "Gemini": "mutable",
    "Virgo": "mutable",
    "Sagittarius": "mutable",
    "Pisces": "mutable",
}

# ── Planet weights for emphasis calculation ───────────────────────────
PLANET_WEIGHTS: dict[str, float] = {
    "Sun": 1.0,
    "Moon": 0.9,
    "Mercury": 0.6,
    "Venus": 0.6,
    "Mars": 0.7,
    "Jupiter": 0.7,
    "Saturn": 0.7,
    "Uranus": 0.5,
    "Neptune": 0.5,
    "Pluto": 0.5,
    "North Node": 0.3,
    "Chiron": 0.3,
}


@dataclass(frozen=True, slots=True)
class FeatureVector:
    """Normalized features extracted from a chart.

    All values are in [0.0, 1.0] unless noted otherwise.
    """

    # Element distribution (sum ≈ 1.0)
    fire: float = 0.0
    earth: float = 0.0
    air: float = 0.0
    water: float = 0.0

    # Modality distribution (sum ≈ 1.0)
    cardinal: float = 0.0
    fixed: float = 0.0
    mutable: float = 0.0

    # Luminaries emphasis
    sun_moon_balance: float = 0.5  # 0 = all Moon, 1 = all Sun

    # House emphasis (top 3 houses as normalized values)
    house_emphasis: dict[int, float] = field(default_factory=dict)

    # Aspect counts (normalized by max possible)
    conjunction_count: float = 0.0
    trine_count: float = 0.0
    square_count: float = 0.0
    opposition_count: float = 0.0

    # Quality flags
    has_birth_time: bool = True
    birth_time_quality: float = 1.0  # 1.0 = exact, 0.5 = approximate, 0.0 = unknown

    def to_dict(self) -> dict[str, float | bool | dict[int, float]]:
        """Serialize to a JSON-compatible dict."""
        return {
            "fire": self.fire,
            "earth": self.earth,
            "air": self.air,
            "water": self.water,
            "cardinal": self.cardinal,
            "fixed": self.fixed,
            "mutable": self.mutable,
            "sun_moon_balance": self.sun_moon_balance,
            "house_emphasis": self.house_emphasis,
            "conjunction_count": self.conjunction_count,
            "trine_count": self.trine_count,
            "square_count": self.square_count,
            "opposition_count": self.opposition_count,
            "has_birth_time": self.has_birth_time,
            "birth_time_quality": self.birth_time_quality,
        }


def extract_features(chart: ChartData) -> FeatureVector:
    """Extract normalized features from a computed chart."""
    # Element distribution
    element_counts = {"fire": 0.0, "earth": 0.0, "air": 0.0, "water": 0.0}
    for planet in chart.planets:
        elem = SIGN_ELEMENTS.get(planet.sign, "fire")
        weight = PLANET_WEIGHTS.get(planet.name, 0.5)
        element_counts[elem] += weight

    total_weight = sum(element_counts.values()) or 1.0
    elements = {k: v / total_weight for k, v in element_counts.items()}

    # Modality distribution
    modality_counts = {"cardinal": 0.0, "fixed": 0.0, "mutable": 0.0}
    for planet in chart.planets:
        mod = SIGN_MODALITIES.get(planet.sign, "cardinal")
        weight = PLANET_WEIGHTS.get(planet.name, 0.5)
        modality_counts[mod] += weight

    total_mod = sum(modality_counts.values()) or 1.0
    modalities = {k: v / total_mod for k, v in modality_counts.items()}

    # Sun/Moon balance
    sun = next((p for p in chart.planets if p.name == "Sun"), None)
    moon = next((p for p in chart.planets if p.name == "Moon"), None)
    sun_moon_balance = _compute_sun_moon_balance(sun, moon)

    # House emphasis
    house_emphasis = _compute_house_emphasis(chart.planets)

    # Aspect counts (normalized)
    aspect_counts = {"conjunction": 0, "trine": 0, "square": 0, "opposition": 0}
    for a in chart.aspects:
        if a.aspect_type in aspect_counts:
            aspect_counts[a.aspect_type] += 1
    max_aspects = max(len(chart.planets) * (len(chart.planets) - 1) // 2, 1)

    # Birth time quality
    has_bt = True  # default
    bt_quality = 1.0

    return FeatureVector(
        fire=round(elements["fire"], 3),
        earth=round(elements["earth"], 3),
        air=round(elements["air"], 3),
        water=round(elements["water"], 3),
        cardinal=round(modalities["cardinal"], 3),
        fixed=round(modalities["fixed"], 3),
        mutable=round(modalities["mutable"], 3),
        sun_moon_balance=round(sun_moon_balance, 3),
        house_emphasis=house_emphasis,
        conjunction_count=round(aspect_counts["conjunction"] / max_aspects, 3),
        trine_count=round(aspect_counts["trine"] / max_aspects, 3),
        square_count=round(aspect_counts["square"] / max_aspects, 3),
        opposition_count=round(aspect_counts["opposition"] / max_aspects, 3),
        has_birth_time=has_bt,
        birth_time_quality=bt_quality,
    )


def _compute_sun_moon_balance(sun: PlanetPosition | None, moon: PlanetPosition | None) -> float:
    """Compute Sun/Moon emphasis balance. 0.5 = equal, 1.0 = all Sun."""
    if not sun or not moon:
        return 0.5
    # Use sign element strength as proxy
    # Simple: Sun's longitude as fraction of 360
    return sun.longitude / 360.0


def _compute_house_emphasis(planets: list[PlanetPosition]) -> dict[int, float]:
    """Compute weighted house emphasis. Returns top houses normalized."""
    house_weights: dict[int, float] = {}
    for planet in planets:
        if planet.house is not None:
            weight = PLANET_WEIGHTS.get(planet.name, 0.5)
            house_weights[planet.house] = house_weights.get(planet.house, 0.0) + weight

    if not house_weights:
        return {}

    max_weight = max(house_weights.values()) or 1.0
    return {h: round(w / max_weight, 3) for h, w in sorted(house_weights.items())}
