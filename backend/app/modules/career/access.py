"""Backend-owned access policy for target Career artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.modules.career.contracts import (
    LEGACY_CAREER_ENTITLEMENT_PRODUCT,
    PLUS_ENTITLEMENT_PRODUCT,
)


class _EntitlementReader(Protocol):
    async def has_active_product_access(self, user_id: UUID, product: str) -> bool: ...


@dataclass(frozen=True)
class CareerAccessDecision:
    """Result of the target Career access gate without protected content."""

    allowed: bool
    source: str | None = None
    reason: str | None = None


class CareerAccessPolicy:
    """Allow active Plus or an active grandfathered legacy Career grant."""

    def __init__(self, entitlements: _EntitlementReader) -> None:
        self.entitlements = entitlements

    async def check(self, user_id: UUID) -> CareerAccessDecision:
        if await self.entitlements.has_active_product_access(
            user_id=user_id,
            product=PLUS_ENTITLEMENT_PRODUCT,
        ):
            return CareerAccessDecision(allowed=True, source="plus")

        if await self.entitlements.has_active_product_access(
            user_id=user_id,
            product=LEGACY_CAREER_ENTITLEMENT_PRODUCT,
        ):
            return CareerAccessDecision(allowed=True, source="legacy_career")

        return CareerAccessDecision(allowed=False, reason="missing_career_access")
