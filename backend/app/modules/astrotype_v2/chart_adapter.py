"""Adapter from chart-engine output to Astrotype v2 normalized ORM rows."""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.chart_engine.features import SIGN_ELEMENTS, SIGN_MODALITIES
from app.chart_engine.types import ChartData
from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.reference_data import canonicalize_body_pair


@dataclass(frozen=True, slots=True)
class NatalChartRows:
    """V2 ORM row bundle built from one chart-engine result, before persistence."""

    chart: models.NatalChart
    planet_positions: list[models.NatalPlanetPosition]
    houses: list[models.NatalHouse]
    aspects: list[models.NatalAspect]
    balances: list[models.NatalChartBalance]
    patterns: list[models.NatalChartPattern]


def build_natal_chart_rows(
    *,
    chart_data: ChartData,
    user_id: uuid.UUID,
    profile_id: uuid.UUID,
    engine_version: str,
    input_hash: str,
) -> NatalChartRows:
    """Convert chart-engine data into v2 natal-only ORM rows without persisting them."""
    chart = models.NatalChart(
        user_id=user_id,
        profile_id=profile_id,
        engine_version=engine_version,
        input_hash=input_hash,
        birth_datetime_utc=chart_data.birth_datetime,
        timezone=chart_data.timezone,
        latitude=chart_data.latitude,
        longitude=chart_data.longitude,
        house_system=chart_data.house_system,
        calculation_payload={"ayanamsa": chart_data.ayanamsa},
    )

    planet_positions = [
        models.NatalPlanetPosition(
            chart_id=chart.id,
            body=planet.name,
            longitude=planet.longitude,
            latitude=planet.latitude,
            speed=planet.speed,
            sign=planet.sign,
            sign_degree=planet.sign_degree,
            house_number=planet.house,
            retrograde=planet.is_retrograde,
        )
        for planet in chart_data.planets
    ]

    houses = [
        models.NatalHouse(
            chart_id=chart.id,
            house_number=house.number,
            longitude=house.longitude,
            sign=house.sign,
        )
        for house in chart_data.houses
    ]

    aspects = [
        models.NatalAspect(
            chart_id=chart.id,
            body_a=body_a,
            body_b=body_b,
            aspect_code=aspect.aspect_type,
            angle_degrees=aspect.angle,
            orb_degrees=aspect.orb,
            applying=aspect.is_applying,
            strength=_aspect_strength(aspect.orb),
        )
        for aspect in chart_data.aspects
        for body_a, body_b in [canonicalize_body_pair(aspect.planet_a, aspect.planet_b)]
    ]

    balances = _build_balance_rows(chart.id, chart_data)
    patterns = _build_pattern_rows(chart.id, balances)

    return NatalChartRows(
        chart=chart,
        planet_positions=planet_positions,
        houses=houses,
        aspects=aspects,
        balances=balances,
        patterns=patterns,
    )


def _aspect_strength(orb_degrees: float) -> float:
    """Return a simple deterministic strength score in [0, 1]."""
    return round(max(0.0, min(1.0, 1.0 - abs(orb_degrees) / 12.0)), 3)


def _build_balance_rows(chart_id: uuid.UUID, chart_data: ChartData) -> list[models.NatalChartBalance]:
    rows: list[models.NatalChartBalance] = []
    element_counts: Counter[str] = Counter()
    modality_counts: Counter[str] = Counter()
    house_counts: Counter[int] = Counter()

    for planet in chart_data.planets:
        element_counts[SIGN_ELEMENTS.get(planet.sign, "unknown")] += 1
        modality_counts[SIGN_MODALITIES.get(planet.sign, "unknown")] += 1
        if planet.house is not None:
            house_counts[planet.house] += 1

    rows.extend(_counter_to_balance_rows(chart_id, "element", element_counts))
    rows.extend(_counter_to_balance_rows(chart_id, "modality", modality_counts))
    rows.extend(_counter_to_balance_rows(chart_id, "house", house_counts))
    return rows


def _counter_to_balance_rows(
    chart_id: uuid.UUID,
    category: str,
    counter: Counter[Any],
) -> list[models.NatalChartBalance]:
    total = sum(counter.values()) or 1
    sorted_items = sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    return [
        models.NatalChartBalance(
            chart_id=chart_id,
            category=category,
            key=str(key),
            value=round(count / total, 3),
            rank=index + 1,
        )
        for index, (key, count) in enumerate(sorted_items)
        if key != "unknown"
    ]


def _build_pattern_rows(
    chart_id: uuid.UUID,
    balances: list[models.NatalChartBalance],
) -> list[models.NatalChartPattern]:
    rows: list[models.NatalChartPattern] = []
    for balance in balances:
        if balance.rank == 1 and balance.value >= 0.5:
            rows.append(
                models.NatalChartPattern(
                    chart_id=chart_id,
                    pattern_code=f"emphasis_{balance.category}_{balance.key}",
                    label=f"{balance.category} emphasis: {balance.key}",
                    weight=balance.value,
                    evidence={"category": balance.category, "key": balance.key, "value": balance.value},
                )
            )
    return rows
