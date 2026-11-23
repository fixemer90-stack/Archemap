"""First-party reader observations. Never infer UI behavior from a report GET."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid5

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.models import BusinessEvent
from app.modules.analytics.schemas import BusinessEventInput, EventType, Product
from app.modules.analytics.service import emit_business_event
from app.modules.astrotype_v2.access import BASIC_REPORT_TYPE
from app.modules.astrotype_v2.repository import AstrotypeV2Repository
from app.modules.authorization.report_access import ReportAccessPolicy
from app.modules.authorization.service import EntitlementsService
from app.modules.career.access import CareerAccessPolicy
from app.modules.career.repository import CareerRepository
from app.modules.child.access import ChildAccessPolicy
from app.modules.child.api_service import owned_child_id

ReaderProduct = Literal["self", "career", "child"]
_VIEW_NAMESPACE = UUID("ae25176b-3148-4eb4-9bb6-43c4463e6c6d")


async def observe_owned_report(
    session: AsyncSession, *, owner_id: UUID, product: ReaderProduct, report_id: UUID
) -> bool:
    """One observation per authenticated owner and immutable report artifact.

    Return False for missing, foreign, or locked reports; do not disclose which.
    Ownership uses metadata-only projections; no payment reconciliation, report
    payload, outbound calls or owner/clock/dedup override from the browser.
    """
    access = EntitlementsService(session)
    if product == "self":
        owned = await AstrotypeV2Repository(session).get_owned_report_chart_id(report_id=report_id, user_id=owner_id)
        if owned is None or not (await ReportAccessPolicy(access).check(owner_id, BASIC_REPORT_TYPE)).allowed:
            return False
    elif product == "career":
        owned = await CareerRepository(session).get_owned_report_id(report_id=report_id, user_id=owner_id)
        if owned is None or not (await CareerAccessPolicy(access).check(owner_id)).allowed:
            return False
    elif product == "child":
        try:
            await owned_child_id(session, owner_id, resource="report", resource_id=report_id)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            return False
        if not (await ChildAccessPolicy(access).check(owner_id)).allowed:
            return False
    else:
        return False
    view_id = uuid5(_VIEW_NAMESPACE, f"{product}:{owner_id}:{report_id}")
    # Preserve the original time across retries, including simultaneous requests.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"analytics:reader:{view_id}"}
    )
    semantic_key = f"v1:report_opened:{view_id}:-"
    if await session.scalar(select(BusinessEvent.id).where(BusinessEvent.semantic_key == semantic_key)) is None:
        await emit_business_event(
            session,
            BusinessEventInput(
                event_type=EventType.REPORT_OPENED,
                entity_id=view_id,
                subject_id=owner_id,
                product=Product(product),
                occurred_at=datetime.now(UTC),
            ),
        )
    return True
