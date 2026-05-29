"""Unit tests for auth service."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthorizationError, ConflictError, ValidationError
from app.modules.auth.service import AuthService


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
        ):
            mock_vs = mock_verification_cls.return_value
            mock_vs.create_verification = AsyncMock(return_value="token123")
            mock_vs.send_verification_email = AsyncMock()
            user = await service.register("new@example.com", "password123")

        assert user.email == "new@example.com"
        assert user.hashed_password == "hashed"
        mock_db.add.assert_called_once()  # Only User; VerificationService handles its own add
        mock_vs.create_verification.assert_awaited_once()
        mock_vs.send_verification_email.assert_awaited_once_with("new@example.com", "token123")

    async def test_register_duplicate_email(self, service: AuthService, mock_db: AsyncMock) -> None:
        existing_user = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError, match="already exists"):
            await service.register("existing@example.com", "password123")

    async def test_register_short_password(self, service: AuthService, mock_db: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValidationError, match="at least 8"):
            await service.register("new@example.com", "short")


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
            tokens = await service.login("test@example.com", "password123")

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
            await service.login("nobody@example.com", "password123")

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
            await service.login("inactive@example.com", "password123")

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
            await service.login("unverified@example.com", "password123")
