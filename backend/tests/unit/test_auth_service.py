"""Unit tests for auth service."""

from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthorizationError, ConflictError, ValidationError
from app.modules.auth.schemas import CompleteProfileRequest
from app.modules.auth.service import AuthService

TEST_PASSWORD = "password123"
TEST_BIRTH_DATE = date(1990, 5, 15)
TEST_BIRTH_PLACE = "Москва"
TEST_LATITUDE = 55.7558
TEST_LONGITUDE = 37.6173
TEST_TIMEZONE = "Europe/Moscow"
TEST_BIRTH_TIME = time(14, 30)
TEST_TIME_ACCURACY = "exact"


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(mock_db: AsyncMock) -> AuthService:
    return AuthService(mock_db)


class TestRegister:
    async def test_register_new_user(self, service: AuthService, mock_db: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with (
            patch("app.modules.auth.service.hash_password", return_value="hashed"),
            patch("app.modules.auth.service.VerificationService") as mock_verification_cls,
            patch("app.modules.auth.service.create_access_token", return_value=("access", "jti1")),
            patch("app.modules.auth.service.create_refresh_token", return_value=("refresh", "jti2")),
        ):
            mock_vs = mock_verification_cls.return_value
            mock_vs.create_verification = AsyncMock(return_value="token123")
            mock_vs.send_verification_email = AsyncMock()
            result = await service.register(
                email="new@example.com",
                password=TEST_PASSWORD,
                name="Test User",
                birth_date=TEST_BIRTH_DATE,
                birth_place=TEST_BIRTH_PLACE,
                latitude=TEST_LATITUDE,
                longitude=TEST_LONGITUDE,
                timezone=TEST_TIMEZONE,
                birth_time=TEST_BIRTH_TIME,
                birth_time_accuracy=TEST_TIME_ACCURACY,
            )

        assert result["email"] == "new@example.com"
        assert result["access_token"] == "access"
        assert "chart" in result
        assert "socionics" in result

    async def test_register_duplicate_email(self, service: AuthService, mock_db: AsyncMock) -> None:
        existing_user = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError, match="already exists"):
            await service.register(
                email="existing@example.com",
                password=TEST_PASSWORD,
                name="Test User",
                birth_date=TEST_BIRTH_DATE,
                birth_place=TEST_BIRTH_PLACE,
                latitude=TEST_LATITUDE,
                longitude=TEST_LONGITUDE,
                timezone=TEST_TIMEZONE,
                birth_time=TEST_BIRTH_TIME,
                birth_time_accuracy=TEST_TIME_ACCURACY,
            )

    async def test_register_short_password(self, service: AuthService, mock_db: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValidationError, match="at least 8"):
            await service.register(
                email="new@example.com",
                password="short",  # noqa: S106
                name="Test User",
                birth_date=TEST_BIRTH_DATE,
                birth_place=TEST_BIRTH_PLACE,
                latitude=TEST_LATITUDE,
                longitude=TEST_LONGITUDE,
                timezone=TEST_TIMEZONE,
                birth_time=TEST_BIRTH_TIME,
                birth_time_accuracy=TEST_TIME_ACCURACY,
            )


class TestLogin:
    async def test_login_success(self, service: AuthService, mock_db: AsyncMock) -> None:
        user = MagicMock()
        user.id = "user-id"
        user.email = "test@example.com"
        user.hashed_password = "hashed"
        user.is_active = True
        user.is_verified = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        with (
            patch("app.modules.auth.service.verify_password", return_value=True),
            patch("app.modules.auth.service.create_access_token", return_value=("access", "jti1")),
            patch("app.modules.auth.service.create_refresh_token", return_value=("refresh", "jti2")),
        ):
            tokens = await service.login("test@example.com", TEST_PASSWORD)

        assert tokens["access_token"] == "access"
        assert tokens["refresh_token"] == "refresh"
        assert tokens["token_type"] == "bearer"

    async def test_login_wrong_password(self, service: AuthService, mock_db: AsyncMock) -> None:
        user = MagicMock()
        user.hashed_password = "hashed"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        with (
            patch("app.modules.auth.service.verify_password", return_value=False),
            pytest.raises(AuthorizationError, match="Invalid"),
        ):
            await service.login("test@example.com", "wrong")

    async def test_login_user_not_found(self, service: AuthService, mock_db: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(AuthorizationError, match="Invalid"):
            await service.login("nobody@example.com", TEST_PASSWORD)

    async def test_login_inactive_user(self, service: AuthService, mock_db: AsyncMock) -> None:
        user = MagicMock()
        user.hashed_password = "hashed"
        user.is_active = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        with (
            patch("app.modules.auth.service.verify_password", return_value=True),
            pytest.raises(AuthorizationError, match="deactivated"),
        ):
            await service.login("inactive@example.com", TEST_PASSWORD)

    async def test_login_unverified_user(self, service: AuthService, mock_db: AsyncMock) -> None:
        user = MagicMock()
        user.hashed_password = "hashed"
        user.is_active = True
        user.is_verified = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        with (
            patch("app.modules.auth.service.verify_password", return_value=True),
            pytest.raises(AuthorizationError, match="not verified"),
        ):
            await service.login("unverified@example.com", TEST_PASSWORD)


class TestCompleteOAuthProfile:
    async def test_complete_oauth_profile_requires_name(self, service: AuthService) -> None:
        user = MagicMock()
        user.is_active = True
        service.get_user_by_id = AsyncMock(return_value=user)  # type: ignore[method-assign]

        with pytest.raises(ValidationError, match="Name is required"):
            await service.complete_oauth_profile(
                user_id=MagicMock(),
                name="   ",
                birth_date=TEST_BIRTH_DATE,
                birth_place=TEST_BIRTH_PLACE,
                latitude=TEST_LATITUDE,
                longitude=TEST_LONGITUDE,
                timezone=TEST_TIMEZONE,
                birth_time=TEST_BIRTH_TIME,
                birth_time_accuracy=TEST_TIME_ACCURACY,
            )

    def test_complete_profile_schema_requires_name(self) -> None:
        with pytest.raises(ValueError):
            CompleteProfileRequest.model_validate(
                {
                    "birth_date": TEST_BIRTH_DATE.isoformat(),
                    "birth_time": TEST_BIRTH_TIME.isoformat(),
                    "birth_time_accuracy": TEST_TIME_ACCURACY,
                    "birth_place": TEST_BIRTH_PLACE,
                    "latitude": TEST_LATITUDE,
                    "longitude": TEST_LONGITUDE,
                    "timezone": TEST_TIMEZONE,
                }
            )
