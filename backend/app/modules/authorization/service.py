"""Authorization and entitlement service."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.models import Entitlement
from app.modules.subscriptions.models import Subscription
from app.modules.users.models import User

logger = structlog.get_logger()


class AuthorizationService:
    """RBAC and permission checks."""


class AccountTierService:
    """Manage status-only Free/Plus account tier."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upgrade_to_plus(self, user_id: UUID) -> User | None:
        """Upgrade a user to Plus after backend-confirmed payment success."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            logger.warning("account_tier_user_not_found", user_id=str(user_id))
            return None
        user.account_tier = "plus"
        await self.db.flush()
        return user


class EntitlementsService:
    """Manage paid product access grants."""

    def __init__(self, db: AsyncSession, *, now: Callable[[], datetime] | None = None) -> None:
        self.db = db
        self._now = now or (lambda: datetime.now(UTC))

    async def has_active_product_access(self, user_id: UUID, product: str) -> bool:
        """Return whether the user has an active, unexpired entitlement for a product."""
        result = await self.db.execute(
            select(Entitlement).where(
                Entitlement.user_id == user_id,
                Entitlement.product == product,
                Entitlement.status == "active",
            )
        )
        entitlement = result.scalar_one_or_none()
        if entitlement is None or entitlement.product != product or entitlement.status != "active":
            return False

        expires_at = entitlement.expires_at
        now = self._now()
        if expires_at is not None and expires_at <= now:
            return False

        subscription_id = (getattr(entitlement, "metadata_json", None) or {}).get("subscription_id")
        if not subscription_id:
            return True
        result = await self.db.execute(select(Subscription).where(Subscription.id == UUID(str(subscription_id))))
        subscription = cast(Subscription | None, result.scalar_one_or_none())
        if subscription is None:
            return False
        normal_period = (
            subscription.status in {"active", "cancel_scheduled"}
            and subscription.current_period_start is not None
            and subscription.current_period_end is not None
            and subscription.current_period_start <= now < subscription.current_period_end
        )
        grace_access = (
            subscription.status == "past_due"
            and subscription.grace_until is not None
            and subscription.grace_until > now
        )
        return normal_period or grace_access

    async def build_product_access_state(self, user_id: UUID, product: str) -> dict[str, Any]:
        """Return safe product access state for API gates and clients."""
        has_access = await self.has_active_product_access(user_id=user_id, product=product)
        if has_access:
            return {"access_state": "active", "required_product": product}
        return build_locked_product_response(product=product, reason="missing_entitlement")

    async def grant_paid_product(
        self,
        user_id: UUID,
        product: str,
        source_payment_id: UUID,
        metadata: dict[str, Any] | None = None,
        starts_at: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> Entitlement:
        """Grant an active product entitlement idempotently for a succeeded payment."""
        result = await self.db.execute(
            select(Entitlement).where(
                Entitlement.source_payment_id == source_payment_id,
                Entitlement.product == product,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.status = "active"
            existing.starts_at = starts_at or existing.starts_at
            existing.expires_at = expires_at
            existing.metadata_json = {**(existing.metadata_json or {}), **(metadata or {})}
            await self.db.flush()
            return existing

        entitlement = Entitlement(
            user_id=user_id,
            product=product,
            status="active",
            source_payment_id=source_payment_id,
            starts_at=starts_at or datetime.now(UTC),
            expires_at=expires_at,
            metadata_json=metadata,
        )
        self.db.add(entitlement)
        await self.db.flush()
        return entitlement


def build_locked_product_response(product: str, reason: str) -> dict[str, Any]:
    """Build a safe locked response without paid report/product payload fields."""
    return {
        "access_state": "locked",
        "required_product": product,
        "reason": reason,
        "upgrade": {
            "title": "Нужен Plus",
            "description": "Полный отчёт открывается после подтверждения оплаты.",
            "href": "/billing",
        },
    }
