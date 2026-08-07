"""Reload Astrotype v2 normalized chart rows into stable serializable contracts."""

from __future__ import annotations

import uuid
from typing import Any, Protocol

from app.modules.astrotype_v2 import models


class SupportsNatalChartContractRepository(Protocol):
    """Read-side repository protocol for v2 natal chart contracts."""

    async def get_chart(self, chart_id: uuid.UUID) -> models.NatalChart | None:
        """Return one v2 chart root row."""
        ...

    async def list_planet_positions_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalPlanetPosition]:
        """Return v2 planet rows."""
        ...

    async def list_houses_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalHouse]:
        """Return v2 house rows."""
        ...

    async def list_aspects_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalAspect]:
        """Return v2 aspect rows."""
        ...

    async def list_balances_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalChartBalance]:
        """Return v2 balance rows."""
        ...

    async def list_patterns_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalChartPattern]:
        """Return v2 pattern rows."""
        ...


async def load_natal_chart_contract(
    repository: SupportsNatalChartContractRepository,
    chart_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Load one v2 chart and its normalized children into an API/debug-safe dict."""
    chart = await repository.get_chart(chart_id)
    if chart is None:
        return None

    positions = await repository.list_planet_positions_for_chart(chart.id)
    houses = await repository.list_houses_for_chart(chart.id)
    aspects = await repository.list_aspects_for_chart(chart.id)
    balances = await repository.list_balances_for_chart(chart.id)
    patterns = await repository.list_patterns_for_chart(chart.id)

    return {
        "chart": _chart_to_contract(chart),
        "planet_positions": [_planet_position_to_contract(row) for row in positions],
        "houses": [_house_to_contract(row) for row in houses],
        "aspects": [_aspect_to_contract(row) for row in aspects],
        "balances": [_balance_to_contract(row) for row in balances],
        "patterns": [_pattern_to_contract(row) for row in patterns],
    }


def _chart_to_contract(row: models.NatalChart) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "user_id": str(row.user_id),
        "profile_id": str(row.profile_id),
        "engine_version": row.engine_version,
        "input_hash": row.input_hash,
        "birth_datetime_utc": row.birth_datetime_utc.isoformat(),
        "timezone": row.timezone,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "house_system": row.house_system,
        "calculation_payload": row.calculation_payload,
    }


def _planet_position_to_contract(row: models.NatalPlanetPosition) -> dict[str, Any]:
    return {
        "body": row.body,
        "longitude": row.longitude,
        "latitude": row.latitude,
        "speed": row.speed,
        "sign": row.sign,
        "sign_degree": row.sign_degree,
        "house_number": row.house_number,
        "retrograde": row.retrograde,
    }


def _house_to_contract(row: models.NatalHouse) -> dict[str, Any]:
    return {
        "house_number": row.house_number,
        "longitude": row.longitude,
        "sign": row.sign,
    }


def _aspect_to_contract(row: models.NatalAspect) -> dict[str, Any]:
    return {
        "body_a": row.body_a,
        "body_b": row.body_b,
        "aspect_code": row.aspect_code,
        "angle_degrees": row.angle_degrees,
        "orb_degrees": row.orb_degrees,
        "applying": row.applying,
        "strength": row.strength,
    }


def _balance_to_contract(row: models.NatalChartBalance) -> dict[str, Any]:
    return {
        "category": row.category,
        "key": row.key,
        "value": row.value,
        "rank": row.rank,
    }


def _pattern_to_contract(row: models.NatalChartPattern) -> dict[str, Any]:
    return {
        "pattern_code": row.pattern_code,
        "label": row.label,
        "weight": row.weight,
        "evidence": row.evidence,
    }
