"""Canonical OpenAPI contract coverage for E10 S02."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_canonical_openapi_contains_refinement_paths_and_error_shapes() -> None:
    contract = yaml.safe_load((ROOT / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
    paths = contract["paths"]

    assert "/v1/profiles/geocode" in paths
    assert "/v1/profiles/{profile_id}/birth-data-refinement-status" in paths
    create = paths["/v1/profiles/{profile_id}/birth-data-refinements"]["post"]
    assert set(create["responses"]) >= {"202", "400", "401", "403", "404", "409", "422", "429", "503"}
    assert create["parameters"][1]["$ref"] == "#/components/parameters/UuidIdempotencyKey"
    assert "/v1/profiles/{profile_id}/birth-data-refinements/{revision_id}" in paths

    schemas = contract["components"]["schemas"]
    request = schemas["BirthDataRefinementRequest"]
    assert request["additionalProperties"] is False
    assert "birth_date" not in request["properties"]
    assert set(request["required"]) == {
        "birth_time",
        "birth_time_accuracy",
        "birth_place",
        "latitude",
        "longitude",
        "timezone",
    }
    assert "geocode_selection_token" not in request["required"]
    assert {"timezone", "selection_token"} <= set(schemas["GeocodeResultItem"]["required"])
    assert set(schemas["RefinementError"]["properties"]["code"]["enum"]) >= {
        "birth_data_unchanged",
        "birth_time_accuracy_mismatch",
        "birth_place_not_geocoded",
        "profile_not_owned",
        "idempotency_key_conflict",
        "birth_data_refinement_cooldown",
        "birth_data_refinement_disabled",
        "refinement_enqueue_unavailable",
    }
