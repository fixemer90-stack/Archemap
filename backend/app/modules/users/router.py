"""User endpoints."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.auth.schemas import UserResponse
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/users", tags=["users"])


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
        birth_date=user.birth_date,
        is_active=user.is_active,
        is_verified=user.is_verified,
    )
