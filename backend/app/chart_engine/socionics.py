"""Socionics rule engine — weighted scoring with calibration."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.chart_engine.features import FeatureVector


@dataclass(frozen=True, slots=True)
class SocionicsResult:
    type_code: str
    type_name: str
    functions: str
    score: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    breakdown: dict[str, float] = field(default_factory=dict)


# ── 16 types: (code, name, functions, element1, element2, modality) ──
# element1 = programmatic function's element (weight 2.0)
# element2 = creative function's element (weight 1.5)
# modality = rationality axis (weight 1.0)
TYPES = [
    ("ILE", "Искатель",        "Ne+Ti", "air",   "earth", "mutable"),
    ("SEI", "Посредник",       "Si+Fe", "earth", "fire",  "mutable"),
    ("ESE", "Энтузиаст",       "Fe+Si", "fire",  "earth", "cardinal"),
    ("LII", "Аналитик",        "Ti+Ne", "air",   "earth", "fixed"),
    ("EIE", "Наставник",       "Fe+Ni", "fire",  "water", "cardinal"),
    ("LSI", "Инспектор",       "Ti+Se", "earth", "fire",  "fixed"),
    ("SLE", "Маршал",          "Se+Ti", "fire",  "earth", "fixed"),
    ("IEI", "Лирик",           "Ni+Fe", "water", "fire",  "mutable"),
    ("SEE", "Политик",         "Se+Fi", "fire",  "water", "fixed"),
    ("ILI", "Критик",          "Ni+Te", "water", "earth", "mutable"),
    ("LIE", "Предприниматель", "Te+Ni", "earth", "fire",  "cardinal"),
    ("ESI", "Хранитель",       "Fi+Se", "water", "earth", "fixed"),
    ("LSE", "Администратор",   "Te+Si", "earth", "fire",  "fixed"),
    ("EII", "Гуманист",        "Fi+Ne", "water", "air",   "mutable"),
    ("IEE", "Психолог",        "Ne+Fi", "air",   "water", "mutable"),
    ("SLI", "Мастер",          "Si+Te", "earth", "air",   "mutable"),
]

# ── Weights ──
W_ELEMENT1 = 2.0   # programmatic function element
W_ELEMENT2 = 1.5   # creative function element
W_MODALITY = 1.0   # rationality axis
W_PLANET = 0.5     # planet position bonus

# ── Planet → function mapping for bonus scoring ──
PLANET_FUNCTION_MAP = {
    "Sun": {"Ti": 0.3, "Te": 0.3, "Se": 0.2, "Ne": 0.2},
    "Moon": {"Fe": 0.2, "Fi": 0.2, "Si": 0.2, "Ni": 0.2},
    "Mercury": {"Ti": 0.4, "Te": 0.3, "Ne": 0.2},
    "Venus": {"Fi": 0.4, "Fe": 0.3, "Si": 0.2},
    "Mars": {"Se": 0.5, "Te": 0.3},
    "Jupiter": {"Ne": 0.3, "Fe": 0.3, "Te": 0.2},
    "Saturn": {"Ti": 0.4, "Si": 0.3, "Te": 0.2},
    "Uranus": {"Ne": 0.5, "Ti": 0.2},
    "Neptune": {"Ni": 0.4, "Fi": 0.3, "Fe": 0.2},
    "Pluto": {"Se": 0.3, "Fi": 0.3, "Ni": 0.3},
}

# ── Sign → element mapping ──
SIGN_ELEMENT = {
    "Aries": "fire", "Leo": "fire", "Sagittarius": "fire",
    "Taurus": "earth", "Virgo": "earth", "Capricorn": "earth",
    "Gemini": "air", "Libra": "air", "Aquarius": "air",
    "Cancer": "water", "Scorpio": "water", "Pisces": "water",
}


def evaluate_socionics(features: FeatureVector, chart: object = None) -> list[SocionicsResult]:
    """Evaluate all 16 socionics types against a feature vector.

    Returns sorted list (best match first).
    """
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

    # Planet bonuses (if chart data available)
    planet_bonuses: dict[str, float] = {}
    if chart and hasattr(chart, "planets"):
        for planet in chart.planets:
            func_map = PLANET_FUNCTION_MAP.get(planet.name, {})
            for func, weight in func_map.items():
                planet_bonuses[func] = planet_bonuses.get(func, 0) + weight

    results: list[SocionicsResult] = []

    for code, name, funcs, e1, e2, mod in TYPES:
        # Element scores (normalized 0-1)
        e1_score = elements[e1]
        e2_score = elements[e2]
        mod_score = modalities[mod]

        # Weighted sum
        raw_score = (
            W_ELEMENT1 * e1_score
            + W_ELEMENT2 * e2_score
            + W_MODALITY * mod_score
        )
        max_possible = W_ELEMENT1 + W_ELEMENT2 + W_MODALITY

        # Planet bonus
        func1, func2 = funcs.split("+")
        bonus = planet_bonuses.get(func1, 0) + planet_bonuses.get(func2, 0) * 0.5
        raw_score += W_PLANET * bonus
        max_possible += W_PLANET * (max(planet_bonuses.values()) if planet_bonuses else 0)

        score = min(raw_score / max_possible, 1.0) if max_possible > 0 else 0

        # Confidence based on how decisive the match is
        # Higher when one element clearly dominates
        max_elem = max(elements.values())
        spread = max_elem - min(elements.values())
        confidence = min(0.5 + spread, 1.0)

        results.append(SocionicsResult(
            type_code=code,
            type_name=name,
            functions=funcs,
            score=round(score, 3),
            confidence=round(confidence, 3),
            breakdown={
                "element1": round(W_ELEMENT1 * e1_score, 3),
                "element2": round(W_ELEMENT2 * e2_score, 3),
                "modality": round(W_MODALITY * mod_score, 3),
                "planet_bonus": round(W_PLANET * bonus, 3),
            },
        ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results
