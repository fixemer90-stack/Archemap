"""Reports router — API endpoints for report generation and retrieval."""

from __future__ import annotations

from typing import Annotated, Any, Literal, cast
from uuid import UUID

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, model_validator
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.authorization.report_access import ReportAccessPolicy
from app.modules.authorization.service import EntitlementsService
from app.modules.catalog.service import CatalogService
from app.modules.report_narratives.service import get_latest_narrative_for_report
from app.modules.reports.access import legacy_report_access_operation
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

_catalog = CatalogService()
_basic_report = _catalog.get_report("basic_natal")
_BASIC_REPORT_IDENTIFIERS = {
    _basic_report.report_type,
    *_basic_report.storage_identifiers,
    *_basic_report.commercial_skus,
}
_PLUS_REPORTS = tuple(_catalog.get_report(report_type) for report_type in ("career", "love", "child"))
_LEGACY_REPORT_IDENTIFIERS_BY_PRODUCT = {
    report.entitlement_product: {
        report.report_type,
        *report.storage_identifiers,
        *report.commercial_skus,
    }
    for report in _PLUS_REPORTS
    if report.entitlement_product is not None
}
_LEGACY_REPORT_PRODUCTS = _BASIC_REPORT_IDENTIFIERS | set().union(*_LEGACY_REPORT_IDENTIFIERS_BY_PRODUCT.values())


async def _require_legacy_report_access(*, db: AsyncSession, user_id: UUID, product: str) -> None:
    entitlements = EntitlementsService(db)
    decision = await ReportAccessPolicy(entitlements).check(user_id, product)
    if decision.allowed:
        return
    raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=decision.to_payload())


async def _require_owned_legacy_report_access(
    *,
    db: AsyncSession,
    user_id: UUID,
    report_id: UUID,
) -> str:
    metadata = await ReportService(db).get_report_access_metadata(report_id, user_id)
    await _require_legacy_report_access(db=db, user_id=user_id, product=metadata.product)
    return metadata.product


async def _accessible_legacy_report_products(*, db: AsyncSession, user_id: UUID) -> set[str]:
    entitlements = EntitlementsService(db)
    if await entitlements.has_active_plus_access(user_id):
        return set(_LEGACY_REPORT_PRODUCTS)
    products = set(_BASIC_REPORT_IDENTIFIERS)
    for entitlement_product, report_identifiers in _LEGACY_REPORT_IDENTIFIERS_BY_PRODUCT.items():
        if await entitlements.has_active_direct_product_access(user_id, entitlement_product):
            products.update(report_identifiers)
    return products


class NarrativeRegenerateRequest(BaseModel):
    scope: Literal["failed_stages", "stage", "full"] = "failed_stages"
    stage_id: str | None = None

    @model_validator(mode="after")
    def validate_stage_scope(self) -> NarrativeRegenerateRequest:
        if self.scope == "stage" and not self.stage_id:
            raise ValueError("stage_id is required when scope is 'stage'")
        if self.scope != "stage" and self.stage_id is not None:
            raise ValueError("stage_id is allowed only when scope is 'stage'")
        return self


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
        if narrative.status == "ready" and report.status != "ready":
            report.status = "ready"
            report.error_message = None
            await _commit_report_changes_if_persistent(db, report)
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
@legacy_report_access_operation("create")
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
    profile_id = UUID(body.profile_id)
    await service.assert_profile_owned(profile_id, current_user)
    await _require_legacy_report_access(db=db, user_id=current_user, product=body.product)
    report = await service.generate_report(
        profile_id=profile_id,
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
@legacy_report_access_operation("list")
async def list_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
    product: Annotated[str | None, Query(description="Filter by product")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReportListResponse:
    """List reports for the current user."""
    service = ReportService(db)
    if product is not None:
        await _require_legacy_report_access(db=db, user_id=current_user, product=product)
        allowed_products = {product}
    else:
        allowed_products = await _accessible_legacy_report_products(db=db, user_id=current_user)
    reports, total = await service.list_reports(
        user_id=current_user,
        product=product,
        limit=limit,
        offset=offset,
        allowed_products=allowed_products,
    )
    items: list[ReportResponse] = []
    for report in reports:
        narrative = await _load_current_narrative(db, report)
        items.append(build_report_response(report, narrative))
    return ReportListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{report_id}", response_model=ReportResponse)
@legacy_report_access_operation("read")
async def get_report(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> ReportResponse:
    """Get a report by ID."""
    await _require_owned_legacy_report_access(db=db, user_id=current_user, report_id=report_id)
    service = ReportService(db)
    report = await service.get_report(report_id, current_user)
    narrative = await _ensure_self_narrative_generation(db, report)
    return build_report_response(report, narrative)


@router.post("/{report_id}/narrative/regenerate", response_model=ReportResponse)
@legacy_report_access_operation("regenerate")
async def regenerate_report_narrative(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
    body: Annotated[NarrativeRegenerateRequest | None, Body()] = None,
) -> ReportResponse:
    """Enqueue a fresh LLM narrative attempt without recomputing deterministic report data."""
    await _require_owned_legacy_report_access(db=db, user_id=current_user, report_id=report_id)
    service = ReportService(db)
    report = await service.get_report(report_id, current_user)
    if report.product != "self":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Narrative regeneration is supported only for self reports",
        )

    regenerate_request = body or NarrativeRegenerateRequest()
    narrative = await _load_current_narrative(db, report)
    if report.status != "generating_narrative":
        try:
            from workers.tasks.reports import generate_report_narrative

            cast(Any, generate_report_narrative).delay(
                report_id=str(report.id),
                force=True,
                scope=regenerate_request.scope,
                stage_id=regenerate_request.stage_id,
            )
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
    await _require_owned_legacy_report_access(db=db, user_id=current_user, report_id=report_id)
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
@legacy_report_access_operation("export")
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


async def _render_report_pdf(
    report_id: UUID,
    db: AsyncSession,
    current_user: UUID,
) -> Response:
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


@router.get("/{report_id}/pdf")
@legacy_report_access_operation("export")
async def get_report_pdf(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> Response:
    """Render report PDF on demand from JSON stored in Postgres."""
    return await _render_report_pdf(report_id, db, current_user)


@router.post("/{report_id}/pdf")
@legacy_report_access_operation("export")
async def post_report_pdf(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> Response:
    """POST alias for PDF downloads used by the current client flow."""
    return await _render_report_pdf(report_id, db, current_user)


@router.get("/{report_id}/versions", response_model=ReportVersionListResponse)
@legacy_report_access_operation("versions")
async def get_report_versions(
    report_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> ReportVersionListResponse:
    """Get version history for a report."""
    await _require_owned_legacy_report_access(db=db, user_id=current_user, report_id=report_id)
    service = ReportService(db)
    versions = await service.get_versions(report_id, current_user)
    return ReportVersionListResponse(items=[ReportVersionResponse.model_validate(v) for v in versions])


@router.get("/{report_id}/versions/{version}", response_model=ReportVersionResponse)
@legacy_report_access_operation("versions")
async def get_report_version(
    report_id: UUID,
    version: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UUID, Depends(get_current_user)],
) -> ReportVersionResponse:
    """Get a specific version of a report."""
    await _require_owned_legacy_report_access(db=db, user_id=current_user, report_id=report_id)
    service = ReportService(db)
    rv = await service.get_version(report_id, version, current_user)
    return ReportVersionResponse.model_validate(rv)
