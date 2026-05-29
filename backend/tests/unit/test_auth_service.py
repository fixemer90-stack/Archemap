"""Unit tests for auth service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthorizationError, ConflictError
from app.modules.auth.service import AuthService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def service(mock_db):
    return AuthService(mock_db)


class TestRegister:
    async def test_register_new_user(self, service, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.modules.auth.service.hash_password", return_value="hashed"):
            user = await service.register("new@example.com", "password123")

        assert user.email == "new@example.com"
        assert user.hashed_password == "hashed"
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    async def test_register_duplicate_email(self, service, mock_db):
        existing_user = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError, match="already exists"):
            await service.register("existing@example.com", "password123")

    async def test_register_short_password(self, service, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="at least 8"):
            await service.register("new@example.com", "short")


class TestLogin:
    async def test_login_success(self, service, mock_db):
        user = MagicMock()
        user.id = "user-id"
        user.email = "test@example.com"
        user.hashed_password = "hashed"
        user.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        with (
            patch("app.modules.auth.service.verify_password", return_value=True),
            patch("app.modules.auth.service.create_access_token", return_value="access"),
            patch("app.modules.auth.service.create_refresh_token", return_value="refresh"),
        ):
            tokens = await service.login("test@example.com", "password123")

        assert tokens["access_token"] == "access"
        assert tokens["refresh_token"] == "refresh"
        assert tokens["token_type"] == "bearer"

    async def test_login_wrong_password(self, service, mock_db):
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

    async def test_login_user_not_found(self, service, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(AuthorizationError, match="Invalid"):
            await service.login("nobody@example.com", "password123")

    async def test_login_inactive_user(self, service, mock_db):
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
