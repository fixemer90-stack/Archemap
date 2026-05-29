"""Authentication endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.modules.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Register a new user with email and password."""
    service = AuthService(db)
    user = await service.register(email=body.email, password=body.password)
    return UserResponse(id=str(user.id), email=user.email, is_active=user.is_active)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Authenticate with email and password."""
    service = AuthService(db)
    tokens = await service.login(email=body.email, password=body.password)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: TokenResponse,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get new tokens using refresh token."""
    service = AuthService(db)
    tokens = await service.refresh_tokens(body.refresh_token)
    return TokenResponse(**tokens)
