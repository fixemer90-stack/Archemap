"""Astrotype v2 report API endpoints."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.api_runtime import (
    build_generation_status_payload,
    build_report_progress_v2,
    build_report_read_payload_v2,
    enqueue_v2_report_generation,
)
from app.modules.astrotype_v2.fact_view import build_fact_evidence_payload
from app.modules.astrotype_v2.infographic_data import build_infographic_api_payload_v2
from app.modules.astrotype_v2.repository import AstrotypeV2Repository
from app.modules.profiles.models import PersonProfile

router = APIRouter(prefix="/astrotype-v2", tags=["astrotype-v2"])


class GenerateV2ReportRequest(BaseModel):
    profile_id: UUID
    force: bool = False


class RegenerateV2ReportRequest(BaseModel):
    force: bool = True


@router.post("/reports", status_code=status.HTTP_202_ACCEPTED)
async def generate_v2_report(
    body: GenerateV2ReportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> JSONResponse:
    """Queue v2 report generation for a profile owned by the current user."""

    repository = AstrotypeV2Repository(db)
    latest_report = await repository.get_latest_report_for_profile(profile_id=body.profile_id, user_id=current_user)
    if latest_report is not None and not body.force:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "contract_version": "astrotype_v2_generation_job_v1",
                "status": "already_exists",
                "profile_id": str(body.profile_id),
                "report_id": str(latest_report.id),
                "links": {"report": f"/api/v1/astrotype-v2/reports/{latest_report.id}"},
            },
        )

    from workers.tasks.astrotype_v2 import generate_natal_report_v2

    response = enqueue_v2_report_generation(
        profile_id=body.profile_id,
        user_id=current_user,
        queue=generate_natal_report_v2,
        force=body.force,
    )
    return JSONResponse(status_code=response.status_code, content=response.payload)


@router.get("/reports/generations/{generation_id}")
async def get_v2_generation_status(
    generation_id: UUID,
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> dict[str, Any]:
    """Return coarse status for an accepted generation id."""

    _ = current_user
    return build_generation_status_payload(generation_id=generation_id)


@router.get("/reports/{report_id}")
async def get_v2_report(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> dict[str, Any]:
    """Return the full v2 report payload for its owner."""

    repository = AstrotypeV2Repository(db)
    report = await _load_report_for_user(repository=repository, report_id=report_id, user_id=current_user)
    outline = await repository.get_outline_for_chart(report.chart_id)
    chart = await repository.get_chart(report.chart_id)
    profile = await _load_profile(db=db, chart=chart, user_id=current_user)
    infographic = await repository.get_infographic_data_for_chart(report.chart_id)
    facts = await repository.list_facts_for_chart(report.chart_id)
    evidence = [row for fact in facts for row in await repository.list_fact_evidence(fact.id)]
    segments = await repository.list_segments_for_outline(outline.id) if outline is not None else []
    return build_report_read_payload_v2(
        report=report,
        outline=outline,
        infographic=infographic,
        facts=build_fact_evidence_payload(facts=facts, evidence=evidence),
        segments=segments,
        profile=profile,
    )


@router.get("/reports/{report_id}/progress")
async def get_v2_report_progress(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> dict[str, Any]:
    """Return segment-level generation progress for polling clients."""

    repository = AstrotypeV2Repository(db)
    report = await _load_report_for_user(repository=repository, report_id=report_id, user_id=current_user)
    outline = await repository.get_outline_for_chart(report.chart_id)
    segments = await repository.list_segments_for_outline(outline.id) if outline is not None else []
    return build_report_progress_v2(report=report, outline=outline, segments=segments)


@router.get("/reports/{report_id}/facts")
async def get_v2_report_facts(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    """Return deterministic v2 facts and evidence for a report."""

    repository = AstrotypeV2Repository(db)
    report = await _load_report_for_user(repository=repository, report_id=report_id, user_id=current_user)
    facts = await repository.list_facts_for_chart(report.chart_id)
    evidence = [row for fact in facts for row in await repository.list_fact_evidence(fact.id)]
    return build_fact_evidence_payload(facts=facts, evidence=evidence)


@router.get("/reports/{report_id}/infographic")
async def get_v2_report_infographic(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> dict[str, Any]:
    """Return reusable deterministic infographic payload for a report."""

    repository = AstrotypeV2Repository(db)
    report = await _load_report_for_user(repository=repository, report_id=report_id, user_id=current_user)
    infographic = await repository.get_infographic_data_for_chart(report.chart_id)
    if infographic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Infographic data is not ready")
    facts = await repository.list_facts_for_chart(report.chart_id)
    evidence = [row for fact in facts for row in await repository.list_fact_evidence(fact.id)]
    return build_infographic_api_payload_v2(
        chart_id=report.chart_id,
        source_version=infographic.source_version,
        calculation_layer=infographic.calculation_layer,
        evidence_cards=build_fact_evidence_payload(facts=facts, evidence=evidence),
    )


@router.get("/reports/{report_id}/segments")
async def get_v2_report_segments(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    """Return segment generation artifacts for a report."""

    repository = AstrotypeV2Repository(db)
    report = await _load_report_for_user(repository=repository, report_id=report_id, user_id=current_user)
    outline = await repository.get_outline_for_chart(report.chart_id)
    if outline is None:
        return []
    segments = await repository.list_segments_for_outline(outline.id)
    return [
        {"section_key": row.section_key, "status": row.status, "payload": row.payload, "error": row.error}
        for row in segments
    ]


@router.post("/reports/{report_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_v2_report(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
    body: Annotated[RegenerateV2ReportRequest | None, Body()] = None,
) -> JSONResponse:
    """Queue safe v2 regeneration for an existing report owner."""

    repository = AstrotypeV2Repository(db)
    report = await _load_report_for_user(repository=repository, report_id=report_id, user_id=current_user)
    chart = await repository.get_chart(report.chart_id)
    if chart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart is not available")

    from workers.tasks.astrotype_v2 import generate_natal_report_v2

    response = enqueue_v2_report_generation(
        profile_id=chart.profile_id,
        user_id=current_user,
        queue=generate_natal_report_v2,
        force=(body.force if body is not None else True),
    )
    payload = {**response.payload, "previous_report_id": str(report.id)}
    return JSONResponse(status_code=response.status_code, content=payload)


async def _load_report_for_user(
    *,
    repository: AstrotypeV2Repository,
    report_id: UUID,
    user_id: UUID,
) -> models.NatalReport:
    report = await repository.get_report_for_user(report_id=report_id, user_id=user_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


async def _load_profile(
    *,
    db: AsyncSession,
    chart: models.NatalChart | None,
    user_id: UUID,
) -> PersonProfile | None:
    if chart is None:
        return None
    result = await db.execute(
        select(PersonProfile).where(PersonProfile.id == chart.profile_id, PersonProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()
