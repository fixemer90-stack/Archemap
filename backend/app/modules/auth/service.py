"""Authentication business logic."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chart_engine.chart import build_chart
from app.chart_engine.features import extract_features
from app.chart_engine.socionics import evaluate_socionics
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.core.token_blacklist import blacklist_token, is_token_blacklisted
from app.modules.auth.verification import VerificationService
from app.modules.charts.models import ChartSnapshot
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
    ) -> dict[str, Any]:
        """Register a new user with email, password and full birth data.

        Automatically computes natal chart and socionics type.
        Returns user data, tokens, and chart results.
        """
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

        # Compute natal chart
        chart_data, features_data, strengths_data, socionics_result = await self._compute_chart(profile)

        # Store chart snapshot with all intermediate data
        snapshot = ChartSnapshot(
            profile_id=profile.id,
            user_id=user.id,
            engine_version="0.1.0",
            birth_data={
                "date": profile.birth_date.isoformat(),
                "time": profile.birth_time.isoformat() if profile.birth_time else None,
                "time_accuracy": profile.birth_time_accuracy,
                "place": profile.birth_place,
                "latitude": profile.latitude,
                "longitude": profile.longitude,
                "timezone": profile.timezone,
            },
            chart_data=chart_data,
            features=features_data,
            function_strengths=strengths_data,
            socionics=socionics_result,
        )
        self.db.add(snapshot)
        await self.db.flush()
        await self.db.refresh(user)

        # Create verification token and send email
        verification_service = VerificationService(self.db)
        token = await verification_service.create_verification(user.id)
        await verification_service.send_verification_email(email, token)

        # Issue tokens
        jwt_access, _ = create_access_token(subject=str(user.id))
        jwt_refresh, _ = create_refresh_token(subject=str(user.id))

        return {
            "user_id": str(user.id),
            "email": email,
            "birth_date": birth_date.isoformat(),
            "profile_id": str(profile.id),
            "access_token": jwt_access,
            "refresh_token": jwt_refresh,
            "token_type": "bearer",
            "chart": chart_data,
            "socionics": socionics_result,
        }

    async def _compute_chart(
        self, profile: PersonProfile
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Compute natal chart and socionics type from profile data.

        Returns: (chart_data, features, function_strengths, socionics)
        """
        # Combine date and time into UTC datetime
        # birth_time is guaranteed to be non-None (set to 12:00 if not provided)
        birth_time = profile.birth_time or time(12, 0)
        local_tz = ZoneInfo(profile.timezone)
        dt_local = datetime.combine(profile.birth_date, birth_time).replace(tzinfo=local_tz)
        dt_utc = dt_local.astimezone(UTC)

        # Compute chart
        chart = build_chart(
            birth_datetime=dt_utc,
            latitude=profile.latitude,
            longitude=profile.longitude,
            timezone_name=profile.timezone,
            house_system="P",
        )

        # Extract features and compute socionics
        features = extract_features(chart)
        socionics_results = evaluate_socionics(features, chart)

        # Prepare chart data for JSON storage
        chart_json = {
            "planets": [
                {
                    "name": p.name,
                    "sign": p.sign,
                    "degree": round(p.sign_degree, 2),
                    "house": p.house,
                    "is_retrograde": p.is_retrograde,
                }
                for p in chart.planets
            ],
            "houses": [{"number": h.number, "sign": h.sign, "longitude": round(h.longitude, 2)} for h in chart.houses],
            "aspects": [
                {
                    "planet_a": a.planet_a,
                    "aspect_type": a.aspect_type,
                    "planet_b": a.planet_b,
                    "orb": round(a.orb, 2),
                    "is_applying": a.is_applying,
                }
                for a in chart.aspects
            ],
        }

        # Prepare features data
        features_json = {
            "fire": round(features.fire, 3),
            "earth": round(features.earth, 3),
            "air": round(features.air, 3),
            "water": round(features.water, 3),
            "cardinal": round(features.cardinal, 3),
            "fixed": round(features.fixed, 3),
            "mutable": round(features.mutable, 3),
        }

        # Prepare function strengths
        top1 = socionics_results[0]
        strengths_json = {
            fn: round(top1.breakdown.get(fn, 0), 3) for fn in ["Se", "Si", "Ne", "Ni", "Fe", "Fi", "Te", "Ti"]
        }

        # Prepare socionics result
        top3 = socionics_results[:3]
        socionics_json = {
            "top3": [
                {
                    "type": r.type_code,
                    "name": r.type_name,
                    "score": round(r.score, 3),
                    "confidence": round(r.confidence, 3),
                    "functions": r.functions,
                    "model_a": round(r.breakdown.get("model_a", 0), 3),
                }
                for r in top3
            ],
        }

        return chart_json, features_json, strengths_json, socionics_json

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

        # Check if refresh token is blacklisted (CRIT-02)
        jti = payload.get("jti")
        if jti and await is_token_blacklisted(jti):
            raise AuthorizationError("Refresh token has been revoked")

        user_id = UUID(payload["sub"])
        user = await self.get_user_by_id(user_id)

        if not user.is_active:
            raise AuthorizationError("Account is deactivated")

        # Blacklist old refresh token
        if jti:
            await blacklist_token(jti)

        new_access, _ = create_access_token(subject=str(user.id))
        new_refresh, _ = create_refresh_token(subject=str(user.id))

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
        }

    async def complete_oauth_profile(
        self,
        user_id: UUID,
        birth_date: date,
        birth_place: str,
        latitude: float,
        longitude: float,
        timezone: str,
        birth_time: time | None = None,
        birth_time_accuracy: str = "unknown",
    ) -> dict[str, Any]:
        """Complete OAuth user profile with birth data.

        Creates PersonProfile and computes chart.
        """
        user = await self.get_user_by_id(user_id)

        if not user.is_active:
            raise AuthorizationError("Account is deactivated")

        # Check if profile already exists
        existing = await self.db.execute(select(PersonProfile).where(PersonProfile.user_id == user_id))
        if existing.scalar_one_or_none() is not None:
            raise ValidationError("Profile already exists")

        # If time not provided, default to 12:00
        if birth_time is None:
            birth_time = time(12, 0)
            birth_time_accuracy = "unknown"

        # Update user birth_date
        user.birth_date = birth_date

        # Create PersonProfile
        profile = PersonProfile(
            user_id=user_id,
            name=user.email.split("@")[0],
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

        # Compute chart
        chart_data, features_data, strengths_data, socionics_result = await self._compute_chart(profile)

        # Store chart snapshot
        snapshot = ChartSnapshot(
            profile_id=profile.id,
            user_id=user_id,
            engine_version="0.1.0",
            birth_data={
                "date": profile.birth_date.isoformat(),
                "time": profile.birth_time.isoformat() if profile.birth_time else None,
                "time_accuracy": profile.birth_time_accuracy,
                "place": profile.birth_place,
                "latitude": profile.latitude,
                "longitude": profile.longitude,
                "timezone": profile.timezone,
            },
            chart_data=chart_data,
            features=features_data,
            function_strengths=strengths_data,
            socionics=socionics_result,
        )
        self.db.add(snapshot)
        await self.db.flush()

        return {
            "profile_id": str(profile.id),
            "chart": chart_data,
            "socionics": socionics_result,
        }
