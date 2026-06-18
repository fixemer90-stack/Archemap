"""Reports service — orchestrates report generation, versioning, and retrieval."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chart_engine.features import extract_features
from app.core.exceptions import NotFoundError
from app.modules.charts.models import ChartSnapshot
from app.modules.charts.service import ChartService
from app.modules.profiles.models import PersonProfile
from app.modules.reports.models import Report, ReportVersion
from app.modules.rules.engine import RULE_ENGINE_VERSION, interpret
from app.modules.rules.loader import load_ruleset
from app.modules.rules.resolver import render_full_report

logger = structlog.get_logger()


class ReportService:
    """Service for generating and managing reports."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_report(
        self,
        profile_id: UUID,
        user_id: UUID,
        product: str = "self",
        mode: str = "full",
    ) -> Report:
        """Generate a report for a profile.

        1. Load or compute chart snapshot
        2. Run rule engine interpretation
        3. Build report data
        4. Persist report
        """
        # Check if report already exists for this profile + product
        existing = await self._find_existing(profile_id, user_id, product)
        supports_narrative = product == "self"
        if existing and existing.status in {"ready", "narrative_failed", "deterministic_ready"}:
            # Create new version
            await self._archive_version(existing)
            existing.version += 1
            existing.status = "generating"
            await self.db.flush()
            report = existing
        elif existing:
            report = existing
            report.status = "generating"
            await self.db.flush()
        else:
            report = Report(
                user_id=user_id,
                profile_id=profile_id,
                product=product,
                version=1,
                status="generating",
                mode=mode,
            )
            self.db.add(report)
            await self.db.flush()

        try:
            # Get chart snapshot
            chart_service = ChartService(self.db)
            snapshot = await chart_service.get_or_compute(profile_id, user_id)
            profile = await self._get_profile(profile_id, user_id)

            # Parse chart data
            chart_data = _dict_to_chart(snapshot.chart_data)
            features = extract_features(chart_data)

            # Run rule engine
            ruleset = load_ruleset(product, "v1")
            interpretation = interpret(features, ruleset, mode=mode)

            # Render with evidence templates
            render_full_report(
                result=interpretation,
                features=features.to_dict(),
                product=product,
                version="v1",
            )

            # Build chart summary for report
            chart_summary = _build_chart_summary(snapshot.chart_data, features.to_dict())

            # Build full report data
            report_data = {
                "product": product,
                "source_chart": {
                    "snapshot_id": str(snapshot.id),
                    "engine_version": snapshot.engine_version,
                },
                "profile": {
                    "name": profile.name,
                    "birth_date": profile.birth_date.isoformat(),
                    "birth_time": profile.birth_time.strftime("%H:%M") if profile.birth_time else None,
                    "birth_time_accuracy": profile.birth_time_accuracy,
                    "birth_place": profile.birth_place,
                    "timezone": profile.timezone,
                },
                "archetype": {
                    "primary": interpretation.primary_archetype,
                    "score": interpretation.primary_score,
                    "confidence": {
                        "value": interpretation.primary_confidence.value,
                        "label": interpretation.primary_confidence.label,
                        "reason_codes": interpretation.primary_confidence.reason_codes,
                    },
                },
                "claims": [
                    {
                        "claim_id": c.claim_id,
                        "section": c.section,
                        "archetype": c.archetype,
                        "score": c.score,
                        "confidence": {
                            "value": c.confidence.value,
                            "label": c.confidence.label,
                            "reason_codes": c.confidence.reason_codes,
                        },
                        "message": c.message,
                        "basis": [
                            {
                                "rule_id": b.rule_id,
                                "feature": b.feature,
                                "value": b.value,
                                "contribution": b.contribution,
                            }
                            for b in c.basis
                        ],
                        "counter_evidence": [
                            {
                                "rule_id": e.rule_id,
                                "feature": e.feature,
                                "value": e.value,
                                "contribution": e.contribution,
                            }
                            for e in c.counter_evidence
                        ],
                        "provenance": c.provenance,
                    }
                    for c in interpretation.claims
                ],
                "all_archetype_scores": interpretation.all_archetype_scores,
                "chart": chart_summary,
                "quality_warning": interpretation.quality_warning,
                "provenance": interpretation.provenance,
            }

            # Update report
            report.report_data = report_data
            report.archetype = interpretation.primary_archetype
            report.score = interpretation.primary_score
            report.confidence = interpretation.primary_confidence.value
            report.status = "deterministic_ready" if supports_narrative else "ready"
            report.error_message = None
            await self.db.flush()
            await self.db.refresh(report)

            logger.info(
                "report_generated",
                report_id=str(report.id),
                product=product,
                archetype=interpretation.primary_archetype,
                claims_count=len(interpretation.claims),
            )

        except Exception as e:
            report.status = "failed"
            report.error_message = str(e)
            await self.db.flush()
            logger.error("report_generation_failed", report_id=str(report.id), error=str(e))
            raise

        return report

    async def get_report(self, report_id: UUID, user_id: UUID) -> Report:
        """Get a report by ID."""
        result = await self.db.execute(select(Report).where(Report.id == report_id, Report.user_id == user_id))
        report = result.scalar_one_or_none()
        if report is None:
            raise NotFoundError("Report not found")
        if await self._report_requires_refresh(report, user_id):
            logger.info(
                "report_refresh_required",
                report_id=str(report.id),
                profile_id=str(report.profile_id),
                product=report.product,
                version=report.version,
            )
            return await self.generate_report(
                profile_id=report.profile_id,
                user_id=user_id,
                product=report.product,
                mode=report.mode,
            )
        return report

    async def list_reports(
        self,
        user_id: UUID,
        product: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[Report], int]:
        """List reports for a user with optional product filter."""
        query = select(Report).where(Report.user_id == user_id)
        count_query = select(func.count()).select_from(Report).where(Report.user_id == user_id)

        if product:
            query = query.where(Report.product == product)
            count_query = count_query.where(Report.product == product)

        query = query.order_by(Report.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        reports = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return reports, total

    async def get_versions(self, report_id: UUID, user_id: UUID) -> list[ReportVersion]:
        """Get version history for a report."""
        # Verify ownership
        report = await self.get_report(report_id, user_id)

        result = await self.db.execute(
            select(ReportVersion).where(ReportVersion.report_id == report.id).order_by(ReportVersion.version.desc())
        )
        return list(result.scalars().all())

    async def get_version(self, report_id: UUID, version: int, user_id: UUID) -> ReportVersion:
        """Get a specific version of a report."""
        # Verify ownership
        await self.get_report(report_id, user_id)

        result = await self.db.execute(
            select(ReportVersion).where(
                ReportVersion.report_id == report_id,
                ReportVersion.version == version,
            )
        )
        rv = result.scalar_one_or_none()
        if rv is None:
            raise NotFoundError("Report version not found")
        return rv

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

    async def _find_existing(self, profile_id: UUID, user_id: UUID, product: str) -> Report | None:
        """Find existing report for profile + user + product."""
        result = await self.db.execute(
            select(Report).where(
                Report.profile_id == profile_id,
                Report.user_id == user_id,
                Report.product == product,
            )
        )
        return result.scalars().first()

    async def _archive_version(self, report: Report) -> None:
        """Archive current report data as a version before regenerating."""
        if not report.report_data:
            return

        version = ReportVersion(
            report_id=report.id,
            version=report.version,
            report_data=report.report_data,
            pdf_url=report.pdf_url,
        )
        self.db.add(version)
        await self.db.flush()

    async def _report_requires_refresh(self, report: Report, user_id: UUID) -> bool:
        if report.status not in {"ready", "narrative_failed", "deterministic_ready"}:
            return False
        if not report.report_data:
            return True

        provenance = report.report_data.get("provenance", {})
        if provenance.get("engine_version") != RULE_ENGINE_VERSION:
            return True

        if report.product != "self":
            return False

        chart_service = ChartService(self.db)
        snapshot = await chart_service.get_or_compute(report.profile_id, user_id)
        return not _report_matches_snapshot(report.report_data, snapshot)


def _dict_to_chart(data: dict[str, Any]) -> Any:
    """Convert a chart dict back to ChartData for feature extraction."""
    from datetime import datetime

    from app.chart_engine.types import ZODIAC_SIGNS, Aspect, ChartData, HousePosition, PlanetPosition

    planets = []
    for p in data.get("planets", []):
        longitude = p.get("longitude", 0)
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

    houses = []
    for h in data.get("houses", []):
        houses.append(
            HousePosition(
                number=h["number"],
                longitude=h["longitude"],
                sign=h["sign"],
            )
        )

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
        house_system=data.get("house_system", "P"),
        ayanamsa=data.get("ayanamsa", 0.0),
    )


def _report_matches_snapshot(report_data: dict[str, Any], snapshot: ChartSnapshot) -> bool:
    """Return True when stored report data already reflects the latest chart snapshot."""

    source_chart = report_data.get("source_chart")
    if isinstance(source_chart, dict):
        snapshot_id = source_chart.get("snapshot_id")
        engine_version = source_chart.get("engine_version")
        if snapshot_id == str(snapshot.id) and engine_version == snapshot.engine_version:
            return True

    chart = report_data.get("chart")
    if not isinstance(chart, dict):
        return False

    return (
        chart.get("planets") == snapshot.chart_data.get("planets")
        and chart.get("houses") == snapshot.chart_data.get("houses")
        and chart.get("aspects") == snapshot.chart_data.get("aspects")
    )


def _build_chart_summary(chart_data: dict[str, Any], features: dict[str, Any]) -> dict[str, Any]:
    """Build chart summary for report response."""
    return {
        "birth_datetime": chart_data.get("birth_datetime"),
        "latitude": chart_data.get("latitude"),
        "longitude": chart_data.get("longitude"),
        "timezone": chart_data.get("timezone"),
        "house_system": chart_data.get("house_system", "P"),
        "ayanamsa": chart_data.get("ayanamsa", 0.0),
        "zodiac": "tropical" if not chart_data.get("ayanamsa") else "sidereal",
        "planets": chart_data.get("planets", []),
        "houses": chart_data.get("houses", []),
        "aspects": chart_data.get("aspects", []),
        "elements": {
            "fire": features.get("fire", 0),
            "earth": features.get("earth", 0),
            "air": features.get("air", 0),
            "water": features.get("water", 0),
        },
        "modalities": {
            "cardinal": features.get("cardinal", 0),
            "fixed": features.get("fixed", 0),
            "mutable": features.get("mutable", 0),
        },
    }
