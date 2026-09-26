from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from app.main import app
from app.modules.career.contracts import CAREER_ROUTE_ACCESS_CONTRACT


def _canonical_openapi() -> dict[str, Any]:
    path = Path(__file__).parents[4] / "contracts" / "openapi.yaml"
    return cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def test_canonical_openapi_matches_runtime_career_surface_statuses_and_security() -> None:
    canonical = _canonical_openapi()
    runtime = app.openapi()
    expected_routes = {(route.path, route.method.lower()) for route in CAREER_ROUTE_ACCESS_CONTRACT}
    canonical_routes = {
        (path, method)
        for path, path_item in canonical["paths"].items()
        if path.startswith("/v1/career/")
        for method in path_item
        if method in {"get", "put", "post"}
    }
    runtime_routes = {
        (path.removeprefix("/api"), method)
        for path, path_item in runtime["paths"].items()
        if path.startswith("/api/v1/career/")
        for method in path_item
        if method in {"get", "put", "post"}
    }

    assert canonical_routes == runtime_routes == expected_routes

    for path, method in sorted(expected_routes):
        canonical_operation = canonical["paths"][path][method]
        runtime_operation = runtime["paths"][f"/api{path}"][method]
        assert canonical_operation["security"] == [{"bearerAuth": []}]
        assert runtime_operation["security"] == [{"HTTPBearer": []}]
        assert set(canonical_operation["responses"]) == set(runtime_operation["responses"]) | {"401"}

        runtime_request_schema = (
            runtime_operation.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
        )
        canonical_request_schema = (
            canonical_operation.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
        )
        assert canonical_request_schema == runtime_request_schema

        success_status = next(status for status in runtime_operation["responses"] if status.startswith("2"))
        assert canonical_operation["responses"][success_status].get("content") == runtime_operation["responses"][
            success_status
        ].get("content")


def test_canonical_openapi_contains_all_career_component_schemas_and_errors() -> None:
    canonical = _canonical_openapi()
    schemas = canonical["components"]["schemas"]

    assert {
        "CareerErrorResponse",
        "CareerLockedResponse",
        "CareerLockedErrorResponse",
        "CareerQuestionnaireDraft",
        "QuestionnaireAnswersRequest",
        "QuestionnaireCurrentResponse",
        "QuestionnaireResponse",
        "CreateCareerReportRequest",
        "RegenerateCareerReportRequest",
        "CareerGenerationAcceptedResponse",
        "CareerSectionStateResponse",
        "CareerGenerationStatusResponse",
        "CareerReportResponse",
        "CareerSectionsResponse",
        "CareerReportVersionResponse",
        "CareerReportHistoryResponse",
    } <= set(schemas)
    assert canonical["components"]["responses"]["CareerLocked"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/CareerLockedErrorResponse"
    }
