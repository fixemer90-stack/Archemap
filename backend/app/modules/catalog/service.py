"""Catalog service."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.exceptions import ValidationError


class AccessClass(StrEnum):
    """Backend-owned report access classification."""

    BASIC = "basic"
    PLUS_ONLY = "plus_only"


@dataclass(frozen=True)
class ReportDefinition:
    """Stable report identity and its non-destructive legacy mappings."""

    report_type: str
    display_name: str
    access_class: AccessClass
    enabled: bool
    storage_identifiers: tuple[str, ...] = ()
    commercial_skus: tuple[str, ...] = ()
    entitlement_product: str | None = None


@dataclass(frozen=True)
class ProductPrice:
    """Server-owned commercial product definition."""

    product_id: str
    product: str
    amount: float
    currency: str
    description: str
    purchasable: bool = True


@dataclass(frozen=True)
class SubscriptionPlanDefinition:
    """Server-owned recurring subscription plan definition."""

    plan_code: str
    display_name: str
    amount: float
    currency: str
    billing_interval: str
    interval_count: int
    products: tuple[str, ...]


PRODUCT_CATALOG: dict[str, ProductPrice] = {
    "self_full": ProductPrice(
        product_id="self_full",
        product="self",
        amount=999.0,
        currency="RUB",
        description="Astrotype Plus — полный доступ",
        purchasable=False,
    ),
    "career_full": ProductPrice(
        product_id="career_full",
        product="career",
        amount=1490.0,
        currency="RUB",
        description="Astrotype Career — полный отчёт",
        purchasable=False,
    ),
}

SUBSCRIPTION_PLAN_CATALOG: dict[str, SubscriptionPlanDefinition] = {
    "astrotype_plus_monthly": SubscriptionPlanDefinition(
        plan_code="astrotype_plus_monthly",
        display_name="Astrotype Plus",
        amount=999.0,
        currency="RUB",
        billing_interval="month",
        interval_count=1,
        products=("self", "career", "love", "child"),
    )
}


REPORT_CATALOG: dict[str, ReportDefinition] = {
    "basic_natal": ReportDefinition(
        report_type="basic_natal",
        display_name="Базовый отчёт",
        access_class=AccessClass.BASIC,
        enabled=True,
        storage_identifiers=("self",),
        commercial_skus=("self_full",),
    ),
    "career": ReportDefinition(
        report_type="career",
        display_name="Карьера",
        access_class=AccessClass.PLUS_ONLY,
        enabled=True,
        storage_identifiers=("career",),
        commercial_skus=("career_full",),
        entitlement_product="career",
    ),
    "love": ReportDefinition(
        report_type="love",
        display_name="Отношения",
        access_class=AccessClass.PLUS_ONLY,
        enabled=False,
        storage_identifiers=("love",),
        entitlement_product="love",
    ),
    "child": ReportDefinition(
        report_type="child",
        display_name="Детский портрет",
        access_class=AccessClass.PLUS_ONLY,
        enabled=False,
        storage_identifiers=("child",),
        entitlement_product="child",
    ),
}

REPORT_TYPE_ALIASES: dict[str, str] = {
    alias: definition.report_type
    for definition in REPORT_CATALOG.values()
    for alias in (
        definition.report_type,
        *definition.storage_identifiers,
        *definition.commercial_skus,
    )
}


class CatalogService:
    """Plan and feature management."""

    def get_product(self, product_id: str) -> ProductPrice:
        """Return server-side price definition for a commercial product."""
        product = PRODUCT_CATALOG.get(product_id)
        if product is None:
            raise ValidationError(f"Unknown product_id: {product_id}")
        if not product.purchasable:
            raise ValidationError(f"Product is retired and not purchasable: {product_id}")
        return product

    def get_subscription_plan(self, plan_code: str) -> SubscriptionPlanDefinition:
        """Return the immutable server-owned recurring plan definition."""
        plan = SUBSCRIPTION_PLAN_CATALOG.get(plan_code)
        if plan is None:
            raise ValidationError(f"Unknown subscription plan: {plan_code}")
        return plan

    def resolve_report_type(self, report_identifier: str) -> str:
        """Resolve canonical and legacy identifiers without rewriting stored rows."""
        report_type = REPORT_TYPE_ALIASES.get(report_identifier)
        if report_type is None:
            raise ValidationError(f"Unknown report type: {report_identifier}")
        return report_type

    def get_report(self, report_identifier: str) -> ReportDefinition:
        """Return a canonical report definition or fail closed."""
        return REPORT_CATALOG[self.resolve_report_type(report_identifier)]
