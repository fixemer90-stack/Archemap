"""Socionics rule engine v3 — planet-first weighted scoring.

No TYPE_PRIOR. Calibration through real astrological parameters:
PLANET_NATURAL, ELEMENT_FUNCTION, HOUSE_FUNCTION, ASPECT_FUNCTION,
PLANET_RELATION_FUNCTION.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.chart_engine.features import FeatureVector


@dataclass(frozen=True, slots=True)
class FunctionProfile:
    """Multi-dimensional function strength."""

    strength: float = 0.0  # base power (Sun/Moon/Mercury/Venus/Mars/Saturn/Jupiter/MC)
    tension: float = 0.0  # Chiron/Pluto/square aspects — vulnerability, compensation
    harmony: float = 0.0  # trine/sextile aspects — easy flow, natural talent
    distortion: float = 0.0  # Lilith/square/opposition — shadow, overcompensation


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
    "Sun": {"Te": 0.34, "Fe": 0.22, "Se": 0.18, "Ti": 0.14, "Ni": 0.12},
    "Moon": {"Si": 0.32, "Fi": 0.28, "Fe": 0.22, "Ni": 0.18},
    "Mercury": {"Ne": 0.34, "Ti": 0.30, "Te": 0.22, "Ni": 0.10, "Fe": 0.04},
    "Venus": {"Fi": 0.38, "Fe": 0.26, "Si": 0.20, "Se": 0.10, "Ni": 0.06},
    "Mars": {"Se": 0.42, "Te": 0.24, "Ti": 0.14, "Fe": 0.12, "Ni": 0.08},
    "Jupiter": {"Ne": 0.26, "Fe": 0.24, "Te": 0.20, "Ni": 0.18, "Se": 0.12},
    "Saturn": {"Ti": 0.32, "Te": 0.26, "Si": 0.24, "Ni": 0.14, "Fi": 0.04},
    "Uranus": {"Ne": 0.46, "Ti": 0.24, "Ni": 0.16, "Te": 0.10, "Se": 0.04},
    "Neptune": {"Ni": 0.42, "Fi": 0.24, "Fe": 0.22, "Si": 0.08, "Ne": 0.04},
    "Pluto": {"Se": 0.26, "Ni": 0.24, "Fi": 0.20, "Ti": 0.18, "Te": 0.12},
    "Chiron": {"Fi": 0.26, "Ni": 0.24, "Ti": 0.18, "Fe": 0.18, "Si": 0.14},
    "Lilith": {"Se": 0.28, "Fi": 0.24, "Ni": 0.20, "Fe": 0.14, "Ti": 0.14},
    "North Node": {"Ni": 0.30, "Ne": 0.24, "Fi": 0.20, "Te": 0.14, "Fe": 0.12},
}

SIGN_ELEMENT = {
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

# ── Element → function boost ──
ELEMENT_FUNCTION: dict[str, dict[str, float]] = {
    "fire": {"Se": 0.34, "Fe": 0.30, "Ni": 0.18, "Ne": 0.12, "Te": 0.06},
    "earth": {"Te": 0.36, "Si": 0.30, "Ti": 0.22, "Fi": 0.08, "Se": 0.04},
    "air": {"Ne": 0.40, "Ti": 0.28, "Ni": 0.14, "Te": 0.12, "Fe": 0.06},
    "water": {"Ni": 0.34, "Fi": 0.30, "Fe": 0.22, "Si": 0.10, "Se": 0.04},
}

# ── House → function boost ──
HOUSE_FUNCTION: dict[int, dict[str, float]] = {
    1: {"Se": 0.36, "Ti": 0.22, "Fi": 0.18, "Fe": 0.12, "Ni": 0.12},
    2: {"Si": 0.30, "Te": 0.26, "Fi": 0.20, "Se": 0.12, "Ni": 0.12},
    3: {"Ne": 0.38, "Ti": 0.30, "Te": 0.16, "Fe": 0.08, "Ni": 0.04, "Se": 0.04},
    4: {"Fi": 0.32, "Si": 0.26, "Ni": 0.24, "Fe": 0.14, "Te": 0.04},
    5: {"Fi": 0.30, "Fe": 0.26, "Se": 0.22, "Ne": 0.14, "Ni": 0.08},
    6: {"Te": 0.34, "Si": 0.30, "Ti": 0.18, "Se": 0.08, "Fi": 0.06, "Ni": 0.04},
    7: {"Fi": 0.32, "Se": 0.28, "Fe": 0.22, "Ti": 0.12, "Ni": 0.06},
    8: {"Ni": 0.32, "Fe": 0.28, "Fi": 0.20, "Se": 0.14, "Ti": 0.06},
    9: {"Ni": 0.30, "Fe": 0.26, "Te": 0.22, "Ne": 0.14, "Ti": 0.08},
    10: {"Te": 0.36, "Si": 0.26, "Se": 0.14, "Fe": 0.10, "Ni": 0.08, "Ti": 0.06},
    11: {"Ne": 0.40, "Te": 0.20, "Fe": 0.18, "Ti": 0.14, "Ni": 0.06, "Se": 0.02},
    12: {"Ni": 0.40, "Fi": 0.28, "Fe": 0.16, "Si": 0.10, "Ne": 0.06},
}

# ── Aspect type → function boost ──
ASPECT_FUNCTION: dict[str, dict[str, float]] = {
    "conjunction": {"Te": 0.18, "Si": 0.18, "Ni": 0.16, "Se": 0.14, "Ti": 0.12, "Fe": 0.12, "Fi": 0.10},
    "sextile": {"Ne": 0.22, "Fe": 0.20, "Te": 0.18, "Fi": 0.16, "Si": 0.12, "Ni": 0.08, "Ti": 0.04},
    "square": {"Se": 0.26, "Te": 0.22, "Ti": 0.16, "Si": 0.12, "Fe": 0.10, "Ni": 0.08, "Fi": 0.06},
    "trine": {"Ni": 0.20, "Si": 0.18, "Ne": 0.18, "Fi": 0.16, "Fe": 0.14, "Te": 0.10, "Ti": 0.04},
    "opposition": {"Ti": 0.24, "Fi": 0.20, "Se": 0.18, "Ni": 0.16, "Te": 0.12, "Fe": 0.10},
    "quincunx": {"Ni": 0.16, "Ne": 0.14, "Ti": 0.14, "Fi": 0.12, "Fe": 0.12, "Se": 0.10, "Te": 0.10, "Si": 0.08},
}

# ── Planet pair → function boost ──
PLANET_RELATION_FUNCTION: dict[tuple[str, str], dict[str, float]] = {
    ("Sun", "Moon"): {"Fe": 0.24, "Fi": 0.22, "Ni": 0.18, "Si": 0.18, "Te": 0.10, "Se": 0.08},
    ("Sun", "Mercury"): {"Te": 0.30, "Ti": 0.26, "Ni": 0.18, "Fe": 0.12, "Ne": 0.10, "Se": 0.04},
    ("Sun", "Venus"): {"Fe": 0.26, "Fi": 0.24, "Si": 0.16, "Se": 0.12, "Ni": 0.12, "Te": 0.10},
    ("Sun", "Mars"): {"Se": 0.34, "Te": 0.24, "Fe": 0.16, "Ti": 0.14, "Ni": 0.12},
    ("Moon", "Mercury"): {"Fe": 0.24, "Ti": 0.20, "Si": 0.20, "Ne": 0.14, "Fi": 0.12, "Te": 0.10},
    ("Moon", "Venus"): {"Fi": 0.32, "Fe": 0.26, "Si": 0.24, "Ni": 0.12, "Se": 0.06},
    ("Moon", "Mars"): {"Se": 0.28, "Fe": 0.22, "Fi": 0.18, "Si": 0.14, "Te": 0.10, "Ni": 0.08},
    ("Moon", "Saturn"): {"Si": 0.32, "Ti": 0.24, "Fi": 0.18, "Te": 0.14, "Ni": 0.12},
    ("Moon", "Neptune"): {"Ni": 0.36, "Fi": 0.24, "Fe": 0.22, "Si": 0.12, "Ne": 0.06},
    ("Mercury", "Venus"): {"Fe": 0.24, "Fi": 0.22, "Ne": 0.18, "Ti": 0.18, "Si": 0.10, "Te": 0.08},
    ("Mercury", "Mars"): {"Ti": 0.28, "Te": 0.26, "Se": 0.24, "Fe": 0.10, "Ne": 0.08, "Ni": 0.04},
    ("Mercury", "Jupiter"): {"Ne": 0.28, "Te": 0.24, "Fe": 0.18, "Ni": 0.14, "Ti": 0.12, "Si": 0.04},
    ("Mercury", "Saturn"): {"Ti": 0.32, "Te": 0.28, "Si": 0.20, "Ni": 0.12, "Ne": 0.08},
    ("Mercury", "Uranus"): {"Ne": 0.48, "Ti": 0.26, "Te": 0.12, "Ni": 0.10, "Fe": 0.04},
    ("Venus", "Mars"): {"Fi": 0.28, "Se": 0.26, "Fe": 0.22, "Si": 0.12, "Te": 0.08, "Ni": 0.04},
    ("Venus", "Saturn"): {"Fi": 0.30, "Si": 0.24, "Ti": 0.18, "Fe": 0.14, "Ni": 0.10, "Te": 0.04},
    ("Mars", "Saturn"): {"Ti": 0.28, "Se": 0.26, "Te": 0.24, "Si": 0.12, "Ni": 0.06, "Fi": 0.04},
    ("Mars", "Pluto"): {"Se": 0.36, "Te": 0.20, "Ni": 0.18, "Fi": 0.14, "Ti": 0.12},
    ("Jupiter", "Saturn"): {"Te": 0.28, "Ti": 0.22, "Si": 0.18, "Ni": 0.16, "Ne": 0.10, "Fe": 0.06},
    ("Jupiter", "Neptune"): {"Ni": 0.30, "Fe": 0.24, "Ne": 0.20, "Fi": 0.16, "Te": 0.10},
    ("Saturn", "Uranus"): {"Ti": 0.28, "Te": 0.24, "Ne": 0.20, "Si": 0.16, "Ni": 0.12},
    ("Saturn", "Neptune"): {"Ni": 0.28, "Si": 0.22, "Ti": 0.20, "Fi": 0.16, "Te": 0.14},
    ("Uranus", "Neptune"): {"Ni": 0.30, "Ne": 0.28, "Ti": 0.16, "Fe": 0.12, "Fi": 0.08, "Te": 0.06},
    ("Uranus", "Pluto"): {"Se": 0.24, "Ne": 0.24, "Ti": 0.20, "Ni": 0.18, "Te": 0.14},
    ("Neptune", "Pluto"): {"Ni": 0.34, "Fi": 0.22, "Se": 0.18, "Fe": 0.14, "Ti": 0.12},
}

# ── Retrograde shift ──
EXTRO_TO_INTRO: dict[str, str] = {
    "Te": "Ti",
    "Ti": "Te",
    "Se": "Si",
    "Si": "Se",
    "Fe": "Fi",
    "Fi": "Fe",
    "Ne": "Ni",
    "Ni": "Ne",
}

# ── Global layer weights ──
W_PLANET = 0.14
W_ELEMENT = 0.20
W_HOUSE = 0.32
W_ASPECT = 0.22
W_RELATION = 0.12

# ── Differential planet importance ──
# Personal (Sun/Moon/Mercury/Venus/Mars): 1.0-1.8
# Social (Jupiter/Saturn): 0.7-0.8
# Generational (Uranus/Neptune/Pluto): 0.3-0.4
# Points (Nodes/Lilith/Chiron): 0.15-0.25
PLANET_WEIGHT: dict[str, float] = {
    "Sun": 1.8,
    "Moon": 1.6,
    "Mercury": 1.3,
    "Venus": 1.2,
    "Mars": 1.3,
    "Jupiter": 0.8,
    "Saturn": 0.9,
    "Uranus": 0.4,
    "Neptune": 0.4,
    "Pluto": 0.5,
    "North Node": 0.2,
    "South Node": 0.2,
    "Lilith": 0.2,
    "Chiron": 0.25,
}

# ── Type scoring weights ──
W_FUNCTION_SCORE = 0.70
W_ELEMENT_SCORE = 0.08
W_MODALITY_SCORE = 0.14
W_ORDER_SCORE = 0.08
SECOND_FUNCTION_FACTOR = 0.48
AXIS_BONUS_FACTOR = 0.05


def _compute_function_strengths(chart: object) -> dict[str, float]:
    """Compute function strengths from chart data."""
    strengths: dict[str, float] = {f: 0.0 for f in ["Se", "Si", "Ne", "Ni", "Fe", "Fi", "Te", "Ti"]}

    if not hasattr(chart, "planets"):
        return strengths

    planet_map: dict[str, object] = {}
    for planet in chart.planets:
        planet_map[planet.name] = planet

    for planet in chart.planets:
        name = planet.name
        sign = planet.sign
        house = planet.house
        elem = SIGN_ELEMENT.get(sign, "fire")
        is_retrograde = getattr(planet, "is_retrograde", False)

        # Planet natural affinity
        natural = PLANET_NATURAL.get(name, {})
        for func, weight in natural.items():
            target = EXTRO_TO_INTRO.get(func, func) if is_retrograde else func
            strengths[target] += W_PLANET * weight

        # Element boost
        elem_boost = ELEMENT_FUNCTION.get(elem, {})
        for func, weight in elem_boost.items():
            target = EXTRO_TO_INTRO.get(func, func) if is_retrograde else func
            strengths[target] += W_ELEMENT * weight

        # House boost
        if house:
            house_boost = HOUSE_FUNCTION.get(house, {})
            for func, weight in house_boost.items():
                target = EXTRO_TO_INTRO.get(func, func) if is_retrograde else func
                strengths[target] += W_HOUSE * weight

    # Aspect-based function boosting
    if hasattr(chart, "aspects"):
        for aspect in chart.aspects:
            aspect_type = aspect.aspect_type
            aspect_funcs = ASPECT_FUNCTION.get(aspect_type, {})
            if not aspect_funcs:
                continue

            # Apply aspect functions weighted by orb (tighter = stronger)
            orb = getattr(aspect, "orb", 5.0)
            orb_factor = max(0.2, 1.0 - orb / 10.0)  # 0°=1.0, 10°=0.2

            for func, weight in aspect_funcs.items():
                strengths[func] += W_ASPECT * weight * orb_factor

    # Planet relation function boosting
    if hasattr(chart, "aspects"):
        for aspect in chart.aspects:
            key_forward = (aspect.planet_a, aspect.planet_b)
            key_reverse = (aspect.planet_b, aspect.planet_a)
            relation = PLANET_RELATION_FUNCTION.get(key_forward) or PLANET_RELATION_FUNCTION.get(key_reverse)
            if not relation:
                continue

            orb = getattr(aspect, "orb", 5.0)
            orb_factor = max(0.2, 1.0 - orb / 10.0)

            for func, weight in relation.items():
                strengths[func] += W_RELATION * weight * orb_factor

    # Normalize to 0-1
    max_val = max(strengths.values()) if strengths else 1.0
    if max_val > 0:
        strengths = {k: v / max_val for k, v in strengths.items()}

    return strengths


# ── Layered computation for tension/harmony/distortion ──

# Planets that create tension (vulnerability, compensation)
TENSION_PLANETS = {"Chiron", "Pluto"}
# Planets that create distortion (shadow, overcompensation)
DISTORTION_PLANETS = {"Lilith"}

ASPECT_HARMONY = {"trine", "sextile"}
ASPECT_TENSION = {"square", "opposition"}


def _compute_function_profiles(chart: object) -> dict[str, FunctionProfile]:
    """Compute multi-dimensional function profiles.

    Layers:
    - strength: base power from Sun/Moon/Mercury/Venus/Mars/Saturn/Jupiter
    - tension: Chiron/Pluto + square/opposition aspects
    - harmony: trine/sextile aspects
    - distortion: Lilith + harsh aspects
    """
    funcs = ["Se", "Si", "Ne", "Ni", "Fe", "Fi", "Te", "Ti"]
    strength = {f: 0.0 for f in funcs}
    tension = {f: 0.0 for f in funcs}
    harmony = {f: 0.0 for f in funcs}
    distortion = {f: 0.0 for f in funcs}

    if not hasattr(chart, "planets"):
        return {f: FunctionProfile() for f in funcs}

    planet_map: dict[str, object] = {}
    for planet in chart.planets:
        planet_map[planet.name] = planet

    for planet in chart.planets:
        name = planet.name
        sign = planet.sign
        house = planet.house
        elem = SIGN_ELEMENT.get(sign, "fire")
        is_retrograde = getattr(planet, "is_retrograde", False)

        natural = PLANET_NATURAL.get(name, {})
        for func, weight in natural.items():
            target = EXTRO_TO_INTRO.get(func, func) if is_retrograde else func

            # Base strength from all planets
            strength[target] += W_PLANET * weight

            # Element boost
            elem_boost = ELEMENT_FUNCTION.get(elem, {})
            for efunc, eweight in elem_boost.items():
                etarget = EXTRO_TO_INTRO.get(efunc, efunc) if is_retrograde else efunc
                strength[etarget] += W_ELEMENT * eweight

            # House boost
            if house:
                house_boost = HOUSE_FUNCTION.get(house, {})
                for hfunc, hweight in house_boost.items():
                    htarget = EXTRO_TO_INTRO.get(hfunc, hfunc) if is_retrograde else hfunc
                    strength[htarget] += W_HOUSE * hweight

            # Tension layer: Chiron/Pluto contribute to tension
            if name in TENSION_PLANETS:
                tension[target] += weight * 0.5

            # Distortion layer: Lilith contributes to distortion
            if name in DISTORTION_PLANETS:
                distortion[target] += weight * 0.5

    # Aspect-based layers
    if hasattr(chart, "aspects"):
        for aspect in chart.aspects:
            aspect_type = aspect.aspect_type
            orb = getattr(aspect, "orb", 5.0)
            orb_factor = max(0.2, 1.0 - orb / 10.0)

            # Harmony from trine/sextile
            if aspect_type in ASPECT_HARMONY:
                aspect_funcs = ASPECT_FUNCTION.get(aspect_type, {})
                for func, weight in aspect_funcs.items():
                    harmony[func] += W_ASPECT * weight * orb_factor

            # Tension from square/opposition
            if aspect_type in ASPECT_TENSION:
                aspect_funcs = ASPECT_FUNCTION.get(aspect_type, {})
                for func, weight in aspect_funcs.items():
                    tension[func] += W_ASPECT * weight * orb_factor * 0.5
                    distortion[func] += W_ASPECT * weight * orb_factor * 0.3

    # Normalize each layer
    def normalize(d: dict[str, float]) -> dict[str, float]:
        mx = max(d.values()) if d else 1.0
        return {k: v / mx for k, v in d.items()} if mx > 0 else d

    strength = normalize(strength)
    tension = normalize(tension)
    harmony = normalize(harmony)
    distortion = normalize(distortion)

    return {
        f: FunctionProfile(
            strength=round(strength[f], 3),
            tension=round(tension[f], 3),
            harmony=round(harmony[f], 3),
            distortion=round(distortion[f], 3),
        )
        for f in funcs
    }


def evaluate_socionics(features: FeatureVector, chart: object = None) -> list[SocionicsResult]:
    """Evaluate all 16 socionics types. Planet-first approach."""

    func_strengths = _compute_function_strengths(chart)
    func_profiles = _compute_function_profiles(chart)

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

        order_alignment = max(f1_score - f2_score, 0.0)
        axis_bonus = min(f1_score, f2_score)

        raw = (
            W_FUNCTION_SCORE * (f1_score + f2_score * SECOND_FUNCTION_FACTOR)
            + W_ELEMENT_SCORE * (e1_score + e2_score * SECOND_FUNCTION_FACTOR)
            + W_MODALITY_SCORE * modalities.get(mod, 0)
            + W_ORDER_SCORE * order_alignment
            + AXIS_BONUS_FACTOR * axis_bonus
        )
        max_possible = (
            W_FUNCTION_SCORE * (1 + SECOND_FUNCTION_FACTOR)
            + W_ELEMENT_SCORE * (1 + SECOND_FUNCTION_FACTOR)
            + W_MODALITY_SCORE
            + W_ORDER_SCORE
            + AXIS_BONUS_FACTOR
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
                    # Full function strengths
                    "Se": round(func_strengths.get("Se", 0), 3),
                    "Si": round(func_strengths.get("Si", 0), 3),
                    "Ne": round(func_strengths.get("Ne", 0), 3),
                    "Ni": round(func_strengths.get("Ni", 0), 3),
                    "Fe": round(func_strengths.get("Fe", 0), 3),
                    "Fi": round(func_strengths.get("Fi", 0), 3),
                    "Te": round(func_strengths.get("Te", 0), 3),
                    "Ti": round(func_strengths.get("Ti", 0), 3),
                    # Layered profiles
                    "Ne_tension": func_profiles["Ne"].tension,
                    "Ne_harmony": func_profiles["Ne"].harmony,
                    "Ti_tension": func_profiles["Ti"].tension,
                    "Ti_harmony": func_profiles["Ti"].harmony,
                    "Te_tension": func_profiles["Te"].tension,
                    "Te_harmony": func_profiles["Te"].harmony,
                    "Fe_tension": func_profiles["Fe"].tension,
                    # Diagnostics
                    "mental_ne_ti": round(func_strengths.get("Ne", 0) * 0.6 + func_strengths.get("Ti", 0) * 0.4, 3),
                    "business_te": round(func_strengths.get("Te", 0), 3),
                },
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results
