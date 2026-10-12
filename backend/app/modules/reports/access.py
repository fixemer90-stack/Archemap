"""Executable access-operation inventory for the mounted legacy reports API."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar


@dataclass(frozen=True)
class LegacyReportRouteAccessContract:
    method: str
    path: str
    operation: str


LEGACY_REPORT_ROUTE_ACCESS_CONTRACT: tuple[LegacyReportRouteAccessContract, ...] = (
    LegacyReportRouteAccessContract("POST", "/v1/reports/generate", "create"),
    LegacyReportRouteAccessContract("GET", "/v1/reports", "list"),
    LegacyReportRouteAccessContract("GET", "/v1/reports/{report_id}", "read"),
    LegacyReportRouteAccessContract(
        "POST",
        "/v1/reports/{report_id}/narrative/regenerate",
        "regenerate",
    ),
    LegacyReportRouteAccessContract("HEAD", "/v1/reports/{report_id}/pdf", "export"),
    LegacyReportRouteAccessContract("GET", "/v1/reports/{report_id}/pdf", "export"),
    LegacyReportRouteAccessContract("POST", "/v1/reports/{report_id}/pdf", "export"),
    LegacyReportRouteAccessContract("GET", "/v1/reports/{report_id}/versions", "versions"),
    LegacyReportRouteAccessContract(
        "GET",
        "/v1/reports/{report_id}/versions/{version}",
        "versions",
    ),
)

_OPERATIONS = {item.operation for item in LEGACY_REPORT_ROUTE_ACCESS_CONTRACT}
_Endpoint = TypeVar("_Endpoint", bound=Callable[..., Any])


def legacy_report_access_operation(operation: str) -> Callable[[_Endpoint], _Endpoint]:
    if operation not in _OPERATIONS:
        raise ValueError(f"Unknown legacy report access operation: {operation}")

    def decorator(endpoint: _Endpoint) -> _Endpoint:
        endpoint.__dict__["__report_access_operation__"] = operation
        return endpoint

    return decorator
