"""Reports router — API endpoints for report generation and retrieval."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.reports.schemas import (
    GenerateReportRequest,
    ReportListResponse,
    ReportResponse,
    ReportVersionListResponse,
    ReportVersionResponse,
)
from app.modules.reports.service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    body: GenerateReportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> ReportResponse:
    """Generate a report for a profile.

    Takes a profile_id and product vertical, runs the rule engine,
    and returns a structured report with archetype, claims, and evidence.
    """
    service = ReportService(db)
    report = await service.generate_report(
        profile_id=UUID(body.profile_id),
        user_id=current_user,
        product=body.product,
        mode=body.mode,
    )
    return ReportResponse.model_validate(report)


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
    return ReportListResponse(
        items=[ReportResponse.model_validate(r) for r in reports],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> ReportResponse:
    """Get a report by ID."""
    service = ReportService(db)
    report = await service.get_report(report_id, current_user)
    return ReportResponse.model_validate(report)


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
