"""Stable product and migration identifiers for Career reports."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from app.modules.catalog.service import CatalogService

_CAREER_REPORT = CatalogService().get_report("career")
CAREER_REPORT_TYPE = _CAREER_REPORT.report_type
CAREER_ACCESS_CLASS = _CAREER_REPORT.access_class.value
PLUS_ENTITLEMENT_PRODUCT = "self"
LEGACY_CAREER_ENTITLEMENT_PRODUCT = _CAREER_REPORT.entitlement_product or "career"
LEGACY_CAREER_SKU = _CAREER_REPORT.commercial_skus[0]
LEGACY_PAYLOAD_FALLBACK_ALLOWED = False


@dataclass(frozen=True)
class CareerAccessRule:
    requires_ownership: bool = True
    requires_target_access: bool = True


@dataclass(frozen=True)
class CareerRouteAccessContract:
    method: str
    path: str
    operation: str


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

CAREER_ROUTE_ACCESS_CONTRACT: tuple[CareerRouteAccessContract, ...] = (
    CareerRouteAccessContract("GET", "/v1/career/questionnaires/current", "questionnaire"),
    CareerRouteAccessContract("PUT", "/v1/career/questionnaires/{session_id}/answers", "questionnaire"),
    CareerRouteAccessContract("POST", "/v1/career/questionnaires/{session_id}/complete", "questionnaire"),
    CareerRouteAccessContract("POST", "/v1/career/reports", "create"),
    CareerRouteAccessContract("GET", "/v1/career/generations/{generation_id}", "generate"),
    CareerRouteAccessContract("GET", "/v1/career/reports/{report_id}", "read"),
    CareerRouteAccessContract("GET", "/v1/career/reports/{report_id}/sections", "read"),
    CareerRouteAccessContract("POST", "/v1/career/reports/{report_id}/regenerate", "regenerate"),
    CareerRouteAccessContract("GET", "/v1/career/reports/{report_id}/versions", "versions"),
    CareerRouteAccessContract("GET", "/v1/career/reports/{report_id}/pdf", "pdf"),
)

_Endpoint = TypeVar("_Endpoint", bound=Callable[..., Any])


def career_access_operation(operation: str) -> Callable[[_Endpoint], _Endpoint]:
    """Attach the declared access operation to a Career route endpoint."""

    if operation not in CAREER_ACCESS_MATRIX:
        raise ValueError(f"Unknown Career access operation: {operation}")

    def decorator(endpoint: _Endpoint) -> _Endpoint:
        endpoint.__dict__["__career_access_operation__"] = operation
        return endpoint

    return decorator
