"""Shared backend-owned access decisions for every report type."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.core.exceptions import ValidationError
from app.modules.catalog.service import AccessClass, CatalogService


class PlusAccessReader(Protocol):
    async def has_active_plus_access(self, user_id: UUID) -> bool: ...

    async def has_active_direct_product_access(self, user_id: UUID, product: str) -> bool: ...


@dataclass(frozen=True)
class ReportAccessDecision:
    allowed: bool
    report_type: str
    access_state: str
    required_level: str | None = None
    reason: str | None = None
    upgrade_url: str | None = None

    def to_payload(self) -> dict[str, str]:
        payload = {
            "access_state": self.access_state,
            "report_type": self.report_type,
        }
        if self.required_level is not None:
            payload["required_level"] = self.required_level
        if self.reason is not None:
            payload["reason"] = self.reason
        if self.upgrade_url is not None:
            payload["upgrade_url"] = self.upgrade_url
        return payload


class ReportAccessPolicy:
    """Grant basic reports to authenticated users and gate all others by Plus."""

    def __init__(
        self,
        plus_access: PlusAccessReader,
        *,
        catalog: CatalogService | None = None,
    ) -> None:
        self.plus_access = plus_access
        self.catalog = catalog or CatalogService()

    async def check(self, user_id: UUID, report_identifier: str) -> ReportAccessDecision:
        try:
            report = self.catalog.get_report(report_identifier)
        except ValidationError:
            return self._locked(report_identifier, reason="unsupported_report_type")

        if report.access_class is AccessClass.BASIC:
            return ReportAccessDecision(
                allowed=True,
                report_type=report.report_type,
                access_state="active",
            )

        if await self.plus_access.has_active_plus_access(user_id):
            return ReportAccessDecision(
                allowed=True,
                report_type=report.report_type,
                access_state="active",
            )

        if report.entitlement_product is not None and await self.plus_access.has_active_direct_product_access(
            user_id,
            report.entitlement_product,
        ):
            return ReportAccessDecision(
                allowed=True,
                report_type=report.report_type,
                access_state="active",
            )

        return self._locked(report.report_type, reason="plus_required")

    @staticmethod
    def _locked(report_type: str, *, reason: str) -> ReportAccessDecision:
        return ReportAccessDecision(
            allowed=False,
            report_type=report_type,
            access_state="locked",
            required_level="plus",
            reason=reason,
            upgrade_url="/billing",
        )
