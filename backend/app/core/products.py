"""Canonical identifiers accepted by new generic report/interpretation requests."""

from typing import Literal, get_args

from app.core.exceptions import ValidationError

GenericProduct = Literal["self", "love", "child", "career"]
_GENERIC_PRODUCTS = get_args(GenericProduct)


def validate_generic_product(product: object) -> None:
    """Reject unknown values without normalizing aliases or exposing input paths."""
    if not isinstance(product, str) or product not in _GENERIC_PRODUCTS:
        raise ValidationError("Unsupported product identifier", code="unsupported_product")
