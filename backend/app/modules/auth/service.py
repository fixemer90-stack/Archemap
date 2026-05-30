"""Authentication business logic."""

from __future__ import annotations

from datetime import date, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.core.token_blacklist import blacklist_token
from app.modules.auth.verification import VerificationService
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(
        self,
        email: str,
        password: str,
        birth_date: date,
        birth_place: str,
        latitude: float,
        longitude: float,
        timezone: str,
        birth_time: time | None = None,
        birth_time_accuracy: str = "unknown",
    ) -> User:
        """Register a new user with email, password and full birth data."""
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ConflictError("User with this email already exists")

        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        # If time not provided, default to 12:00 and mark as unknown
        if birth_time is None:
            birth_time = time(12, 0)
            birth_time_accuracy = "unknown"

        user = User(
            email=email,
            hashed_password=hash_password(password),
            birth_date=birth_date,
        )
        self.db.add(user)
        await self.db.flush()

        # Create PersonProfile with birth data for chart computation
        profile = PersonProfile(
            user_id=user.id,
            name=email.split("@")[0],  # default name from email
            birth_date=birth_date,
            birth_time=birth_time,
            birth_time_accuracy=birth_time_accuracy,
            birth_place=birth_place,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
        )
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(user)

        # Create verification token and send email
        verification_service = VerificationService(self.db)
        token = await verification_service.create_verification(user.id)
        await verification_service.send_verification_email(email, token)

        return user

    async def login(self, email: str, password: str) -> dict[str, str]:
        """Authenticate user and return tokens."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None or not verify_password(password, user.hashed_password):
            raise AuthorizationError("Invalid email or password")

        if not user.is_active:
            raise AuthorizationError("Account is deactivated")

        if not user.is_verified:
            raise AuthorizationError("Email not verified. Please check your inbox.")

        access_token, _ = create_access_token(subject=str(user.id))
        refresh_token, _ = create_refresh_token(subject=str(user.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def logout(self, access_token: str, refresh_token: str | None = None) -> None:
        """Blacklist tokens to log out the user."""
        # Blacklist access token
        payload = decode_access_token(access_token)
        if payload and payload.get("jti"):
            await blacklist_token(payload["jti"])

        # Blacklist refresh token if provided
        if refresh_token:
            refresh_payload = decode_refresh_token(refresh_token)
            if refresh_payload and refresh_payload.get("jti"):
                await blacklist_token(refresh_payload["jti"])

    async def get_user_by_id(self, user_id: UUID) -> User:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def refresh_tokens(self, refresh_token: str) -> dict[str, str]:
        """Issue new access token from refresh token."""
        payload = decode_refresh_token(refresh_token)
        if payload is None:
            raise AuthorizationError("Invalid or expired refresh token")

        user_id = UUID(payload["sub"])
        user = await self.get_user_by_id(user_id)

        if not user.is_active:
            raise AuthorizationError("Account is deactivated")

        # Blacklist old refresh token
        if payload.get("jti"):
            await blacklist_token(payload["jti"])

        new_access, _ = create_access_token(subject=str(user.id))
        new_refresh, _ = create_refresh_token(subject=str(user.id))

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
        }
