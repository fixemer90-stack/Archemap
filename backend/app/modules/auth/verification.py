"""Email verification business logic."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.infrastructure.email import get_email_provider
from app.infrastructure.email_templates import resend_verification_template, verify_email_template
from app.modules.analytics.schemas import BusinessEventInput, EventType
from app.modules.analytics.service import emit_business_event
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

    async def create_verification(self, user_id: uuid.UUID) -> str:
        """Create a verification token for a user."""
        # Lock order shared with verification and account deletion: user, then token.
        await self.db.execute(select(User.id).where(User.id == user_id).with_for_update())
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
        user_id = await self.db.scalar(
            select(EmailVerification.user_id).where(
                EmailVerification.token == token, EmailVerification.used_at.is_(None)
            )
        )
        if user_id is None:
            raise ValidationError("Invalid or already used verification token")

        user_result = await self.db.execute(
            select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True)
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            raise NotFoundError("User not found")

        verification = await self.db.scalar(
            select(EmailVerification)
            .where(
                EmailVerification.token == token,
                EmailVerification.user_id == user.id,
                EmailVerification.used_at.is_(None),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if verification is None:
            raise ValidationError("Invalid or already used verification token")
        now = datetime.now(UTC)
        if verification.expires_at < now:
            raise ValidationError("Verification token has expired")
        verification.used_at = now
        first_verification = not user.is_verified
        user.is_verified = True
        await self.db.flush()
        if first_verification and settings.BUSINESS_MONITORING_ENABLED:
            await emit_business_event(
                self.db, BusinessEventInput(event_type=EventType.ACCOUNT_VERIFIED, entity_id=user.id, occurred_at=now)
            )

        logger.info("email_verified", user_id=str(user.id))
        return user

    async def send_verification_email(self, email: str, token: str) -> None:
        """Send verification email using configured provider."""
        link = f"{settings.FRONTEND_URL.rstrip('/')}/verify?token={token}"
        html_body, text_body = verify_email_template(link)

        provider = get_email_provider()
        await provider.send(
            to=email,
            subject="Подтвердите email — Astrotype",
            html_body=html_body,
            text_body=text_body,
        )

    async def resend_verification(self, email: str) -> None:
        """Resend verification email for a user."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None or user.is_verified:
            return  # anti-enumeration: don't reveal if user exists

        token = await self.create_verification(user.id)
        link = f"{settings.FRONTEND_URL.rstrip('/')}/verify?token={token}"
        html_body, text_body = resend_verification_template(link)

        provider = get_email_provider()
        await provider.send(
            to=email,
            subject="Подтвердите email — Astrotype",
            html_body=html_body,
            text_body=text_body,
        )
