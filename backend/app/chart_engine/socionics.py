"""Socionics rule engine v2 — planet-first weighted scoring."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.chart_engine.features import FeatureVector


@dataclass(frozen=True, slots=True)
class SocionicsResult:
    type_code: str
    type_name: str
    functions: str
    score: float
    confidence: float
    breakdown: dict[str, float] = field(default_factory=dict)


# ── 16 types ──
TYPES = [
    ("ILE", "Искатель", "Ne+Ti", "air", "earth", "mutable"),
    ("SEI", "Посредник", "Si+Fe", "earth", "fire", "mutable"),
    ("ESE", "Энтузиаст", "Fe+Si", "fire", "earth", "cardinal"),
    ("LII", "Аналитик", "Ti+Ne", "air", "earth", "fixed"),
    ("EIE", "Наставник", "Fe+Ni", "fire", "water", "cardinal"),
    ("LSI", "Инспектор", "Ti+Se", "earth", "fire", "fixed"),
    ("SLE", "Маршал", "Se+Ti", "fire", "earth", "fixed"),
    ("IEI", "Лирик", "Ni+Fe", "water", "fire", "mutable"),
    ("SEE", "Политик", "Se+Fi", "fire", "water", "fixed"),
    ("ILI", "Критик", "Ni+Te", "water", "earth", "mutable"),
    ("LIE", "Предприниматель", "Te+Ni", "earth", "fire", "cardinal"),
    ("ESI", "Хранитель", "Fi+Se", "water", "earth", "fixed"),
    ("LSE", "Администратор", "Te+Si", "earth", "fire", "fixed"),
    ("EII", "Гуманист", "Fi+Ne", "water", "air", "mutable"),
    ("IEE", "Психолог", "Ne+Fi", "air", "water", "mutable"),
    ("SLI", "Мастер", "Si+Te", "earth", "air", "mutable"),
]

# ── Planet → function strength ──
PLANET_NATURAL: dict[str, dict[str, float]] = {
    "Sun": {"Te": 0.5, "Ti": 0.3, "Se": 0.2},
    "Moon": {"Fe": 0.4, "Fi": 0.3, "Si": 0.3},
    "Mercury": {"Ti": 0.5, "Te": 0.3, "Ne": 0.2},
    "Venus": {"Fi": 0.5, "Fe": 0.3, "Si": 0.2},
    "Mars": {"Se": 0.6, "Te": 0.2, "Fe": 0.2},
    "Jupiter": {"Ne": 0.3, "Fe": 0.3, "Te": 0.2, "Ni": 0.2},
    "Saturn": {"Ti": 0.4, "Si": 0.3, "Te": 0.2, "Ni": 0.1},
    "Uranus": {"Ne": 0.5, "Ni": 0.3, "Ti": 0.2},
    "Neptune": {"Ni": 0.5, "Fi": 0.3, "Fe": 0.2},
    "Pluto": {"Se": 0.3, "Fi": 0.3, "Ni": 0.2, "Ti": 0.2},
    "North Node": {"Ni": 0.4, "Ne": 0.3, "Fi": 0.3},
}

SIGN_ELEMENT = {
    "Aries": "fire", "Leo": "fire", "Sagittarius": "fire",
    "Taurus": "earth", "Virgo": "earth", "Capricorn": "earth",
    "Gemini": "air", "Libra": "air", "Aquarius": "air",
    "Cancer": "water", "Scorpio": "water", "Pisces": "water",
}

# Element → function boost
ELEMENT_FUNCTION_BOOST: dict[str, dict[str, float]] = {
    "fire": {"Se": 0.50, "Fe": 0.28, "Ni": 0.12, "Ne": 0.10},
    "earth": {"Te": 0.35, "Ti": 0.30, "Si": 0.20, "Fi": 0.15},
    "air": {"Ti": 0.38, "Ne": 0.28, "Ni": 0.20, "Te": 0.14},
    "water": {"Se": 0.30, "Ni": 0.27, "Fi": 0.25, "Fe": 0.18},
}

# House → function boost
HOUSE_FUNCTION_BOOST: dict[int, dict[str, float]] = {
    1: {"Se": 0.50, "Ti": 0.25, "Fi": 0.15, "Ni": 0.10},
    2: {"Te": 0.30, "Si": 0.25, "Se": 0.20, "Ti": 0.15, "Ni": 0.10},
    3: {"Ti": 0.45, "Se": 0.25, "Te": 0.20, "Ne": 0.10},
    4: {"Fi": 0.30, "Si": 0.30, "Ni": 0.25, "Fe": 0.15},
    5: {"Se": 0.32, "Fi": 0.28, "Fe": 0.25, "Ne": 0.15},
    6: {"Te": 0.35, "Ti": 0.32, "Se": 0.18, "Si": 0.15},
    7: {"Se": 0.38, "Fi": 0.28, "Fe": 0.18, "Ti": 0.16},
    8: {"Se": 0.35, "Ni": 0.28, "Fi": 0.20, "Fe": 0.17},
    9: {"Te": 0.30, "Ti": 0.25, "Ni": 0.20, "Fe": 0.15, "Ne": 0.10},
    10: {"Se": 0.38, "Te": 0.30, "Ti": 0.20, "Fe": 0.12},
    11: {"Ne": 0.35, "Fe": 0.30, "Ti": 0.20, "Se": 0.15},
    12: {"Ni": 0.40, "Fi": 0.30, "Si": 0.20, "Fe": 0.10},
}

# ── Weights ──
W_NATURAL = 0.08
W_ELEMENT = 0.32
W_HOUSE = 0.60
W_ASPECT = 0.12  # aspect between two planets
W_RETROGRADE = 0.10  # retrograde shift

# Extraverted ↔ Introverted for retrograde planets
EXTRO_TO_INTRO: dict[str, str] = {
    "Te": "Ti", "Ti": "Te",
    "Se": "Si", "Si": "Se",
    "Fe": "Fi", "Fi": "Fe",
    "Ne": "Ni", "Ni": "Ne",
}

# Aspect type → boost multiplier
ASPECT_BOOST: dict[str, float] = {
    "conjunction": 0.6,
    "trine": 0.5,
    "sextile": 0.4,
    "square": 0.35,
    "opposition": 0.3,
    "quincunx": 0.2,
}

# Score composition
W_FUNCTION_SCORE = 0.68
W_ELEMENT_SCORE = 0.17
W_MODALITY_SCORE = 0.15
SECOND_FUNCTION_FACTOR = 0.62


def _compute_function_strengths(chart: object) -> dict[str, float]:
    """Compute function strengths from chart data using planet positions."""
    strengths: dict[str, float] = {f: 0.0 for f in ["Se", "Si", "Ne", "Ni", "Fe", "Fi", "Te", "Ti"]}

    if not hasattr(chart, "planets"):
        return strengths

    # Build planet lookup for aspect processing
    planet_map: dict[str, object] = {}
    for planet in chart.planets:
        planet_map[planet.name] = planet

    for planet in chart.planets:
        name = planet.name
        sign = planet.sign
        house = planet.house
        elem = SIGN_ELEMENT.get(sign, "fire")
        is_retrograde = getattr(planet, "is_retrograde", False)

        # Natural affinity (shifted if retrograde)
        natural = PLANET_NATURAL.get(name, {})
        for func, weight in natural.items():
            target = EXTRO_TO_INTRO.get(func, func) if is_retrograde else func
            strengths[target] += W_NATURAL * weight

        # Element boost (shifted if retrograde)
        elem_boost = ELEMENT_FUNCTION_BOOST.get(elem, {})
        for func, weight in elem_boost.items():
            target = EXTRO_TO_INTRO.get(func, func) if is_retrograde else func
            strengths[target] += W_ELEMENT * weight

        # House boost (shifted if retrograde)
        if house:
            house_boost = HOUSE_FUNCTION_BOOST.get(house, {})
            for func, weight in house_boost.items():
                target = EXTRO_TO_INTRO.get(func, func) if is_retrograde else func
                strengths[target] += W_HOUSE * weight

    # Aspect-based function boosting
    if hasattr(chart, "aspects"):
        for aspect in chart.aspects:
            boost = ASPECT_BOOST.get(aspect.aspect_type, 0.2)
            p1 = planet_map.get(aspect.planet_a)
            p2 = planet_map.get(aspect.planet_b)
            if not p1 or not p2:
                continue

            # Both planets get function boost from the aspect
            for p in (p1, p2):
                pname = getattr(p, "name", "")
                natural = PLANET_NATURAL.get(pname, {})
                is_retro = getattr(p, "is_retrograde", False)
                for func, weight in natural.items():
                    target = EXTRO_TO_INTRO.get(func, func) if is_retro else func
                    strengths[target] += W_ASPECT * boost * weight

    # Normalize to 0-1
    max_val = max(strengths.values()) if strengths else 1.0
    if max_val > 0:
        strengths = {k: v / max_val for k, v in strengths.items()}

    return strengths


def evaluate_socionics(features: FeatureVector, chart: object = None) -> list[SocionicsResult]:
    """Evaluate all 16 socionics types. Planet-first approach."""

    func_strengths = _compute_function_strengths(chart)

    elements = {
        "fire": features.fire,
        "earth": features.earth,
        "air": features.air,
        "water": features.water,
    }
    modalities = {
        "cardinal": features.cardinal,
        "fixed": features.fixed,
        "mutable": features.mutable,
    }

    results: list[SocionicsResult] = []

    for code, name, funcs, e1, e2, mod in TYPES:
        func1, func2 = funcs.split("+")

        f1_score = func_strengths.get(func1, 0)
        f2_score = func_strengths.get(func2, 0)
        e1_score = elements[e1]
        e2_score = elements[e2]

        raw = (
            W_FUNCTION_SCORE * (f1_score + f2_score * SECOND_FUNCTION_FACTOR)
            + W_ELEMENT_SCORE * (e1_score + e2_score * SECOND_FUNCTION_FACTOR)
            + W_MODALITY_SCORE * modalities.get(mod, 0)
        )
        max_possible = (
            W_FUNCTION_SCORE * (1 + SECOND_FUNCTION_FACTOR)
            + W_ELEMENT_SCORE * (1 + SECOND_FUNCTION_FACTOR)
            + W_MODALITY_SCORE
        )

        score = min(raw / max_possible, 1.0) if max_possible > 0 else 0

        spread = max(func_strengths.values()) - min(func_strengths.values())
        confidence = min(0.4 + spread * 0.6, 1.0)

        results.append(
            SocionicsResult(
                type_code=code,
                type_name=name,
                functions=funcs,
                score=round(score, 3),
                confidence=round(confidence, 3),
                breakdown={
                    "func1": round(f1_score, 3),
                    "func2": round(f2_score, 3),
                    "elem1": round(e1_score, 3),
                    "elem2": round(e2_score, 3),
                },
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results
