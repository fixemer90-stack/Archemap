"""Reports router — API endpoints for report generation and retrieval."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.report_narratives.service import get_latest_narrative_for_report
from app.modules.reports.schemas import (
    GenerateReportRequest,
    ReportListResponse,
    ReportResponse,
    ReportVersionListResponse,
    ReportVersionResponse,
    build_report_response,
)
from app.modules.reports.service import ReportService
from app.modules.reports.storage import S3Storage, get_signed_ttl

router = APIRouter(prefix="/reports", tags=["reports"])
logger = structlog.get_logger()


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    body: GenerateReportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> ReportResponse:
    """Generate a report for a profile.

    Takes a profile_id and product vertical, runs the rule engine,
    and returns a structured report with archetype, claims, and evidence.
    Also triggers async PDF generation.
    """
    service = ReportService(db)
    report = await service.generate_report(
        profile_id=UUID(body.profile_id),
        user_id=current_user,
        product=body.product,
        mode=body.mode,
    )

    if report.product == "self":
        report.status = "generating_narrative"
        report.error_message = None

    await db.flush()
    await db.commit()
    await db.refresh(report)

    # Trigger async PDF generation (S06)
    try:
        from workers.tasks.reports import generate_pdf

        generate_pdf.delay(
            report_id=str(report.id),
            user_id=str(current_user),
        )
    except Exception as exc:
        # PDF generation is non-critical, don't fail the request
        logger.warning("pdf_task_enqueue_failed", error=str(exc))

    if report.product == "self":
        try:
            from workers.tasks.reports import generate_report_narrative

            generate_report_narrative.delay(report_id=str(report.id))
        except Exception as exc:
            report.status = "deterministic_ready"
            report.error_message = f"Narrative task enqueue failed: {exc}"
            logger.warning("narrative_task_enqueue_failed", report_id=str(report.id), error=str(exc))
            await db.flush()
            await db.commit()
            await db.refresh(report)

    narrative = await get_latest_narrative_for_report(db=db, report_id=report.id)
    return build_report_response(report, narrative)


@router.get("", response_model=ReportListResponse)
async def list_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
    product: Annotated[str | None, Query(description="Filter by product")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReportListResponse:
    """List reports for the current user."""
    service = ReportService(db)
    reports, total = await service.list_reports(
        user_id=current_user,
        product=product,
        limit=limit,
        offset=offset,
    )
    items: list[ReportResponse] = []
    for report in reports:
        narrative = await get_latest_narrative_for_report(db=db, report_id=report.id)
        items.append(build_report_response(report, narrative))
    return ReportListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> ReportResponse:
    """Get a report by ID."""
    service = ReportService(db)
    report = await service.get_report(report_id, current_user)
    narrative = await get_latest_narrative_for_report(db=db, report_id=report.id)
    return build_report_response(report, narrative)


@router.post("/{report_id}/narrative/regenerate", response_model=ReportResponse)
async def regenerate_report_narrative(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> ReportResponse:
    """Enqueue a fresh LLM narrative attempt without recomputing deterministic report data."""
    service = ReportService(db)
    report = await service.get_report(report_id, current_user)
    if report.product != "self":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Narrative regeneration is supported only for self reports",
        )

    narrative = await get_latest_narrative_for_report(db=db, report_id=report.id)
    if report.status != "generating_narrative":
        try:
            from workers.tasks.reports import generate_report_narrative

            generate_report_narrative.delay(report_id=str(report.id), force=True)
        except Exception as exc:
            logger.warning("narrative_regenerate_enqueue_failed", report_id=str(report.id), error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Narrative regenerate task enqueue failed",
            ) from exc
        report.status = "generating_narrative"
        report.error_message = None
        await db.flush()

    return build_report_response(report, narrative)


@router.get("/{report_id}/pdf")
async def get_report_pdf(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> RedirectResponse:
    """Get signed URL for report PDF download.

    Returns 307 redirect to signed S3 URL.
    If PDF not generated yet, returns 404.
    """
    service = ReportService(db)
    report = await service.get_report(report_id, current_user)

    if not report.pdf_generated or not report.pdf_url:
        raise HTTPException(
            status_code=404,
            detail="PDF not generated yet. Please wait and try again.",
        )

    # Refresh signed URL (may have expired)
    from app.modules.reports.storage import build_report_key

    storage = S3Storage()
    key = build_report_key(
        user_id=str(current_user),
        report_id=str(report_id),
        version=report.version,
    )
    ttl = get_signed_ttl(report.mode)
    fresh_url = storage.get_signed_url(key, expires_in=ttl)

    return RedirectResponse(url=fresh_url, status_code=307)


@router.get("/{report_id}/versions", response_model=ReportVersionListResponse)
async def get_report_versions(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> ReportVersionListResponse:
    """Get version history for a report."""
    service = ReportService(db)
    versions = await service.get_versions(report_id, current_user)
    return ReportVersionListResponse(items=[ReportVersionResponse.model_validate(v) for v in versions])


@router.get("/{report_id}/versions/{version}", response_model=ReportVersionResponse)
async def get_report_version(
    report_id: UUID,
    version: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> ReportVersionResponse:
    """Get a specific version of a report."""
    service = ReportService(db)
    rv = await service.get_version(report_id, version, current_user)
    return ReportVersionResponse.model_validate(rv)
