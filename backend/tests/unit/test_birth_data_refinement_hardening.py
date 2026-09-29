"""Blocking S01/S02 hardening contracts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.main import app
from app.modules.profiles.dispatch import dispatch_birth_data_revision
from app.modules.profiles.refinement import (
    BirthDataPlaceNotGeocodedError,
    BirthDataRefinementService,
    canonical_request_hash,
    create_geocode_selection_token,
    map_generation_status,
    verify_geocode_selection_token,
)
from app.modules.profiles.schemas import BirthDataRefinementRequest, UpdateProfileRequest

_TOKEN_SECRET = "test-geocode-token"


def _request(**overrides: object) -> BirthDataRefinementRequest:
    payload: dict[str, object] = {
        "birth_time": "08:35",
        "birth_time_accuracy": "exact",
        "birth_place": "Moscow, Russia",
        "latitude": 55.7558,
        "longitude": 37.6176,
        "timezone": "Europe/Moscow",
        "geocode_selection_token": "proof",
    }
    payload.update(overrides)
    return BirthDataRefinementRequest.model_validate(payload)


def test_request_hash_binds_profile_and_normalized_payload() -> None:
    profile_a = uuid.uuid4()
    profile_b = uuid.uuid4()
    request = _request()

    assert canonical_request_hash(profile_a, request) == canonical_request_hash(
        profile_a, _request(birth_time="08:35:00")
    )
    assert canonical_request_hash(profile_a, request) != canonical_request_hash(profile_b, request)


def test_geocode_selection_token_is_signed_bound_and_expires() -> None:
    now = datetime(2026, 9, 28, 10, 0, tzinfo=UTC)
    token = create_geocode_selection_token(
        secret=_TOKEN_SECRET,
        place="  Moscow,   Russia ",
        latitude=55.7558,
        longitude=37.6176,
        timezone="Europe/Moscow",
        now=now,
    )

    verify_geocode_selection_token(
        token=token,
        secret=_TOKEN_SECRET,
        place="Moscow, Russia",
        latitude=55.7558,
        longitude=37.6176,
        timezone="Europe/Moscow",
        now=now,
    )
    with pytest.raises(BirthDataPlaceNotGeocodedError):
        verify_geocode_selection_token(
            token=token,
            secret=_TOKEN_SECRET,
            place="Arbitrary free text",
            latitude=55.7558,
            longitude=37.6176,
            timezone="Europe/Moscow",
            now=now,
        )


def test_generic_patch_explicitly_rejects_birth_date() -> None:
    with pytest.raises(PydanticValidationError) as exc_info:
        UpdateProfileRequest.model_validate({"birth_date": "1999-01-01"})
    assert exc_info.value.errors()[0]["type"] == "extra_forbidden"
    assert UpdateProfileRequest.model_validate({"name": "New name"}).name == "New name"


@pytest.mark.parametrize(
    ("generation_status", "expected"),
    [
        ("queued", "queued"),
        ("running", "processing"),
        ("narrative_generating", "deterministic_ready"),
        ("ready", "ready"),
        ("already_exists", "ready"),
        ("narrative_failed", "deterministic_ready"),
        ("failed", "failed"),
    ],
)
def test_generation_status_maps_to_revision_contract(generation_status: str, expected: str) -> None:
    assert map_generation_status(generation_status) == expected


async def test_snapshot_requires_valid_server_proof_even_when_coordinates_match() -> None:
    resolver = AsyncMock()
    resolver.resolve.return_value = "Europe/Moscow"
    service = BirthDataRefinementService(
        AsyncMock(),
        timezone_resolver=resolver,
        geocode_token_secret=_TOKEN_SECRET,
        clock=lambda: datetime(2026, 9, 28, 10, 0, tzinfo=UTC),
    )

    with pytest.raises(BirthDataPlaceNotGeocodedError):
        await service.validate_snapshot(_request())


def test_runtime_openapi_documents_token_enums_auth_not_found_and_retry_header() -> None:
    schema = app.openapi()
    create = schema["paths"]["/api/v1/profiles/{profile_id}/birth-data-refinements"]["post"]
    revision = schema["paths"]["/api/v1/profiles/{profile_id}/birth-data-refinements/{revision_id}"]["get"]
    geocode = schema["paths"]["/api/v1/profiles/geocode"]["get"]
    request_schema = schema["components"]["schemas"]["BirthDataRefinementRequest"]
    accepted = schema["components"]["schemas"]["BirthDataRefinementAcceptedResponse"]
    status_response = schema["components"]["schemas"]["BirthDataRevisionStatusResponse"]

    assert "geocode_selection_token" in request_schema["required"]
    assert "selection_token" in schema["components"]["schemas"]["GeocodeResultItem"]["required"]
    assert set(create["responses"]) >= {"202", "400", "401", "403", "404", "409", "422", "429", "503"}
    assert set(revision["responses"]) >= {"200", "401", "403", "404"}
    assert geocode["responses"]["429"]["headers"]["Retry-After"]
    assert accepted["properties"]["status"]["enum"] == ["queued"]
    assert set(status_response["properties"]["status"]["enum"]) == {
        "queued",
        "processing",
        "deterministic_ready",
        "ready",
        "failed",
    }
    expected_fields = ["birth_time", "birth_time_accuracy", "birth_place", "latitude", "longitude", "timezone"]
    assert accepted["properties"]["changed_fields"]["items"]["enum"] == expected_fields
    assert status_response["properties"]["changed_fields"]["items"]["enum"] == expected_fields


async def test_dispatch_failure_log_is_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    revision = SimpleNamespace(
        id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        generation_id=uuid.uuid4(),
    )
    repository = MagicMock()
    repository.claim_dispatch = AsyncMock(return_value=revision)
    repository.release_dispatch = AsyncMock()
    repository.mark_dispatched = AsyncMock()
    session = AsyncMock()
    warning = MagicMock()
    monkeypatch.setattr("app.modules.profiles.dispatch.BirthDataRevisionRepository", lambda _session: repository)
    monkeypatch.setattr("app.modules.profiles.dispatch.logger.warning", warning)

    def sender(**_kwargs: object) -> object:
        raise RuntimeError("private place: Moscow, Russia")

    assert await dispatch_birth_data_revision(session, revision_id=revision.id, sender=sender) is False

    warning.assert_called_once_with(
        "birth_data_refinement_dispatch_failed",
        revision_id=str(revision.id),
        generation_id=str(revision.generation_id),
        error_code="broker_unavailable",
    )
    assert "Moscow" not in repr(warning.call_args)
