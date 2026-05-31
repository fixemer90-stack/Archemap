"""Rules service — orchestrates rule loading, evaluation, and content resolution."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chart_engine.features import extract_features
from app.chart_engine.types import ChartData
from app.core.exceptions import NotFoundError
from app.modules.charts.models import ChartSnapshot
from app.modules.rules.engine import interpret
from app.modules.rules.loader import list_available_rulesets, load_ruleset
from app.modules.rules.resolver import render_full_report

logger = structlog.get_logger()


class RulesService:
    """Service for interpreting chart data through the rule engine."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def interpret_chart(
        self,
        profile_id: UUID,
        user_id: UUID,
        product: str = "self",
        ruleset_version: str = "v1",
        locale: str = "ru-RU",
        mode: str = "full",
    ) -> dict[str, Any]:
        """Interpret a chart snapshot through the rule engine.

        Args:
            profile_id: ID of the person profile
            user_id: ID of the user (for access control)
            product: Vertical (self, love, child, career)
            ruleset_version: Ruleset version suffix (v1, v2)
            locale: Locale for templates (ru-RU, en-US)
            mode: "full" or "preview"

        Returns:
            Rendered interpretation dict
        """
        # Load chart snapshot
        snapshot = await self._get_snapshot(profile_id, user_id)

        # Parse chart data back to ChartData
        chart_data = _dict_to_chart(snapshot.chart_data)

        # Extract features
        features = extract_features(chart_data)

        # Load ruleset
        ruleset = load_ruleset(product, ruleset_version)

        # Run rule engine
        result = interpret(features, ruleset, mode=mode)

        # Render with evidence templates
        rendered = render_full_report(
            result=result,
            features=features.to_dict(),
            product=product,
            version=ruleset_version,
        )

        logger.info(
            "interpretation_complete",
            profile_id=str(profile_id),
            product=product,
            archetypes_count=len(rendered.get("archetypes", [])),
            claims_count=len(rendered.get("claims", [])),
        )

        return rendered

    async def list_rulesets(self) -> list[dict[str, str]]:
        """List all available rulesets."""
        return list_available_rulesets()

    async def _get_snapshot(self, profile_id: UUID, user_id: UUID) -> ChartSnapshot:
        """Get chart snapshot by profile ID."""
        result = await self.db.execute(
            select(ChartSnapshot).where(
                ChartSnapshot.profile_id == profile_id,
                ChartSnapshot.user_id == user_id,
            )
        )
        snapshot = result.scalars().first()
        if snapshot is None:
            raise NotFoundError("Chart snapshot not found")
        return snapshot


def _dict_to_chart(data: dict[str, Any]) -> ChartData:
    """Convert a chart dict back to ChartData for feature extraction."""
    from datetime import datetime

    from app.chart_engine.types import ZODIAC_SIGNS, Aspect, ChartData, HousePosition, PlanetPosition

    # Parse planets — handle both stored format (sign_degree) and computed format (longitude)
    planets = []
    for p in data.get("planets", []):
        longitude = p.get("longitude", 0)
        # If no longitude, compute from sign + degree
        if longitude == 0 and "sign" in p and "degree" in p:
            sign_index = ZODIAC_SIGNS.index(p["sign"]) if p["sign"] in ZODIAC_SIGNS else 0
            longitude = sign_index * 30 + p.get("degree", 0)
        planets.append(
            PlanetPosition(
                name=p["name"],
                longitude=longitude,
                latitude=p.get("latitude", 0),
                speed=p.get("speed", 0),
                sign=p.get("sign", ""),
                sign_degree=p.get("degree", p.get("sign_degree", 0)),
                house=p.get("house"),
            )
        )

    # Parse houses
    houses = []
    for h in data.get("houses", []):
        houses.append(
            HousePosition(
                number=h["number"],
                longitude=h["longitude"],
                sign=h["sign"],
            )
        )

    # Parse aspects
    aspects = []
    for a in data.get("aspects", []):
        aspects.append(
            Aspect(
                planet_a=a["planet_a"],
                planet_b=a["planet_b"],
                aspect_type=a["aspect_type"],
                angle=a.get("angle", 0),
                orb=a.get("orb", 0),
                is_applying=a.get("is_applying", False),
            )
        )

    # Parse birth datetime
    birth_dt_str = data.get("birth_datetime", "")
    try:
        birth_dt = datetime.fromisoformat(birth_dt_str)
    except (ValueError, TypeError):
        birth_dt = datetime.min

    return ChartData(
        birth_datetime=birth_dt,
        latitude=data.get("latitude", 0),
        longitude=data.get("longitude", 0),
        timezone=data.get("timezone", "UTC"),
        planets=planets,
        houses=houses,
        aspects=aspects,
    )
