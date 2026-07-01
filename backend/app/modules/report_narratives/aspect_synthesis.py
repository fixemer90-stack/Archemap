# ruff: noqa: RUF001
"""Deterministic aspect ranking and pattern clustering for staged narratives."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.modules.report_narratives.schemas import AspectPattern, RankedAspect

PLANET_RU = {
    "Sun": "Солнце",
    "Moon": "Луна",
    "Mercury": "Меркурий",
    "Venus": "Венера",
    "Mars": "Марс",
    "Jupiter": "Юпитер",
    "Saturn": "Сатурн",
    "Uranus": "Уран",
    "Neptune": "Нептун",
    "Pluto": "Плутон",
}

ASPECT_RU = {
    "conjunction": "соединение",
    "sextile": "секстиль",
    "square": "квадрат",
    "trine": "тригон",
    "opposition": "оппозиция",
}

PERSONAL_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Mars"}
OUTER_PLANETS = {"Uranus", "Neptune", "Pluto"}
PLANET_IMPORTANCE = {
    "Sun": 1.0,
    "Moon": 1.0,
    "Mercury": 0.92,
    "Venus": 0.92,
    "Mars": 0.92,
    "Jupiter": 0.75,
    "Saturn": 0.82,
    "Uranus": 0.45,
    "Neptune": 0.45,
    "Pluto": 0.5,
}
ASPECT_TYPE_WEIGHT = {
    "conjunction": 1.0,
    "opposition": 0.96,
    "square": 0.93,
    "trine": 0.88,
    "sextile": 0.78,
}


def _aspect_id(aspect: dict[str, Any]) -> str:
    return (
        f"{str(aspect.get('planet_a', '')).lower()}_"
        f"{str(aspect.get('aspect_type', '')).lower()}_"
        f"{str(aspect.get('planet_b', '')).lower()}"
    )


def _aspect_label(aspect: dict[str, Any]) -> str:
    left = PLANET_RU.get(str(aspect.get("planet_a")), str(aspect.get("planet_a")))
    right = PLANET_RU.get(str(aspect.get("planet_b")), str(aspect.get("planet_b")))
    aspect_name = ASPECT_RU.get(str(aspect.get("aspect_type")), str(aspect.get("aspect_type")))
    return f"{left} {aspect_name} {right}"


def _orb_score(orb: Any) -> float:
    if not isinstance(orb, int | float):
        return 0.35
    return max(0.1, 1.0 - (float(orb) / 6.0))


def _planet_importance(aspect: dict[str, Any]) -> float:
    left = str(aspect.get("planet_a"))
    right = str(aspect.get("planet_b"))
    return (PLANET_IMPORTANCE.get(left, 0.55) + PLANET_IMPORTANCE.get(right, 0.55)) / 2


def _personal_relevance(aspect: dict[str, Any]) -> float:
    planets = {str(aspect.get("planet_a")), str(aspect.get("planet_b"))}
    personal_count = len(planets & PERSONAL_PLANETS)
    outer_count = len(planets & OUTER_PLANETS)
    if personal_count == 2:
        return 1.0
    if personal_count == 1:
        return 0.84
    if outer_count == 2:
        return 0.28
    return 0.55


def _section_targets(aspect: dict[str, Any]) -> list[str]:
    planets = {str(aspect.get("planet_a")), str(aspect.get("planet_b"))}
    if {"Moon", "Mercury"} <= planets:
        return ["emotions_and_communication", "world_perception"]
    if {"Venus", "Mars"} <= planets:
        return ["relationships", "sexuality"]
    if "Saturn" in planets:
        return ["development", "vulnerabilities"]
    if "Moon" in planets:
        return ["emotions_and_communication", "vulnerabilities"]
    if "Sun" in planets or "Mercury" in planets:
        return ["main_formula", "world_perception"]
    return ["main_formula"]


def _repeated_theme_bonus(aspects: list[dict[str, Any]]) -> dict[str, float]:
    counts: Counter[str] = Counter()
    for aspect in aspects:
        planets = {str(aspect.get("planet_a")), str(aspect.get("planet_b"))}
        if {"Moon", "Mercury"} <= planets:
            counts["moon_mercury"] += 1
        if {"Venus", "Mars"} <= planets:
            counts["venus_mars"] += 1
        if "Saturn" in planets:
            counts["saturn"] += 1
    return {
        "moon_mercury": 0.05 if counts["moon_mercury"] > 1 else 0.0,
        "venus_mars": 0.05 if counts["venus_mars"] > 1 else 0.0,
        "saturn": 0.05 if counts["saturn"] > 1 else 0.0,
    }


def rank_chart_aspects(chart: dict[str, Any]) -> list[RankedAspect]:
    aspects = list(chart.get("aspects", []))
    bonuses = _repeated_theme_bonus(aspects)
    ranked: list[RankedAspect] = []
    for aspect in aspects:
        aspect_type = str(aspect.get("aspect_type"))
        targets = _section_targets(aspect)
        planets = {str(aspect.get("planet_a")), str(aspect.get("planet_b"))}
        repeated_bonus = 0.0
        if {"Moon", "Mercury"} <= planets:
            repeated_bonus = bonuses["moon_mercury"]
        elif {"Venus", "Mars"} <= planets:
            repeated_bonus = bonuses["venus_mars"]
        elif "Saturn" in planets:
            repeated_bonus = bonuses["saturn"]
        weight = (
            (_orb_score(aspect.get("orb")) * 0.35)
            + (_planet_importance(aspect) * 0.20)
            + (ASPECT_TYPE_WEIGHT.get(aspect_type, 0.6) * 0.15)
            + (_personal_relevance(aspect) * 0.20)
            + ((0.9 if len(targets) > 1 else 0.6) * 0.10)
            + repeated_bonus
        )
        ranked.append(
            RankedAspect(
                id=_aspect_id(aspect),
                label=_aspect_label(aspect),
                weight=round(weight, 4),
                evidence_ids=[_aspect_id(aspect)],
                section_targets=targets,
            )
        )
    ranked.sort(key=lambda item: (-item.weight, item.id))
    return ranked


def _pattern_type(aspect_type: str) -> str:
    if aspect_type in {"square", "opposition"}:
        return "tension"
    if aspect_type in {"trine", "sextile"}:
        return "support"
    return "mixed"


def _raw_aspects_by_id(chart: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {_aspect_id(aspect): aspect for aspect in chart.get("aspects", [])}


def cluster_aspect_patterns(chart: dict[str, Any], ranked_aspects: list[RankedAspect]) -> list[AspectPattern]:
    raw_by_id = _raw_aspects_by_id(chart)
    patterns: list[AspectPattern] = []
    high_signal_ids = [item.id for item in ranked_aspects if item.weight >= 0.55]

    def build_pattern(pattern_id: str, title: str, ids: list[str], section_targets: list[str]) -> None:
        if not ids:
            return
        members = [raw_by_id[item_id] for item_id in ids if item_id in raw_by_id]
        if not members:
            return
        aspect_types = {str(member.get("aspect_type")) for member in members}
        planets = sorted(
            {PLANET_RU.get(str(member.get("planet_a")), str(member.get("planet_a"))) for member in members}
            | {PLANET_RU.get(str(member.get("planet_b")), str(member.get("planet_b"))) for member in members}
        )
        pattern_type = (
            "integration"
            if {"square", "opposition"} & aspect_types and {"trine", "sextile"} & aspect_types
            else _pattern_type(next(iter(aspect_types)))
        )
        weight = round(max(item.weight for item in ranked_aspects if item.id in ids), 4)
        patterns.append(
            AspectPattern(
                id=pattern_id,
                title=title,
                aspect_ids=ids,
                planets=planets,
                pattern_type=pattern_type,
                psychological_mechanism=(
                    f"Паттерн {title.lower()} связывает повторяющийся способ внутренней обработки опыта."
                ),
                life_manifestation=(
                    "Это проявляется в повторяемой манере реагировать, связывать переживание и действие."
                ),
                risk="Под нагрузкой этот паттерн может уходить в автоматизм и односторонность.",
                mature_expression=(
                    "В зрелой форме он становится более осознанным способом интеграции разных частей личности."
                ),
                section_targets=section_targets,
                evidence_ids=ids,
                weight=weight,
            )
        )

    moon_mercury_ids = [
        item_id for item_id in high_signal_ids if item_id.startswith("moon_") and item_id.endswith("_mercury")
    ]
    build_pattern(
        "moon_mercury_pattern",
        "Эмоционально-когнитивная связка",
        moon_mercury_ids,
        ["emotions_and_communication", "world_perception"],
    )

    venus_mars_ids = [item_id for item_id in high_signal_ids if "venus_" in item_id and item_id.endswith("_mars")]
    build_pattern(
        "venus_mars_pattern",
        "Паттерн притяжения и напряжения в близости",
        venus_mars_ids,
        ["relationships", "sexuality"],
    )

    saturn_ids = [item_id for item_id in high_signal_ids if "saturn" in item_id]
    build_pattern(
        "saturn_boundary_pattern",
        "Паттерн границ, зрелости и внутреннего давления",
        saturn_ids,
        ["development", "vulnerabilities"],
    )

    return patterns
