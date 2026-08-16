"""Astrotype v2 report generation background tasks."""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime, time
from typing import Any, cast
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.chart_engine.chart import build_chart
from app.infrastructure.celery_async import run_async_in_worker
from app.infrastructure.database import async_session_factory
from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.chart_adapter import build_natal_chart_rows
from app.modules.astrotype_v2.chart_persistence import persist_natal_chart_rows
from app.modules.astrotype_v2.fact_extractor import (
    build_aspect_fact_rows,
    build_balance_pattern_fact_rows,
    build_placement_fact_rows,
)
from app.modules.astrotype_v2.infographic_data import build_natal_infographic_data_row
from app.modules.astrotype_v2.outline import build_report_outline_row
from app.modules.astrotype_v2.report_assembler import build_natal_report_row
from app.modules.astrotype_v2.repository import AstrotypeV2Repository
from app.modules.astrotype_v2.schemas import ReportSegmentOutputV2
from app.modules.astrotype_v2.synthesis import NatalSynthesisV2, build_natal_synthesis_row
from app.modules.profiles.models import PersonProfile
from workers.celery_app import app

_SOURCE_VERSION = "v2.0"
_ENGINE_VERSION = "0.1.5"
_PROMPT_VERSION = "astrotype_v2_deterministic_local_v1"
_PROVIDER = "deterministic"
_MODEL = "v2-local-runtime"


@app.task(name="astrotype_v2.generate_natal_report", bind=True)  # type: ignore[untyped-decorator]
def generate_natal_report_v2(
    self: object,
    *,
    profile_id: str,
    user_id: str,
    generation_id: str,
    force: bool = False,
) -> dict[str, Any]:
    """Run the v2 generation pipeline outside the request lifecycle."""

    return run_async_in_worker(
        _generate_natal_report_v2_async(
            profile_id=profile_id,
            user_id=user_id,
            generation_id=generation_id,
            force=force,
        )
    )


async def _generate_natal_report_v2_async(
    *,
    profile_id: str,
    user_id: str,
    generation_id: str,
    force: bool,
) -> dict[str, Any]:
    """Build and persist a ready natal-only v2 report for one owned profile."""

    profile_uuid = uuid.UUID(profile_id)
    user_uuid = uuid.UUID(user_id)
    async with async_session_factory() as db:
        repository = AstrotypeV2Repository(db)
        try:
            existing_report = await repository.get_latest_report_for_profile(
                profile_id=profile_uuid,
                user_id=user_uuid,
            )
            if existing_report is not None and not force:
                return _task_payload(
                    generation_id=generation_id,
                    profile_id=profile_uuid,
                    report=existing_report,
                    status="already_exists",
                    force=force,
                )
            if not force:
                existing_report = await _wait_for_existing_report(
                    repository=repository,
                    profile_id=profile_uuid,
                    user_id=user_uuid,
                )
                if existing_report is not None:
                    return _task_payload(
                        generation_id=generation_id,
                        profile_id=profile_uuid,
                        report=existing_report,
                        status="already_exists",
                        force=force,
                    )

            profile = await _load_profile(db, profile_id=profile_uuid, user_id=user_uuid)
            chart = await _get_or_create_chart(repository=repository, profile=profile, user_id=user_uuid)
            positions = await repository.list_planet_positions_for_chart(chart.id)
            houses = await repository.list_houses_for_chart(chart.id)
            aspects = await repository.list_aspects_for_chart(chart.id)
            balances = await repository.list_balances_for_chart(chart.id)
            patterns = await repository.list_patterns_for_chart(chart.id)

            facts = await repository.list_facts_for_chart(chart.id)
            if not facts:
                facts, evidence = await _create_fact_rows(
                    repository=repository,
                    chart_id=chart.id,
                    positions=positions,
                    aspects=aspects,
                    balances=balances,
                    patterns=patterns,
                )
            else:
                evidence = [row for fact in facts for row in await repository.list_fact_evidence(fact.id)]

            synthesis = await repository.get_synthesis_for_chart(chart.id)
            if synthesis is None:
                synthesis = build_natal_synthesis_row(
                    chart_id=chart.id,
                    facts=facts,
                    facts_version=f"facts:{_SOURCE_VERSION}",
                    source_version=_SOURCE_VERSION,
                )
                await repository.add(synthesis)
                await repository.flush()

            outline = await repository.get_outline_for_chart(chart.id)
            if outline is None:
                outline = build_report_outline_row(
                    synthesis=_synthesis_contract(chart.id, synthesis),
                    source_version=_SOURCE_VERSION,
                )
                await repository.add(outline)
                await repository.flush()

            infographic = await repository.get_infographic_data_for_chart(chart.id)
            if infographic is None:
                infographic = build_natal_infographic_data_row(
                    chart_id=chart.id,
                    positions=positions,
                    houses=houses,
                    aspects=aspects,
                    balances=balances,
                    facts=facts,
                    evidence=evidence,
                    source_version=_SOURCE_VERSION,
                )
                await repository.add(infographic)
                await repository.flush()

            segments = await _ensure_ready_segments(
                repository=repository,
                chart_id=chart.id,
                outline=outline,
                synthesis=_synthesis_contract(chart.id, synthesis),
            )
            latest_report = await repository.get_latest_report_for_chart(chart.id)
            report = build_natal_report_row(
                chart_id=chart.id,
                synthesis_row=synthesis,
                outline_row=outline,
                infographic_row=infographic,
                segment_rows=segments,
                previous_version=latest_report.version if latest_report is not None else 0,
            )
            await repository.add(report)
            await repository.flush()
            await db.commit()
            return _task_payload(
                generation_id=generation_id,
                profile_id=profile_uuid,
                report=report,
                status="ready",
                force=force,
            )
        except Exception:
            await db.rollback()
            raise


async def _load_profile(db: Any, *, profile_id: uuid.UUID, user_id: uuid.UUID) -> PersonProfile:
    result = await db.execute(
        select(PersonProfile).where(PersonProfile.id == profile_id, PersonProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise ValueError("Profile not found")
    return cast(PersonProfile, profile)


async def _wait_for_existing_report(
    *,
    repository: AstrotypeV2Repository,
    profile_id: uuid.UUID,
    user_id: uuid.UUID,
) -> models.NatalReport | None:
    """Give an in-flight force generation a chance to commit before non-force work starts."""

    for _ in range(10):
        await asyncio.sleep(0.25)
        existing_report = await repository.get_latest_report_for_profile(profile_id=profile_id, user_id=user_id)
        if existing_report is not None:
            return existing_report
    return None


async def _get_or_create_chart(
    *,
    repository: AstrotypeV2Repository,
    profile: PersonProfile,
    user_id: uuid.UUID,
) -> models.NatalChart:
    birth_time = profile.birth_time or time(12, 0)
    local_tz = ZoneInfo(profile.timezone)
    birth_dt_local = datetime.combine(profile.birth_date, birth_time).replace(tzinfo=local_tz)
    birth_dt_utc = birth_dt_local.astimezone(UTC)
    input_payload = {
        "profile_id": str(profile.id),
        "birth_date": profile.birth_date.isoformat(),
        "birth_time": birth_time.isoformat(),
        "birth_time_accuracy": profile.birth_time_accuracy,
        "birth_place": profile.birth_place,
        "latitude": profile.latitude,
        "longitude": profile.longitude,
        "timezone": profile.timezone,
    }
    input_hash = _stable_hash(input_payload)
    existing_chart = await repository.get_chart_by_profile_engine_input(
        profile_id=profile.id,
        engine_version=_ENGINE_VERSION,
        input_hash=input_hash,
    )
    if existing_chart is not None:
        return existing_chart

    chart_data = build_chart(
        birth_datetime=birth_dt_utc,
        latitude=profile.latitude,
        longitude=profile.longitude,
        timezone_name=profile.timezone,
    )
    rows = build_natal_chart_rows(
        chart_data=chart_data,
        user_id=user_id,
        profile_id=profile.id,
        engine_version=_ENGINE_VERSION,
        input_hash=input_hash,
    )
    await persist_natal_chart_rows(repository, rows)
    return rows.chart


async def _create_fact_rows(
    *,
    repository: AstrotypeV2Repository,
    chart_id: uuid.UUID,
    positions: list[models.NatalPlanetPosition],
    aspects: list[models.NatalAspect],
    balances: list[models.NatalChartBalance],
    patterns: list[models.NatalChartPattern],
) -> tuple[list[models.NatalFact], list[models.NatalFactEvidence]]:
    placement_facts, placement_evidence = build_placement_fact_rows(chart_id=chart_id, positions=positions)
    balance_facts, balance_evidence = build_balance_pattern_fact_rows(
        chart_id=chart_id,
        balances=balances,
        patterns=patterns,
    )
    aspect_facts, aspect_evidence = await build_aspect_fact_rows(
        repository,
        chart_id=chart_id,
        aspects=aspects,
    )
    facts = [*placement_facts, *balance_facts, *aspect_facts]
    evidence = [*placement_evidence, *balance_evidence, *aspect_evidence]
    await repository.add_many(facts)
    await repository.add_many(evidence)
    await repository.flush()
    return facts, evidence


async def _ensure_ready_segments(
    *,
    repository: AstrotypeV2Repository,
    chart_id: uuid.UUID,
    outline: models.ReportOutline,
    synthesis: NatalSynthesisV2,
) -> list[models.ReportSegmentGeneration]:
    existing_segments = await repository.list_segments_for_outline(outline.id)
    by_key = {segment.section_key: segment for segment in existing_segments}
    section_plans = outline.outline.get("sections", []) if isinstance(outline.outline, dict) else []
    new_segments: list[models.ReportSegmentGeneration] = []
    for section in section_plans:
        section_id = str(section.get("id"))
        existing = by_key.get(section_id)
        output = _segment_output(section=section, synthesis=synthesis)
        response_payload = output.model_dump(mode="json")
        payload = {
            "request_hash": _stable_hash({"section": section}),
            "response_hash": _stable_hash(response_payload),
            "response": response_payload,
        }
        if existing is not None:
            existing.status = "ready"
            existing.provider = _PROVIDER
            existing.model = _MODEL
            existing.prompt_version = _PROMPT_VERSION
            existing.payload = payload
            existing.error = None
            continue
        new_segments.append(
            models.ReportSegmentGeneration(
                chart_id=chart_id,
                outline_id=outline.id,
                section_key=section_id,
                status="ready",
                provider=_PROVIDER,
                model=_MODEL,
                prompt_version=_PROMPT_VERSION,
                payload=payload,
                error=None,
            )
        )
    if new_segments:
        await repository.add_many(new_segments)
        await repository.flush()
        existing_segments = await repository.list_segments_for_outline(outline.id)
    return existing_segments


def _segment_output(*, section: dict[str, Any], synthesis: NatalSynthesisV2) -> ReportSegmentOutputV2:
    section_id = str(section.get("id"))
    title = str(section.get("title") or section_id.replace("_", " ").title())
    owned_theme_ids = [str(item) for item in section.get("owned_theme_ids", [])]
    if not owned_theme_ids and synthesis.dominant_themes:
        owned_theme_ids = [synthesis.dominant_themes[0].id]
    evidence_ids = [str(item) for item in section.get("evidence_ids", [])]
    if not evidence_ids and owned_theme_ids:
        theme_by_id = {theme.id: theme for theme in synthesis.dominant_themes}
        evidence_ids = list(theme_by_id.get(owned_theme_ids[0], synthesis.dominant_themes[0]).evidence_ids)
    theme_by_id = {theme.id: theme for theme in synthesis.dominant_themes}
    summaries = [theme_by_id[theme_id].summary for theme_id in owned_theme_ids if theme_id in theme_by_id]
    body_core = " ".join(summaries) or "Собран из детерминированных фактов натальной карты."
    body = f"{title}: {body_core}"
    return ReportSegmentOutputV2(
        section_id=section_id,
        title=title,
        body=body,
        covered_theme_ids=owned_theme_ids,
        evidence_ids=evidence_ids,
        continuation_complete=True,
        notes=["generated by local deterministic v2 worker"],
    )


def _synthesis_contract(chart_id: uuid.UUID, synthesis_row: models.NatalSynthesis) -> NatalSynthesisV2:
    payload = synthesis_row.payload
    return NatalSynthesisV2(
        chart_id=chart_id,
        source_version=str(payload.get("source_version", _SOURCE_VERSION)),
        dominant_themes=tuple(_theme_from_payload(item) for item in payload.get("dominant_themes", [])),
        tensions=tuple(_theme_from_payload(item) for item in payload.get("tensions", [])),
        resources=tuple(_theme_from_payload(item) for item in payload.get("resources", [])),
        growth_vectors=tuple(_theme_from_payload(item) for item in payload.get("growth_vectors", [])),
        input_fact_keys=list(payload.get("input_fact_keys", [])),
    )


def _theme_from_payload(payload: dict[str, Any]) -> Any:
    from app.modules.astrotype_v2.synthesis import SynthesisThemeV2

    return SynthesisThemeV2(
        id=str(payload["id"]),
        title=str(payload["title"]),
        summary=str(payload["summary"]),
        primary_section=str(payload["primary_section"]),
        fact_keys=tuple(str(item) for item in payload.get("fact_keys", [])),
        evidence_ids=tuple(str(item) for item in payload.get("evidence_ids", [])),
        weight=float(payload.get("weight", 0.0)),
        confidence=float(payload.get("confidence", 0.0)),
        polarity=payload.get("polarity"),
        fact_type=payload.get("fact_type"),
    )


def _task_payload(
    *,
    generation_id: str,
    profile_id: uuid.UUID,
    report: models.NatalReport,
    status: str,
    force: bool,
) -> dict[str, Any]:
    return {
        "contract_version": "astrotype_v2_generation_task_v1",
        "generation_id": generation_id,
        "profile_id": str(profile_id),
        "report_id": str(report.id),
        "status": status,
        "report_status": report.status,
        "force": force,
    }


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
