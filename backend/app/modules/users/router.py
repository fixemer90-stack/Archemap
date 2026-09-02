"""User endpoints."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.auth.schemas import UserResponse
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/users", tags=["users"])


class UpdateUserRequest(BaseModel):
    """Request to update user profile."""

    name: str | None = Field(None, min_length=1, max_length=120)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get current authenticated user profile."""
    service = AuthService(db)
    user = await service.get_user_by_id(current_user_id)
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        birth_date=user.birth_date,
        account_tier=user.account_tier,
        is_active=user.is_active,
        is_verified=user.is_verified,
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UpdateUserRequest,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update current user profile."""
    service = AuthService(db)
    user = await service.get_user_by_id(current_user_id)

    if body.name is not None:
        user.name = body.name.strip()

    await db.flush()

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        birth_date=user.birth_date,
        account_tier=user.account_tier,
        is_active=user.is_active,
        is_verified=user.is_verified,
    )
