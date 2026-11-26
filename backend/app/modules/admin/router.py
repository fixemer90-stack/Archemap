"""Admin module — authenticated support endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_superuser, get_db
from app.infrastructure.database import async_session_factory
from app.modules.admin.schemas import SubscriptionReconcileRequest, SubscriptionSupportResponse
from app.modules.admin.service import AdminService
from app.modules.analytics.landing_documents import read_landing_documents
from app.modules.analytics.overview import BusinessOverview, BusinessTimezone, build_overview

router = APIRouter(prefix="/admin", tags=["admin"])


async def business_read_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory(autoflush=False) as session, session.begin():
        await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        await session.execute(text("SET LOCAL statement_timeout = '5s'"))
        await session.execute(text("SET LOCAL extra_float_digits = 1"))
        yield session


@router.get("/business/overview", response_model=BusinessOverview)
async def get_business_overview(
    _operator: Annotated[UUID, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(business_read_session)],
    response: Response,
    from_date: date | None = None,
    to_date: date | None = None,
    timezone: BusinessTimezone = "Europe/Moscow",
) -> BusinessOverview:
    response.headers["Cache-Control"] = "no-store"
    try:
        overview = await build_overview(
            db,
            as_of=datetime.now(UTC),
            from_date=from_date,
            to_date=to_date,
            timezone=timezone,
            enabled=settings.BUSINESS_MONITORING_ENABLED,
            coverage_since=settings.BUSINESS_MONITORING_COVERAGE_SINCE,
        )
    except (ValueError, OverflowError) as exc:
        raise HTTPException(status_code=422, detail="Invalid business date range") from exc
    overview.landing_documents = await read_landing_documents(datetime.now(UTC))
    return overview


@router.get("/subscriptions/support", response_model=SubscriptionSupportResponse)
async def get_subscription_support(
    email: Annotated[EmailStr, Query()],
    db: Annotated[AsyncSession, Depends(get_db)],
    _operator: Annotated[UUID, Depends(get_current_superuser)],
) -> SubscriptionSupportResponse:
    return await AdminService(db).get_subscription_support(email=str(email))


@router.post("/subscriptions/reconcile", response_model=SubscriptionSupportResponse)
async def reconcile_subscription(
    body: SubscriptionReconcileRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    operator: Annotated[UUID, Depends(get_current_superuser)],
) -> SubscriptionSupportResponse:
    return await AdminService(db).reconcile_subscription(
        email=str(body.email),
        reason=body.reason,
        operator_user_id=operator,
    )
