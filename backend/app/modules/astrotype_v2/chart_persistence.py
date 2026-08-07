"""Persistence helpers for Astrotype v2 normalized chart rows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.core.models import BaseModel
from app.modules.astrotype_v2.chart_adapter import NatalChartRows


class SupportsV2Repository(Protocol):
    """Repository protocol used by chart persistence helpers."""

    async def add(self, instance: BaseModel) -> BaseModel:
        """Add one v2 row to the current unit of work."""
        ...

    async def add_many(self, instances: Sequence[BaseModel]) -> Sequence[BaseModel]:
        """Add several v2 rows to the current unit of work."""
        ...

    async def flush(self) -> None:
        """Flush pending rows without committing."""
        ...


async def persist_natal_chart_rows(
    repository: SupportsV2Repository,
    rows: NatalChartRows,
) -> NatalChartRows:
    """Persist one complete normalized v2 natal chart row bundle through the repository."""
    await repository.add(rows.chart)
    await repository.add_many(rows.planet_positions)
    await repository.add_many(rows.houses)
    await repository.add_many(rows.aspects)
    await repository.add_many(rows.balances)
    await repository.add_many(rows.patterns)
    await repository.flush()
    return rows
