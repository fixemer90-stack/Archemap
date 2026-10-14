"""Backend-owned access policy for Child Report resources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.modules.child.contracts import CHILD_ENTITLEMENT_PRODUCT


class _EntitlementReader(Protocol):
    async def has_active_plus_access(self, user_id: UUID) -> bool: ...

    async def has_active_direct_product_access(self, user_id: UUID, product: str) -> bool: ...


@dataclass(frozen=True)
class ChildAccessDecision:
    """Safe access result that contains no child or report payload."""

    allowed: bool
    source: str | None = None
    reason: str | None = None


class ChildAccessPolicy:
    """Allow active Plus or a current direct Child product grant."""

    def __init__(self, entitlements: _EntitlementReader) -> None:
        self.entitlements = entitlements

    async def check(self, user_id: UUID) -> ChildAccessDecision:
        if await self.entitlements.has_active_plus_access(user_id=user_id):
            return ChildAccessDecision(allowed=True, source="plus")

        if await self.entitlements.has_active_direct_product_access(
            user_id=user_id,
            product=CHILD_ENTITLEMENT_PRODUCT,
        ):
            return ChildAccessDecision(allowed=True, source="grandfathered_child")

        return ChildAccessDecision(allowed=False, reason="missing_child_access")
