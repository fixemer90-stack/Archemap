"""Runtime OpenAPI parity for profile refinement routes."""

from __future__ import annotations

from app.main import app


def test_runtime_openapi_exposes_refinement_and_timezone_contracts() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    status_path = paths["/api/v1/profiles/{profile_id}/birth-data-refinement-status"]
    create_path = paths["/api/v1/profiles/{profile_id}/birth-data-refinements"]
    revision_path = paths["/api/v1/profiles/{profile_id}/birth-data-refinements/{revision_id}"]

    assert "get" in status_path
    assert "post" in create_path
    assert "get" in revision_path
    idempotency = next(
        parameter for parameter in create_path["post"]["parameters"] if parameter["name"] == "Idempotency-Key"
    )
    assert idempotency["required"] is True
    assert idempotency["schema"]["format"] == "uuid"
    assert create_path["post"]["responses"]["202"]["content"]["application/json"]["schema"]
    assert set(create_path["post"]["responses"]) >= {"202", "400", "403", "409", "422", "429", "503"}

    geocode_schema = schema["components"]["schemas"]["GeocodeResultItem"]
    assert "timezone" in geocode_schema["required"]
    refinement_schema = schema["components"]["schemas"]["BirthDataRefinementRequest"]
    assert "birth_date" not in refinement_schema["properties"]
    update_schema = schema["components"]["schemas"]["UpdateProfileRequest"]
    assert set(update_schema["properties"]) == {"name"}
