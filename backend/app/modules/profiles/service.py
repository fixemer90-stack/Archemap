"""Profile business logic — CRUD for PersonProfile."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.profiles.models import PersonProfile
from app.modules.profiles.schemas import CreateProfileRequest, UpdateProfileRequest

MIN_BIRTH_YEAR = 1900
MAX_BIRTH_YEAR = 2100


class ProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Validation ────────────────────────────────────────────────────
    @staticmethod
    def _validate_birth_date(birth_date: date) -> None:
        if birth_date.year < MIN_BIRTH_YEAR or birth_date.year > MAX_BIRTH_YEAR:
            raise ValidationError(
                f"Birth year must be between {MIN_BIRTH_YEAR} and {MAX_BIRTH_YEAR}, got {birth_date.year}"
            )

    # ── Create ────────────────────────────────────────────────────────
    async def create(self, user_id: UUID, data: CreateProfileRequest) -> PersonProfile:
        self._validate_birth_date(data.birth_date)

        profile = PersonProfile(
            user_id=user_id,
            name=data.name,
            birth_date=data.birth_date,
            birth_time=data.birth_time,
            birth_time_accuracy=data.birth_time_accuracy,
            birth_place=data.birth_place,
            latitude=data.latitude,
            longitude=data.longitude,
            timezone=data.timezone,
        )
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    # ── Read one ──────────────────────────────────────────────────────
    async def get_by_id(self, profile_id: UUID, user_id: UUID) -> PersonProfile:
        result = await self.db.execute(
            select(PersonProfile).where(
                PersonProfile.id == profile_id,
                PersonProfile.user_id == user_id,
            )
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise NotFoundError("Profile not found")
        return profile

    # ── List ──────────────────────────────────────────────────────────
    async def list_by_user(self, user_id: UUID) -> tuple[list[PersonProfile], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(PersonProfile).where(PersonProfile.user_id == user_id)
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(PersonProfile)
            .where(PersonProfile.user_id == user_id)
            .order_by(PersonProfile.created_at.desc())
        )
        profiles = list(result.scalars().all())
        return profiles, total

    # ── Update ────────────────────────────────────────────────────────
    async def update(
        self, profile_id: UUID, user_id: UUID, data: UpdateProfileRequest
    ) -> PersonProfile:
        profile = await self.get_by_id(profile_id, user_id)

        update_data = data.model_dump(exclude_unset=True)
        if "birth_date" in update_data and update_data["birth_date"] is not None:
            self._validate_birth_date(update_data["birth_date"])

        for field, value in update_data.items():
            setattr(profile, field, value)

        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    # ── Delete ────────────────────────────────────────────────────────
    async def delete(self, profile_id: UUID, user_id: UUID) -> None:
        profile = await self.get_by_id(profile_id, user_id)
        await self.db.delete(profile)
        await self.db.flush()
