"""Unit contracts for the birth-data refinement API slice."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.modules.profiles.refinement import (
    BirthDataAccuracyMismatchError,
    BirthDataPlaceNotGeocodedError,
    BirthDataRefinementService,
    canonical_request_hash,
)
from app.modules.profiles.schemas import BirthDataRefinementRequest, UpdateProfileRequest


def _request(**overrides: object) -> BirthDataRefinementRequest:
    payload: dict[str, object] = {
        "birth_time": "08:35",
        "birth_time_accuracy": "exact",
        "birth_place": "Moscow, Russia",
        "latitude": 55.7558,
        "longitude": 37.6176,
        "timezone": "Europe/Moscow",
    }
    payload.update(overrides)
    return BirthDataRefinementRequest(**payload)


def test_refinement_request_is_full_snapshot_without_birth_date() -> None:
    assert "birth_date" not in BirthDataRefinementRequest.model_fields
    with pytest.raises(PydanticValidationError):
        BirthDataRefinementRequest.model_validate({"birth_time": None})


def test_generic_profile_patch_is_name_only_and_rejects_birth_data() -> None:
    assert set(UpdateProfileRequest.model_fields) == {"name"}
    with pytest.raises(PydanticValidationError):
        UpdateProfileRequest.model_validate({"birth_time": "09:00"})


def test_canonical_request_hash_is_stable_for_equivalent_payloads() -> None:
    first = _request()
    second = BirthDataRefinementRequest.model_validate(
        {
            "timezone": "Europe/Moscow",
            "longitude": 37.6176,
            "latitude": 55.7558,
            "birth_place": "Moscow, Russia",
            "birth_time_accuracy": "exact",
            "birth_time": "08:35:00",
        }
    )

    assert canonical_request_hash(first) == canonical_request_hash(second)
    assert len(canonical_request_hash(first)) == 64


@pytest.mark.parametrize("accuracy", ["exact", "approximate"])
async def test_exact_and_approximate_require_time(accuracy: str) -> None:
    service = BirthDataRefinementService(AsyncMock(), timezone_resolver=AsyncMock())

    with pytest.raises(BirthDataAccuracyMismatchError):
        await service.validate_snapshot(_request(birth_time=None, birth_time_accuracy=accuracy))


async def test_unknown_requires_null_time() -> None:
    service = BirthDataRefinementService(AsyncMock(), timezone_resolver=AsyncMock())

    with pytest.raises(BirthDataAccuracyMismatchError):
        await service.validate_snapshot(_request(birth_time="08:35", birth_time_accuracy="unknown"))


@pytest.mark.parametrize(
    ("latitude", "longitude", "timezone", "resolved"),
    [
        (0.0, 0.0, "Etc/UTC", "Etc/UTC"),
        (55.7558, 37.6176, "Not/AZone", "Europe/Moscow"),
        (55.7558, 37.6176, "Europe/London", "Europe/Moscow"),
        (55.7558, 37.6176, "Europe/Moscow", None),
    ],
)
async def test_place_group_requires_real_matching_iana_timezone(
    latitude: float,
    longitude: float,
    timezone: str,
    resolved: str | None,
) -> None:
    resolver = AsyncMock()
    resolver.resolve.return_value = resolved
    service = BirthDataRefinementService(AsyncMock(), timezone_resolver=resolver)

    with pytest.raises(BirthDataPlaceNotGeocodedError):
        await service.validate_snapshot(_request(latitude=latitude, longitude=longitude, timezone=timezone))


async def test_status_uses_server_clock_and_account_wide_latest_revision() -> None:
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    now = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
    repository = MagicMock()
    repository.ensure_owned_profile = AsyncMock()
    repository.latest_revision_at = AsyncMock(return_value=now - timedelta(hours=23))
    service = BirthDataRefinementService(
        AsyncMock(),
        timezone_resolver=AsyncMock(),
        repository=repository,
        clock=lambda: now,
    )

    result = await service.get_status(user_id=user_id, profile_id=profile_id)

    assert result.profile_id == profile_id
    assert result.can_refine is False
    assert result.next_available_at == now + timedelta(hours=1)
    assert result.retry_after_seconds == 3600
