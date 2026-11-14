"""Tracked E20 API contract accepts retired inputs and documents exact 410s."""

from pathlib import Path
from typing import Any, cast

import pytest
import yaml


def _spec() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[4] / "contracts/openapi.yaml"
    return cast(dict[str, Any], yaml.safe_load(path.read_text()))


@pytest.mark.parametrize(
    "path",
    ["/v1/reports/generate", "/v1/reports/{report_id}/narrative/regenerate", "/v1/rules/interpret"],
)
def test_every_public_legacy_career_generation_path_documents_retirement(path: str) -> None:
    spec = _spec()
    endpoint = spec["paths"].get(path)
    assert endpoint is not None, f"Missing discovered legacy generation consumer: {path}"
    assert endpoint["post"]["responses"].get("410") == {"$ref": "#/components/responses/LegacyCareerRetired"}


def test_archive_list_accepts_an_owned_profile_filter_without_changing_the_report_payload() -> None:
    endpoint = _spec()["paths"].get("/v1/reports")
    assert endpoint is not None, "Archive lookup needs a documented profile-scoped list"
    parameters = {item["name"]: item for item in endpoint["get"]["parameters"]}
    assert parameters["profile_id"]["schema"]["format"] == "uuid"
    assert parameters["profile_id"].get("required", False) is False
    assert parameters["product"]["schema"]["type"] == "string"


@pytest.mark.parametrize("schema_name", ["GenerateReportRequest", "LegacyRuleInterpretRequest"])
def test_generic_product_inputs_document_exact_nonpath_allowlist(schema_name: str) -> None:
    product = _spec()["components"]["schemas"][schema_name]["properties"]["product"]
    assert set(product.get("enum", [])) == {"self", "love", "child", "career"}, (
        "Generic product input must reject filesystem aliases without normalizing them"
    )


def test_archive_availability_metadata_matches_runtime_without_rewriting_saved_payload() -> None:
    from app.modules.reports.schemas import ReportResponse

    tracked = _spec()["components"]["schemas"]["ReportResponse"]
    field = tracked["properties"].get("archive_status")
    assert field is not None, "Tracked response must document additive archive availability"
    assert set(field["type"]) == {"string", "null"}
    assert set(field["enum"]) == {"available", "unavailable", None}
    assert "archive_status" not in tracked["required"]
    assert tracked["properties"]["report_data"]["additionalProperties"] is True
    runtime = ReportResponse.model_json_schema()["properties"]["archive_status"]
    runtime_values = next(item["enum"] for item in runtime["anyOf"] if "enum" in item)
    assert set(runtime_values) == set(field["enum"]) - {None}


def test_retirement_contract_is_distinct_from_payload_and_does_not_reject_career_at_parsing() -> None:
    spec = _spec()
    schemas = spec["components"]["schemas"]
    response = schemas.get("LegacyCareerRetirementResponse")
    assert response is not None, "Retirement needs a machine-readable non-report response"
    detail = response["properties"]["detail"]
    assert set(detail["required"]) == {"code", "message", "target_path"}
    assert detail["properties"]["code"]["const"] == "legacy_career_generation_retired"
    assert detail["properties"]["target_path"]["const"] == "/products/career"
    product = schemas["GenerateReportRequest"]["properties"]["product"]
    assert product["type"] == "string"
    assert "enum" not in product or "career" in product["enum"]
