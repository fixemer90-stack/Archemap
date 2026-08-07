"""Async repository layer for the Astrotype v2 bounded context."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import BaseModel
from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.reference_data import canonicalize_body_pair

_V2Model = TypeVar("_V2Model", bound=BaseModel)


class AstrotypeV2Repository:
    """Persistence boundary for v2 natal chart, fact, synthesis, and report artifacts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, instance: _V2Model) -> _V2Model:
        """Add one v2 model instance to the current unit of work."""
        self.session.add(instance)
        return instance

    async def add_many(self, instances: Sequence[_V2Model]) -> Sequence[_V2Model]:
        """Add several v2 model instances to the current unit of work."""
        self.session.add_all(list(instances))
        return instances

    async def flush(self) -> None:
        """Flush the current unit of work without committing it."""
        await self.session.flush()

    async def list_aspect_definitions(self) -> list[models.AspectDefinition]:
        """Return canonical v2 aspect type definitions."""
        result = await self.session.execute(
            select(models.AspectDefinition).order_by(models.AspectDefinition.sort_order)
        )
        return list(result.scalars().all())

    async def get_aspect_definition(self, code: str) -> models.AspectDefinition | None:
        """Return one canonical v2 aspect type definition by code."""
        result = await self.session.execute(
            select(models.AspectDefinition).where(models.AspectDefinition.code == code)
        )
        return result.scalar_one_or_none()

    async def get_aspect_pair_interpretation(
        self,
        *,
        aspect_code: str,
        planet_a: str,
        planet_b: str,
        locale: str = "ru",
        source_version: str = "v2.0",
    ) -> models.AspectPairInterpretation | None:
        """Return one enabled v2 pair interpretation by canonical pair/version key."""
        canonical_planet_a, canonical_planet_b = canonicalize_body_pair(planet_a, planet_b)
        result = await self.session.execute(
            select(models.AspectPairInterpretation).where(
                models.AspectPairInterpretation.aspect_code == aspect_code,
                models.AspectPairInterpretation.planet_a == canonical_planet_a,
                models.AspectPairInterpretation.planet_b == canonical_planet_b,
                models.AspectPairInterpretation.locale == locale,
                models.AspectPairInterpretation.source_version == source_version,
                models.AspectPairInterpretation.enabled.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_chart(self, chart_id: uuid.UUID) -> models.NatalChart | None:
        """Return one v2 natal chart by id."""
        result = await self.session.execute(select(models.NatalChart).where(models.NatalChart.id == chart_id))
        return result.scalar_one_or_none()

    async def get_chart_by_profile_engine_input(
        self,
        *,
        profile_id: uuid.UUID,
        engine_version: str,
        input_hash: str,
    ) -> models.NatalChart | None:
        """Return the v2 chart row for the profile/engine/input idempotency key."""
        result = await self.session.execute(
            select(models.NatalChart).where(
                models.NatalChart.profile_id == profile_id,
                models.NatalChart.engine_version == engine_version,
                models.NatalChart.input_hash == input_hash,
            )
        )
        return result.scalar_one_or_none()

    async def list_planet_positions_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalPlanetPosition]:
        """Return v2 planet/body positions for one chart."""
        result = await self.session.execute(
            select(models.NatalPlanetPosition)
            .where(models.NatalPlanetPosition.chart_id == chart_id)
            .order_by(models.NatalPlanetPosition.body)
        )
        return list(result.scalars().all())

    async def list_houses_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalHouse]:
        """Return v2 house cusps for one chart."""
        result = await self.session.execute(
            select(models.NatalHouse)
            .where(models.NatalHouse.chart_id == chart_id)
            .order_by(models.NatalHouse.house_number)
        )
        return list(result.scalars().all())

    async def list_aspects_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalAspect]:
        """Return v2 aspects for one chart."""
        result = await self.session.execute(
            select(models.NatalAspect)
            .where(models.NatalAspect.chart_id == chart_id)
            .order_by(models.NatalAspect.body_a, models.NatalAspect.body_b, models.NatalAspect.aspect_code)
        )
        return list(result.scalars().all())

    async def list_balances_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalChartBalance]:
        """Return v2 deterministic balance rows for one chart."""
        result = await self.session.execute(
            select(models.NatalChartBalance)
            .where(models.NatalChartBalance.chart_id == chart_id)
            .order_by(models.NatalChartBalance.category, models.NatalChartBalance.rank, models.NatalChartBalance.key)
        )
        return list(result.scalars().all())

    async def list_patterns_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalChartPattern]:
        """Return v2 deterministic pattern rows for one chart."""
        result = await self.session.execute(
            select(models.NatalChartPattern)
            .where(models.NatalChartPattern.chart_id == chart_id)
            .order_by(models.NatalChartPattern.pattern_code)
        )
        return list(result.scalars().all())

    async def list_facts_for_chart(self, chart_id: uuid.UUID) -> list[models.NatalFact]:
        """Return deterministic facts for one v2 chart."""
        result = await self.session.execute(
            select(models.NatalFact)
            .where(models.NatalFact.chart_id == chart_id)
            .order_by(models.NatalFact.section_hint, models.NatalFact.fact_type, models.NatalFact.fact_key)
        )
        return list(result.scalars().all())

    async def list_fact_evidence(self, fact_id: uuid.UUID) -> list[models.NatalFactEvidence]:
        """Return deterministic source links for one v2 fact."""
        result = await self.session.execute(
            select(models.NatalFactEvidence)
            .where(models.NatalFactEvidence.fact_id == fact_id)
            .order_by(models.NatalFactEvidence.source_table, models.NatalFactEvidence.source_key)
        )
        return list(result.scalars().all())

    async def get_synthesis_for_chart(self, chart_id: uuid.UUID) -> models.NatalSynthesis | None:
        """Return the deterministic synthesis for one v2 chart."""
        result = await self.session.execute(
            select(models.NatalSynthesis)
            .where(models.NatalSynthesis.chart_id == chart_id)
            .order_by(models.NatalSynthesis.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_outline_for_chart(self, chart_id: uuid.UUID) -> models.ReportOutline | None:
        """Return the latest deterministic report outline for one v2 chart."""
        result = await self.session.execute(
            select(models.ReportOutline)
            .where(models.ReportOutline.chart_id == chart_id)
            .order_by(models.ReportOutline.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_segments_for_outline(self, outline_id: uuid.UUID) -> list[models.ReportSegmentGeneration]:
        """Return all section generation artifacts for one v2 report outline."""
        result = await self.session.execute(
            select(models.ReportSegmentGeneration)
            .where(models.ReportSegmentGeneration.outline_id == outline_id)
            .order_by(models.ReportSegmentGeneration.section_key)
        )
        return list(result.scalars().all())

    async def get_infographic_data_for_chart(self, chart_id: uuid.UUID) -> models.NatalInfographicData | None:
        """Return latest deterministic calculation-layer data for one v2 chart."""
        result = await self.session.execute(
            select(models.NatalInfographicData)
            .where(models.NatalInfographicData.chart_id == chart_id)
            .order_by(models.NatalInfographicData.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_report(self, report_id: uuid.UUID) -> models.NatalReport | None:
        """Return one v2 report artifact by id."""
        result = await self.session.execute(select(models.NatalReport).where(models.NatalReport.id == report_id))
        return result.scalar_one_or_none()

    async def get_latest_report_for_chart(self, chart_id: uuid.UUID) -> models.NatalReport | None:
        """Return the newest versioned v2 report artifact for one chart."""
        result = await self.session.execute(
            select(models.NatalReport)
            .where(models.NatalReport.chart_id == chart_id)
            .order_by(models.NatalReport.version.desc(), models.NatalReport.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
