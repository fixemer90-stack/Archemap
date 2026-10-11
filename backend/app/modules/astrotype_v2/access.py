"""Access-operation contract for the canonical basic natal report."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from app.modules.catalog.service import CatalogService

BASIC_REPORT_TYPE = CatalogService().resolve_report_type("self")


@dataclass(frozen=True)
class ReportRouteAccessContract:
    method: str
    path: str
    operation: str


REPORT_ROUTE_ACCESS_CONTRACT: tuple[ReportRouteAccessContract, ...] = (
    ReportRouteAccessContract("POST", "/v1/astrotype-v2/reports", "create"),
    ReportRouteAccessContract("GET", "/v1/astrotype-v2/reports/generations/{generation_id}", "status"),
    ReportRouteAccessContract("GET", "/v1/astrotype-v2/reports/{report_id}", "read"),
    ReportRouteAccessContract("GET", "/v1/astrotype-v2/reports/{report_id}/pdf", "export"),
    ReportRouteAccessContract("GET", "/v1/astrotype-v2/reports/{report_id}/progress", "status"),
    ReportRouteAccessContract("GET", "/v1/astrotype-v2/reports/{report_id}/facts", "calculation"),
    ReportRouteAccessContract("GET", "/v1/astrotype-v2/reports/{report_id}/infographic", "calculation"),
    ReportRouteAccessContract("GET", "/v1/astrotype-v2/reports/{report_id}/segments", "segments"),
    ReportRouteAccessContract("POST", "/v1/astrotype-v2/reports/{report_id}/regenerate", "regenerate"),
)

_REPORT_OPERATIONS = {item.operation for item in REPORT_ROUTE_ACCESS_CONTRACT}
_Endpoint = TypeVar("_Endpoint", bound=Callable[..., Any])


def report_access_operation(operation: str) -> Callable[[_Endpoint], _Endpoint]:
    if operation not in _REPORT_OPERATIONS:
        raise ValueError(f"Unknown report access operation: {operation}")

    def decorator(endpoint: _Endpoint) -> _Endpoint:
        endpoint.__dict__["__report_access_operation__"] = operation
        return endpoint

    return decorator
