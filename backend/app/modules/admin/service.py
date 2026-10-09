"""Administrative subscription support and audited repair operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.admin.repository import AdminRepository
from app.modules.admin.schemas import (
    SubscriptionEventSummary,
    SubscriptionSupportData,
    SubscriptionSupportResponse,
)
from app.modules.payments.service import PaymentsService
from app.modules.subscriptions.models import SubscriptionEvent
from app.modules.subscriptions.observability import subscription_telemetry

logger = structlog.get_logger()


class _Repository(Protocol):
    async def get_subscription_support_by_email(self, email: str) -> SubscriptionSupportData | None: ...
    async def append_subscription_event(self, **values: Any) -> tuple[SubscriptionEvent, bool]: ...


class _Payments(Protocol):
    async def reconcile_latest_pending_provider_payment(self, user_id: UUID) -> None: ...


class AdminService:
    """Expose support-safe reads and reasoned reconciliation without DB edits."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: _Repository | None = None,
        payments: _Payments | None = None,
    ) -> None:
        self.repository = repository or AdminRepository(db)
        self.payments = payments or PaymentsService(db)

    @staticmethod
    def _response(data: SubscriptionSupportData) -> SubscriptionSupportResponse:
        return SubscriptionSupportResponse(
            user_id=str(data.user_id),
            email=data.email,
            subscription_id=str(data.subscription_id),
            plan_code=data.plan_code,
            display_name=data.display_name,
            status=data.status,
            current_period_start=data.current_period_start,
            current_period_end=data.current_period_end,
            cancel_at_period_end=data.cancel_at_period_end,
            next_billing_at=data.next_billing_at,
            latest_payment_id=str(data.latest_payment_id) if data.latest_payment_id else None,
            latest_payment_status=data.latest_payment_status,
            events=[
                SubscriptionEventSummary(
                    event_type=str(event.event_type),
                    effective_at=event.effective_at,
                    provider_event_id=event.provider_event_id,
                    metadata=dict(event.payload_json or {}),
                )
                for event in data.events
            ],
        )

    async def get_subscription_support(self, *, email: str) -> SubscriptionSupportResponse:
        data = await self.repository.get_subscription_support_by_email(email.strip().lower())
        if data is None:
            raise NotFoundError("Subscription not found")
        return self._response(data)

    async def reconcile_subscription(
        self,
        *,
        email: str,
        reason: str,
        operator_user_id: UUID,
    ) -> SubscriptionSupportResponse:
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ValidationError("Manual reconciliation reason is required")
        data = await self.repository.get_subscription_support_by_email(email.strip().lower())
        if data is None:
            raise NotFoundError("Subscription not found")

        moment = datetime.now(UTC)
        await self.repository.append_subscription_event(
            subscription_id=data.subscription_id,
            event_key=f"manual_reconciliation_requested:{data.subscription_id}:{uuid4()}",
            provider_event_id=None,
            event_type="manual_reconciliation_requested",
            effective_at=moment,
            payload_json={
                "reason": normalized_reason,
                "operator_user_id": str(operator_user_id),
            },
        )
        await self.payments.reconcile_latest_pending_provider_payment(data.user_id)
        subscription_telemetry.record_transition(
            event_type="manual_reconciliation_requested",
            old_status=data.status,
            new_status=data.status,
        )
        logger.info(
            "subscription_manual_reconciliation_requested",
            subscription_id=str(data.subscription_id),
            operator_user_id=str(operator_user_id),
        )
        refreshed = await self.repository.get_subscription_support_by_email(data.email)
        return self._response(refreshed or data)


__all__ = ["AdminService", "SubscriptionSupportData"]
