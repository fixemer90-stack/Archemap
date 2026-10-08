"""Catalog service."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import ValidationError


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
