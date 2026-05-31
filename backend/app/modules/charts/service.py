"""Chart snapshot service — compute, persist, and retrieve chart data."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chart_engine.chart import build_chart
from app.chart_engine.features import extract_features
from app.chart_engine.socionics import evaluate_socionics
from app.chart_engine.types import ChartData
from app.core.exceptions import NotFoundError
from app.modules.charts.models import ChartSnapshot
from app.modules.profiles.models import PersonProfile

logger = structlog.get_logger()

ENGINE_VERSION = "0.1.0"


class ChartService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_compute(
        self,
        profile_id: UUID,
        user_id: UUID,
        force_recompute: bool = False,
    ) -> ChartSnapshot:
        """Get existing snapshot or compute a new one.

        If a snapshot exists for this profile + engine version,
        returns it (unless force_recompute=True).
        """
        if not force_recompute:
            existing = await self._find_existing(profile_id, user_id)
            if existing:
                logger.info("chart_cache_hit", profile_id=str(profile_id))
                return existing

        # Load profile
        profile = await self._get_profile(profile_id, user_id)

        # Build chart
        birth_dt = datetime.combine(profile.birth_date, profile.birth_time or datetime.min.time())
        birth_dt = birth_dt.replace(tzinfo=UTC)

        chart_data = build_chart(
            birth_datetime=birth_dt,
            latitude=profile.latitude,
            longitude=profile.longitude,
            timezone_name=profile.timezone,
        )

        # Extract features and compute socionics
        features = extract_features(chart_data)
        socionics_results = evaluate_socionics(features, chart_data)

        # Serialize
        chart_dict = _chart_to_dict(chart_data)

        # Prepare socionics data
        socionics_data = {
            "top3": [
                {
                    "type": r.type_code,
                    "name": r.type_name,
                    "score": round(r.score, 3),
                    "confidence": round(r.confidence, 3),
                    "functions": r.functions,
                    "model_a": round(r.score * 0.85, 3),  # approximate model_a
                }
                for r in socionics_results[:3]
            ],
        }

        # Function strengths
        function_strengths = {
            "Se": round(features.fire * 0.5 + features.cardinal * 0.3, 3),
            "Si": round(features.earth * 0.5 + features.fixed * 0.3, 3),
            "Ne": round(features.air * 0.5 + features.mutable * 0.3, 3),
            "Ni": round(features.water * 0.5 + features.mutable * 0.3, 3),
            "Fe": round(features.water * 0.4 + features.cardinal * 0.3, 3),
            "Fi": round(features.fire * 0.4 + features.fixed * 0.3, 3),
            "Te": round(features.air * 0.4 + features.cardinal * 0.3, 3),
            "Ti": round(features.earth * 0.4 + features.fixed * 0.3, 3),
        }

        # Persist
        snapshot = ChartSnapshot(
            profile_id=profile_id,
            user_id=user_id,
            engine_version=ENGINE_VERSION,
            chart_data=chart_dict,
            socionics=socionics_data,
            function_strengths=function_strengths,
        )
        self.db.add(snapshot)
        await self.db.flush()
        await self.db.refresh(snapshot)

        logger.info(
            "chart_computed",
            profile_id=str(profile_id),
            engine_version=ENGINE_VERSION,
            planets=len(chart_data.planets),
            aspects=len(chart_data.aspects),
        )
        return snapshot

    async def get_by_id(self, snapshot_id: UUID, user_id: UUID) -> ChartSnapshot:
        result = await self.db.execute(
            select(ChartSnapshot).where(
                ChartSnapshot.id == snapshot_id,
                ChartSnapshot.user_id == user_id,
            )
        )
        snapshot = result.scalar_one_or_none()
        if snapshot is None:
            raise NotFoundError("Chart snapshot not found")
        return snapshot

    async def list_by_profile(self, profile_id: UUID, user_id: UUID) -> list[ChartSnapshot]:
        result = await self.db.execute(
            select(ChartSnapshot)
            .where(ChartSnapshot.profile_id == profile_id, ChartSnapshot.user_id == user_id)
            .order_by(ChartSnapshot.created_at.desc())
        )
        return list(result.scalars().all())

    # ── internals ─────────────────────────────────────────────────────
    async def _find_existing(self, profile_id: UUID, user_id: UUID) -> ChartSnapshot | None:
        result = await self.db.execute(
            select(ChartSnapshot).where(
                ChartSnapshot.profile_id == profile_id,
                ChartSnapshot.user_id == user_id,
                ChartSnapshot.engine_version == ENGINE_VERSION,
            )
        )
        return result.scalars().first()

    async def _get_profile(self, profile_id: UUID, user_id: UUID) -> PersonProfile:
        result = await self.db.execute(
            select(PersonProfile).where(
                PersonProfile.id == profile_id,
                PersonProfile.user_id == user_id,
            )
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise NotFoundError("Profile not found")
        return profile


def _chart_to_dict(chart: ChartData) -> dict[str, Any]:
    """Serialize ChartData to a JSON-compatible dict."""
    return {
        "birth_datetime": chart.birth_datetime.isoformat(),
        "latitude": chart.latitude,
        "longitude": chart.longitude,
        "timezone": chart.timezone,
        "house_system": chart.house_system,
        "planets": [
            {
                "name": p.name,
                "longitude": round(p.longitude, 4),
                "latitude": round(p.latitude, 4),
                "speed": round(p.speed, 4),
                "sign": p.sign,
                "sign_degree": round(p.sign_degree, 2),
                "house": p.house,
                "is_retrograde": p.is_retrograde,
            }
            for p in chart.planets
        ],
        "houses": [{"number": h.number, "longitude": round(h.longitude, 4), "sign": h.sign} for h in chart.houses],
        "aspects": [
            {
                "planet_a": a.planet_a,
                "planet_b": a.planet_b,
                "aspect_type": a.aspect_type,
                "angle": round(a.angle, 2),
                "orb": round(a.orb, 2),
                "is_applying": a.is_applying,
            }
            for a in chart.aspects
        ],
    }
