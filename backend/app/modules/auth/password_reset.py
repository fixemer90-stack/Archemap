"""Password reset business logic."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ValidationError
from app.core.security import hash_password
from app.infrastructure.email import get_email_provider
from app.infrastructure.email_templates import password_reset_template
from app.modules.auth.models import PasswordReset
from app.modules.users.models import User

logger = structlog.get_logger()

RESET_TOKEN_EXPIRE_HOURS = 1
RESET_TOKEN_LENGTH = 32


class PasswordResetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _generate_token(self) -> str:
        return secrets.token_urlsafe(RESET_TOKEN_LENGTH)

    async def request_reset(self, email: str) -> None:
        """Create reset token and send email. Anti-enumeration: always succeeds."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            return  # anti-enumeration

        # Invalidate existing tokens
        await self.db.execute(
            update(PasswordReset)
            .where(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None))
            .values(used_at=datetime.now(UTC))
        )

        token = self._generate_token()
        reset = PasswordReset(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(UTC) + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS),
        )
        self.db.add(reset)
        await self.db.flush()

        reset_link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
        html_body, text_body = password_reset_template(reset_link)

        provider = get_email_provider()
        await provider.send(
            to=email,
            subject="Reset your password — Astrotype",
            html_body=html_body,
            text_body=text_body,
        )

        logger.info("password_reset_requested", email=email)

    async def confirm_reset(self, token: str, new_password: str) -> None:
        """Reset password using token."""
        if len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        result = await self.db.execute(
            select(PasswordReset).where(
                PasswordReset.token == token,
                PasswordReset.used_at.is_(None),
            )
        )
        reset = result.scalar_one_or_none()

        if reset is None:
            raise ValidationError("Invalid or already used reset token")

        if reset.expires_at < datetime.now(UTC):
            raise ValidationError("Reset token has expired")

        # Mark token as used
        reset.used_at = datetime.now(UTC)

        # Update password
        user_result = await self.db.execute(select(User).where(User.id == reset.user_id))
        user = user_result.scalar_one_or_none()

        if user is None:
            raise ValidationError("User not found")

        user.hashed_password = hash_password(new_password)
        await self.db.flush()

        logger.info("password_reset_completed", user_id=str(user.id))
