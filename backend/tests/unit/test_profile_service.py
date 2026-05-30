"""Unit tests for profile service."""

from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.profiles.schemas import CreateProfileRequest, UpdateProfileRequest
from app.modules.profiles.service import ProfileService


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(mock_db: AsyncMock) -> ProfileService:
    return ProfileService(mock_db)


def _make_create_data(**overrides: object) -> CreateProfileRequest:
    defaults = {
        "name": "Test User",
        "birth_date": date(1990, 5, 15),
        "birth_time": time(14, 30),
        "birth_time_accuracy": "exact",
        "birth_place": "Moscow, Russia",
        "latitude": 55.7558,
        "longitude": 37.6173,
        "timezone": "Europe/Moscow",
    }
    defaults.update(overrides)
    return CreateProfileRequest(**defaults)


class TestValidateBirthDate:
    def test_valid_date(self) -> None:
        ProfileService._validate_birth_date(date(1990, 5, 15))

    def test_boundary_1900(self) -> None:
        ProfileService._validate_birth_date(date(1900, 1, 1))

    def test_boundary_2100(self) -> None:
        ProfileService._validate_birth_date(date(2100, 12, 31))

    def test_too_old(self) -> None:
        with pytest.raises(ValidationError, match="between 1900 and 2100"):
            ProfileService._validate_birth_date(date(1899, 12, 31))

    def test_too_future(self) -> None:
        with pytest.raises(ValidationError, match="between 1900 and 2100"):
            ProfileService._validate_birth_date(date(2101, 1, 1))


class TestCreateProfile:
    async def test_create_calls_db(self, service: ProfileService, mock_db: AsyncMock) -> None:
        data = _make_create_data()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        profile = await service.create(user_id="fake-uuid", data=data)  # type: ignore[arg-type]

        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()
        assert profile.name == "Test User"
        assert profile.birth_date == date(1990, 5, 15)
        assert profile.birth_time == time(14, 30)
        assert profile.birth_time_accuracy == "exact"
        assert profile.latitude == 55.7558

    async def test_create_unknown_time(self, service: ProfileService, mock_db: AsyncMock) -> None:
        data = _make_create_data(birth_time=None, birth_time_accuracy="unknown")
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        profile = await service.create(user_id="fake-uuid", data=data)  # type: ignore[arg-type]

        assert profile.birth_time is None
        assert profile.birth_time_accuracy == "unknown"

    async def test_create_invalid_year(self, service: ProfileService) -> None:
        data = _make_create_data(birth_date=date(1850, 1, 1))
        with pytest.raises(ValidationError):
            await service.create(user_id="fake-uuid", data=data)  # type: ignore[arg-type]


class TestGetById:
    async def test_found(self, service: ProfileService, mock_db: AsyncMock) -> None:
        mock_profile = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_profile
        mock_db.execute.return_value = mock_result

        result = await service.get_by_id("profile-id", "user-id")  # type: ignore[arg-type]
        assert result == mock_profile

    async def test_not_found(self, service: ProfileService, mock_db: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError, match="Profile not found"):
            await service.get_by_id("profile-id", "user-id")  # type: ignore[arg-type]


class TestListByUser:
    async def test_returns_profiles_and_count(self, service: ProfileService, mock_db: AsyncMock) -> None:
        mock_profile = MagicMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = [mock_profile]
        mock_db.execute.side_effect = [mock_count_result, mock_list_result]

        profiles, total = await service.list_by_user("user-id")  # type: ignore[arg-type]
        assert total == 1
        assert len(profiles) == 1


class TestUpdate:
    async def test_partial_update(self, service: ProfileService, mock_db: AsyncMock) -> None:
        mock_profile = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_profile
        mock_db.execute.return_value = mock_result
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        data = UpdateProfileRequest(name="New Name")
        await service.update("profile-id", "user-id", data)  # type: ignore[arg-type]

        assert mock_profile.name == "New Name"
        mock_db.flush.assert_awaited_once()

    async def test_update_birth_date_validates(self, service: ProfileService, mock_db: AsyncMock) -> None:
        mock_profile = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_profile
        mock_db.execute.return_value = mock_result

        data = UpdateProfileRequest(birth_date=date(1800, 1, 1))
        with pytest.raises(ValidationError):
            await service.update("profile-id", "user-id", data)  # type: ignore[arg-type]


class TestDelete:
    async def test_delete_calls_db(self, service: ProfileService, mock_db: AsyncMock) -> None:
        mock_profile = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_profile
        mock_db.execute.return_value = mock_result
        mock_db.flush = AsyncMock()
        mock_db.delete = AsyncMock()

        await service.delete("profile-id", "user-id")  # type: ignore[arg-type]
        mock_db.delete.assert_awaited_once_with(mock_profile)
        mock_db.flush.assert_awaited_once()
