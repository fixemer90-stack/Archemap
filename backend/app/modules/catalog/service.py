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


PRODUCT_CATALOG: dict[str, ProductPrice] = {
    "self_full": ProductPrice(
        product_id="self_full",
        product="self",
        amount=990.0,
        currency="RUB",
        description="Astrotype Self — полный отчёт",
    ),
    "career_full": ProductPrice(
        product_id="career_full",
        product="career",
        amount=1490.0,
        currency="RUB",
        description="Astrotype Career — полный отчёт",
    ),
}


class CatalogService:
    """Plan and feature management."""

    def get_product(self, product_id: str) -> ProductPrice:
        """Return server-side price definition for a commercial product."""
        product = PRODUCT_CATALOG.get(product_id)
        if product is None:
            raise ValidationError(f"Unknown product_id: {product_id}")
        return product
