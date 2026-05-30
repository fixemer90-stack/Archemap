"""Profile endpoints — CRUD for PersonProfile."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.profiles.schemas import (
    CreateProfileRequest,
    ProfileListResponse,
    ProfileResponse,
    UpdateProfileRequest,
)
from app.modules.profiles.service import ProfileService

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    body: CreateProfileRequest,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new person profile with birth data."""
    service = ProfileService(db)
    profile = await service.create(user_id=current_user_id, data=body)
    return ProfileResponse(
        id=str(profile.id),
        user_id=str(profile.user_id),
        name=profile.name,
        birth_date=profile.birth_date,
        birth_time=profile.birth_time,
        birth_time_accuracy=profile.birth_time_accuracy,
        birth_place=profile.birth_place,
        latitude=profile.latitude,
        longitude=profile.longitude,
        timezone=profile.timezone,
    )


@router.get("", response_model=ProfileListResponse)
async def list_profiles(
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all profiles for the current user."""
    service = ProfileService(db)
    profiles, total = await service.list_by_user(user_id=current_user_id)
    return ProfileListResponse(
        items=[
            ProfileResponse(
                id=str(p.id),
                user_id=str(p.user_id),
                name=p.name,
                birth_date=p.birth_date,
                birth_time=p.birth_time,
                birth_time_accuracy=p.birth_time_accuracy,
                birth_place=p.birth_place,
                latitude=p.latitude,
                longitude=p.longitude,
                timezone=p.timezone,
            )
            for p in profiles
        ],
        total=total,
    )


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: UUID,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a single profile by ID."""
    service = ProfileService(db)
    profile = await service.get_by_id(profile_id=profile_id, user_id=current_user_id)
    return ProfileResponse(
        id=str(profile.id),
        user_id=str(profile.user_id),
        name=profile.name,
        birth_date=profile.birth_date,
        birth_time=profile.birth_time,
        birth_time_accuracy=profile.birth_time_accuracy,
        birth_place=profile.birth_place,
        latitude=profile.latitude,
        longitude=profile.longitude,
        timezone=profile.timezone,
    )


@router.patch("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: UUID,
    body: UpdateProfileRequest,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update an existing profile. Only provided fields are changed."""
    service = ProfileService(db)
    profile = await service.update(profile_id=profile_id, user_id=current_user_id, data=body)
    return ProfileResponse(
        id=str(profile.id),
        user_id=str(profile.user_id),
        name=profile.name,
        birth_date=profile.birth_date,
        birth_time=profile.birth_time,
        birth_time_accuracy=profile.birth_time_accuracy,
        birth_place=profile.birth_place,
        latitude=profile.latitude,
        longitude=profile.longitude,
        timezone=profile.timezone,
    )


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: UUID,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a profile."""
    service = ProfileService(db)
    await service.delete(profile_id=profile_id, user_id=current_user_id)
