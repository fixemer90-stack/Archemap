"""OAuth service — handles social login flows."""

from __future__ import annotations

import secrets
from datetime import date, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ValidationError
from app.core.security import create_access_token, create_refresh_token
from app.infrastructure.redis import get_redis_client
from app.modules.auth.models import IdentityLink
from app.modules.auth.oauth.yandex import YandexOAuthProvider
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User

logger = structlog.get_logger()

OAUTH_STATE_TTL = 600  # 10 minutes


class OAuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.redis = get_redis_client()

    # ── State management ────────────────────────────────────────────
    async def create_state(self, provider: str) -> str:
        """Generate and store OAuth state token."""
        state = secrets.token_urlsafe(32)
        key = f"oauth:state:{state}"
        await self.redis.set(key, provider, ex=OAUTH_STATE_TTL)
        return state

    async def validate_state(self, state: str) -> str | None:
        """Validate state and return provider name. Returns None if invalid."""
        key = f"oauth:state:{state}"
        provider = await self.redis.get(key)
        if provider:
            await self.redis.delete(key)
        return str(provider) if provider else None

    # ── Yandex flow ────────────────────────────────────────────────
    async def get_yandex_authorize_url(self) -> str:
        """Get Yandex authorization URL."""
        state = await self.create_state("yandex")
        provider = YandexOAuthProvider()
        return provider.get_authorize_url(state)

    async def handle_yandex_callback(self, code: str, state: str) -> dict[str, Any]:
        """Handle Yandex OAuth callback. Returns tokens."""
        # Validate state
        provider = await self.validate_state(state)
        if provider != "yandex":
            raise ValidationError("Invalid or expired OAuth state")

        # Exchange code for tokens
        yandex = YandexOAuthProvider()
        token_data = await yandex.exchange_code(code)
        access_token = token_data.get("access_token")
        if not access_token:
            raise AuthorizationError("Failed to get access token from Yandex")

        # Get user info
        user_info = await yandex.get_user_info(access_token)
        yandex_id = user_info.get("id")
        emails = user_info.get("emails", [])
        email = user_info.get("default_email") or (emails[0] if emails else None)
        name = user_info.get("real_name") or user_info.get("display_name") or user_info.get("login")

        # Parse birthday (YYYY-MM-DD format from Yandex)
        birth_date: date | None = None
        birthday_str = user_info.get("birthday")
        if birthday_str:
            try:
                birth_date = datetime.strptime(birthday_str, "%Y-%m-%d").date()
            except ValueError:
                logger.warning("yandex_birthday_parse_failed", birthday=birthday_str)

        if not yandex_id:
            raise AuthorizationError("Failed to get user ID from Yandex")

        # Find or create user
        user = await self._find_or_create_user(
            provider="yandex",
            provider_user_id=str(yandex_id),
            provider_email=email,
            provider_name=name,
            provider_access_token=access_token,
            birth_date=birth_date,
        )

        # Issue our tokens
        jwt_access, _ = create_access_token(subject=str(user.id))
        jwt_refresh, _ = create_refresh_token(subject=str(user.id))

        # Check if user has a complete profile
        profile_result = await self.db.execute(select(PersonProfile).where(PersonProfile.user_id == user.id))
        has_profile = profile_result.scalar_one_or_none() is not None

        return {
            "access_token": jwt_access,
            "refresh_token": jwt_refresh,
            "token_type": "bearer",
            "birth_date": birth_date.isoformat() if birth_date else None,
            "has_profile": has_profile,
            "email": email,
        }

    # ── Account linking ────────────────────────────────────────────
    async def _find_or_create_user(
        self,
        provider: str,
        provider_user_id: str,
        provider_email: str | None,
        provider_name: str | None,
        provider_access_token: str | None,
        birth_date: date | None = None,
    ) -> User:
        """Find existing user by identity link or email, or create new."""
        # 1. Check if identity link exists
        result = await self.db.execute(
            select(IdentityLink).where(
                IdentityLink.provider == provider,
                IdentityLink.provider_user_id == provider_user_id,
            )
        )
        link = result.scalar_one_or_none()

        if link:
            # Existing link — get user
            user_result = await self.db.execute(select(User).where(User.id == link.user_id))
            user = user_result.scalar_one_or_none()
            if user and user.is_active:
                # Update tokens
                link.access_token = provider_access_token
                # Update birth_date if we got it and user doesn't have one
                if birth_date and not user.birth_date:
                    user.birth_date = birth_date
                await self.db.flush()
                return user

        # 2. Try to find by email
        if provider_email:
            email_result = await self.db.execute(select(User).where(User.email == provider_email))
            matched_user = email_result.scalar_one_or_none()

            if matched_user:
                # Link existing user
                new_link = IdentityLink(
                    user_id=matched_user.id,
                    provider=provider,
                    provider_user_id=provider_user_id,
                    provider_email=provider_email,
                    provider_name=provider_name,
                    access_token=provider_access_token,
                )
                self.db.add(new_link)
                matched_user.is_verified = True  # OAuth emails are considered verified
                # Update birth_date if we got it and user doesn't have one
                if birth_date and not matched_user.birth_date:
                    matched_user.birth_date = birth_date
                await self.db.flush()
                logger.info("oauth_account_linked", user_id=str(matched_user.id), provider=provider)
                return matched_user

        # 3. Create new user
        if not provider_email:
            provider_email = f"{provider}_{provider_user_id}@archemap.local"

        user = User(
            email=provider_email,
            hashed_password="",  # OAuth users don't have a password
            birth_date=birth_date,
            is_active=True,
            is_verified=True,  # OAuth emails are considered verified
        )
        self.db.add(user)
        await self.db.flush()

        # Create identity link
        new_link = IdentityLink(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            provider_name=provider_name,
            access_token=provider_access_token,
        )
        self.db.add(new_link)
        await self.db.flush()

        logger.info(
            "oauth_user_created",
            user_id=str(user.id),
            provider=provider,
            has_birth_date=birth_date is not None,
        )
        return user
