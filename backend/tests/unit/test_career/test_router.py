from __future__ import annotations

from app.main import app

EXPECTED_ROUTES = {
    ("get", "/api/v1/career/questionnaires/current"),
    ("put", "/api/v1/career/questionnaires/{session_id}/answers"),
    ("post", "/api/v1/career/questionnaires/{session_id}/complete"),
    ("post", "/api/v1/career/reports"),
    ("get", "/api/v1/career/generations/{generation_id}"),
    ("get", "/api/v1/career/reports/{report_id}"),
    ("get", "/api/v1/career/reports/{report_id}/sections"),
    ("post", "/api/v1/career/reports/{report_id}/regenerate"),
    ("get", "/api/v1/career/reports/{report_id}/pdf"),
}


def test_career_routes_publish_explicit_openapi_contracts() -> None:
    schema = app.openapi()
    for method, path in EXPECTED_ROUTES:
        assert path in schema["paths"]
        operation = schema["paths"][path][method]
        assert operation["responses"]
        assert operation.get("security")

    create = schema["paths"]["/api/v1/career/reports"]["post"]
    assert "202" in create["responses"]
    assert "402" in create["responses"]
    assert "409" in create["responses"]
    assert "422" in create["responses"]

    complete = schema["paths"]["/api/v1/career/questionnaires/{session_id}/complete"]["post"]
    assert "Idempotency-Key" in {
        parameter["name"] for parameter in complete["parameters"] if parameter["in"] == "header"
    }

    regenerate = schema["paths"]["/api/v1/career/reports/{report_id}/regenerate"]["post"]
    assert "Idempotency-Key" in {
        parameter["name"] for parameter in regenerate["parameters"] if parameter["in"] == "header"
    }
