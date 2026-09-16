"""Stable product and migration identifiers for Career reports."""

from __future__ import annotations

from dataclasses import dataclass

CAREER_REPORT_TYPE = "career"
CAREER_ACCESS_CLASS = "plus_only"
PLUS_ENTITLEMENT_PRODUCT = "self"
LEGACY_CAREER_ENTITLEMENT_PRODUCT = "career"
LEGACY_CAREER_SKU = "career_full"
LEGACY_PAYLOAD_FALLBACK_ALLOWED = False


@dataclass(frozen=True)
class CareerAccessRule:
    requires_ownership: bool = True
    requires_target_access: bool = True


CAREER_ACCESS_MATRIX: dict[str, CareerAccessRule] = {
    operation: CareerAccessRule()
    for operation in (
        "create",
        "questionnaire",
        "generate",
        "read",
        "regenerate",
        "versions",
        "pdf",
    )
}
