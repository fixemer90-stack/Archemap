"""Authentication business logic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.modules.auth.verification import VerificationService
from app.modules.users.models import User


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, email: str, password: str) -> User:
        """Register a new user with email and password."""
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ConflictError("User with this email already exists")

        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        user = User(
            email=email,
            hashed_password=hash_password(password),
        )
        self.db.add(user)
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

        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

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

        new_access = create_access_token(subject=str(user.id))
        new_refresh = create_refresh_token(subject=str(user.id))

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
        }
