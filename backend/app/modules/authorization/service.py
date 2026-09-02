"""Authorization and entitlement service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authorization.models import Entitlement
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

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def grant_paid_product(
        self,
        user_id: UUID,
        product: str,
        source_payment_id: UUID,
        metadata: dict[str, Any] | None = None,
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
            existing.metadata_json = {**(existing.metadata_json or {}), **(metadata or {})}
            await self.db.flush()
            return existing

        entitlement = Entitlement(
            user_id=user_id,
            product=product,
            status="active",
            source_payment_id=source_payment_id,
            starts_at=datetime.now(UTC),
            expires_at=None,
            metadata_json=metadata,
        )
        self.db.add(entitlement)
        await self.db.flush()
        return entitlement
