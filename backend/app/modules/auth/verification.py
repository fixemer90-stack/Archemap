"""Email verification business logic."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.auth.models import EmailVerification
from app.modules.users.models import User

logger = structlog.get_logger()

VERIFICATION_TOKEN_EXPIRE_HOURS = 24
VERIFICATION_TOKEN_LENGTH = 32


class VerificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _generate_token(self) -> str:
        return secrets.token_urlsafe(VERIFICATION_TOKEN_LENGTH)

    async def create_verification(self, user_id: int) -> str:
        """Create a verification token for a user."""
        # Invalidate any existing tokens for this user
        await self.db.execute(
            update(EmailVerification)
            .where(EmailVerification.user_id == user_id, EmailVerification.used_at.is_(None))
            .values(used_at=datetime.now(UTC))
        )

        token = self._generate_token()
        verification = EmailVerification(
            user_id=user_id,
            token=token,
            expires_at=datetime.now(UTC) + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS),
        )
        self.db.add(verification)
        await self.db.flush()

        logger.info("verification_token_created", user_id=str(user_id))
        return token

    async def verify_email(self, token: str) -> User:
        """Verify email using token."""
        result = await self.db.execute(
            select(EmailVerification).where(
                EmailVerification.token == token,
                EmailVerification.used_at.is_(None),
            )
        )
        verification = result.scalar_one_or_none()

        if verification is None:
            raise ValidationError("Invalid or already used verification token")

        if verification.expires_at < datetime.now(UTC):
            raise ValidationError("Verification token has expired")

        # Mark token as used
        verification.used_at = datetime.now(UTC)

        # Mark user as verified
        user_result = await self.db.execute(select(User).where(User.id == verification.user_id))
        user = user_result.scalar_one_or_none()

        if user is None:
            raise NotFoundError("User not found")

        user.is_verified = True
        await self.db.flush()

        logger.info("email_verified", user_id=str(user.id))
        return user

    async def send_verification_email(self, email: str, token: str) -> None:
        """Send verification email.

        TODO: integrate with actual email provider (SMTP/SendGrid).
        For now, logs the verification link.
        """
        verification_link = f"http://localhost:3000/verify?token={token}"
        logger.info(
            "verification_email_sent",
            email=email,
            link=verification_link,
        )
        # In production, this would send an actual email:
        # await email_provider.send(
        #     to=email,
        #     subject="Verify your email - Archemap",
        #     template="verify-email",
        #     context={"link": verification_link},
        # )
