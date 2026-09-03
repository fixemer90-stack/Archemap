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
        assert result["requires_verification"] is True
        assert "access_token" not in result
        assert "refresh_token" not in result
        assert "chart" not in result
        assert "socionics" not in result

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

    async def test_login_normalizes_email_case_and_whitespace(self, service: AuthService, mock_db: AsyncMock) -> None:
        user = MagicMock()
        user.id = "user-id"
        user.email = "balthier90@mail.ru"
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
            tokens = await service.login("  Balthier90@mail.ru  ", TEST_PASSWORD)

        compiled_query = str(mock_db.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True}))
        assert "lower(users.email) = 'balthier90@mail.ru'" in compiled_query
        assert tokens["access_token"] == "access"

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
            pytest.raises(AuthorizationError, match="не подтверждён"),
        ):
            await service.login("unverified@example.com", TEST_PASSWORD)

    async def test_refresh_unverified_user_rejected(self, service: AuthService, mock_db: AsyncMock) -> None:
        user = MagicMock()
        user.id = "user-id"
        user.is_active = True
        user.is_verified = False
        service.get_user_by_id = AsyncMock(return_value=user)  # type: ignore[method-assign]

        refresh_payload = {
            "sub": "00000000-0000-0000-0000-000000000001",
            "jti": "jti",
        }

        with (
            patch("app.modules.auth.service.decode_refresh_token", return_value=refresh_payload),
            patch("app.modules.auth.service.is_token_blacklisted", new=AsyncMock(return_value=False)),
            pytest.raises(AuthorizationError, match="не подтверждён"),
        ):
            await service.refresh_tokens("refresh")


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


class TestVerificationLinks:
    async def test_verification_email_uses_configured_frontend_url(
        self, mock_db: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.modules.auth import verification as verification_module

        sent: dict[str, str] = {}

        class Provider:
            async def send(self, to: str, subject: str, html_body: str, text_body: str = "") -> None:
                sent["html"] = html_body
                sent["text"] = text_body

        from app.config import settings

        monkeypatch.setattr(settings, "FRONTEND_URL", "https://astrotype.ru/")
        monkeypatch.setattr(
            verification_module,
            "verify_email_template",
            lambda link: (f"html:{link}", f"text:{link}"),
        )
        monkeypatch.setattr(verification_module, "get_email_provider", lambda: Provider())

        service = verification_module.VerificationService(mock_db)
        await service.send_verification_email("user@example.com", "token123")

        assert "https://astrotype.ru/verify?token=token123" in sent["html"]
        assert "http://localhost:3000" not in sent["html"]


class TestPasswordResetLinks:
    async def test_password_reset_email_uses_configured_frontend_url(
        self, mock_db: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.modules.auth import password_reset as password_reset_module

        user = MagicMock()
        user.id = "user-id"
        result = MagicMock()
        result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = result
        sent: dict[str, str] = {}

        class Provider:
            async def send(self, to: str, subject: str, html_body: str, text_body: str = "") -> None:
                sent["html"] = html_body
                sent["text"] = text_body

        from app.config import settings

        monkeypatch.setattr(settings, "FRONTEND_URL", "https://astrotype.ru/")
        monkeypatch.setattr(password_reset_module.PasswordResetService, "_generate_token", lambda self: "reset123")
        monkeypatch.setattr(
            password_reset_module,
            "password_reset_template",
            lambda link: (f"html:{link}", f"text:{link}"),
        )
        monkeypatch.setattr(password_reset_module, "get_email_provider", lambda: Provider())

        service = password_reset_module.PasswordResetService(mock_db)
        await service.request_reset("user@example.com")

        assert "https://astrotype.ru/reset-password?token=reset123" in sent["html"]
        assert "http://localhost:3000" not in sent["html"]
