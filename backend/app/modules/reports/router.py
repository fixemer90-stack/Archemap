"""Reports router — API endpoints for report generation and retrieval."""

from __future__ import annotations

from typing import Annotated, Any, cast
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.report_narratives.service import get_latest_narrative_for_report
from app.modules.reports.models import Report
from app.modules.reports.pdf import generate_report_pdf
from app.modules.reports.schemas import (
    GenerateReportRequest,
    ReportListResponse,
    ReportResponse,
    ReportVersionListResponse,
    ReportVersionResponse,
    build_report_response,
)
from app.modules.reports.service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])
logger = structlog.get_logger()


async def _commit_report_changes_if_persistent(db: AsyncSession, report: object) -> None:
    """Persist in-route report status changes when the report is bound to this session.

    Unit tests sometimes mock ReportService and return a transient Report instance.
    Calling refresh() for that object raises InvalidRequestError because it is not
    persistent within the request session. Real service results are persistent and
    still need the commit/refresh cycle.
    """
    if isinstance(db, AsyncSession):
        state = sa_inspect(report, raiseerr=False)
        if state is None or not state.persistent:
            return
    await db.flush()
    await db.commit()
    await db.refresh(report)


async def _load_current_narrative(
    db: AsyncSession,
    report: Report,
) -> Any | None:
    return await get_latest_narrative_for_report(db=db, report_id=report.id, report=report)


async def _ensure_self_narrative_generation(
    db: AsyncSession,
    report: Report,
) -> Any | None:
    narrative = await get_latest_narrative_for_report(db=db, report_id=report.id, report=report)
    if report.product != "self":
        return narrative
    if narrative is not None:
        return narrative
    if report.status != "deterministic_ready":
        return None

    try:
        from workers.tasks.reports import generate_report_narrative

        cast(Any, generate_report_narrative).delay(report_id=str(report.id))
        report.status = "generating_narrative"
        report.error_message = None
        await _commit_report_changes_if_persistent(db, report)
    except Exception as exc:
        logger.warning("narrative_task_enqueue_failed", report_id=str(report.id), error=str(exc))

    return await get_latest_narrative_for_report(db=db, report_id=report.id, report=report)


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

    await _commit_report_changes_if_persistent(db, report)

    # PDF is generated on demand from JSON stored in Postgres. Do not enqueue
    # artifact generation/upload here; report_data + narrative rows are the source of truth.

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

    narrative = await _ensure_self_narrative_generation(db, report)
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
        narrative = await _load_current_narrative(db, report)
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
    narrative = await _ensure_self_narrative_generation(db, report)
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

    narrative = await _load_current_narrative(db, report)
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
        await _commit_report_changes_if_persistent(db, report)

    return build_report_response(report, narrative)


async def _get_report_pdf_headers(
    report_id: UUID,
    db: AsyncSession,
    current_user: UUID,
) -> dict[str, str]:
    service = ReportService(db)
    report = await service.get_report(report_id, current_user)

    if not report.report_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report data is not available yet. Please wait and try again.",
        )

    filename = f"astrotype-report-{report.id}.pdf"
    return {"Content-Disposition": f'attachment; filename="{filename}"'}


@router.head("/{report_id}/pdf")
async def head_report_pdf(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> Response:
    """Return PDF availability/headers without generating the body.

    This explicit HEAD route avoids FastAPI's auto-generated HEAD path for the GET
    endpoint, which currently triggers an OpenTelemetry route-inspection crash in
    our stack for included routers.
    """
    headers = await _get_report_pdf_headers(report_id, db, current_user)
    return Response(status_code=status.HTTP_200_OK, media_type="application/pdf", headers=headers)


@router.get("/{report_id}/pdf")
async def get_report_pdf(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> Response:
    """Render report PDF on demand from JSON stored in Postgres.

    The persisted source of truth is report.report_data plus the latest narrative
    JSON row. We intentionally do not depend on pre-generated S3 artifacts here.
    """
    headers = await _get_report_pdf_headers(report_id, db, current_user)
    service = ReportService(db)
    report = await service.get_report(report_id, current_user)

    narrative = await _load_current_narrative(db, report)
    pdf_bytes = generate_report_pdf(
        report.report_data,
        narrative_content=narrative.content if narrative is not None else None,
        narrative_status=narrative.status if narrative is not None else None,
        narrative_error=narrative.error_message if narrative is not None else None,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=headers,
    )


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
