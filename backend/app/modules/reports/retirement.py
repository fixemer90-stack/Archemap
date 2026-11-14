"""Non-destructive retirement boundary for the generic Career report writer."""

from collections.abc import Mapping
from typing import Literal, Protocol

from fastapi import HTTPException
from opentelemetry import metrics
from pydantic import BaseModel


class _Counter(Protocol):
    def add(self, amount: float, attributes: Mapping[str, str] | None = None) -> None: ...


_OPERATIONS = frozenset(
    {
        "blocked_generation",
        "blocked_regenerate",
        "blocked_worker",
        "archive_read",
        "archive_versions",
        "archive_pdf",
        "archive_missing",
        "target_grandfathered_access",
    }
)


class RetirementTelemetry:
    """One bounded label; never accepts identifiers or free-form diagnostics."""

    def __init__(self, *, counter: _Counter) -> None:
        self.counter = counter

    def record(self, operation: str) -> None:
        if isinstance(operation, str) and operation in _OPERATIONS:
            self.counter.add(1, {"operation": operation})


retirement_telemetry = RetirementTelemetry(
    counter=metrics.get_meter("archemap.legacy_career").create_counter(
        "legacy_career_operations", description="Non-destructive legacy Career retirement operations"
    )
)

RETIREMENT_DETAIL = {
    "code": "legacy_career_generation_retired",
    "message": "Career reports are created through the Career product flow.",
    "target_path": "/products/career",
}


class LegacyCareerRetiredDetail(BaseModel):
    code: Literal["legacy_career_generation_retired"]
    message: Literal["Career reports are created through the Career product flow."]
    target_path: Literal["/products/career"]


class LegacyCareerRetiredResponse(BaseModel):
    detail: LegacyCareerRetiredDetail


class LegacyCareerRetiredError(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=410, detail=dict(RETIREMENT_DETAIL))


def reject_legacy_career_write(product: str, *, operation: str = "blocked_generation") -> None:
    if product == "career":
        retirement_telemetry.record(operation)
        raise LegacyCareerRetiredError()
