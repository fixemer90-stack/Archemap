"""Auth request/response schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str  # min 8 chars validated in service
    birth_date: date = Field(..., description="Date of birth (YYYY-MM-DD)")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    birth_date: date | None
    is_active: bool
    is_verified: bool

    model_config = {"from_attributes": True}


class VerifyRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str  # min 8 chars validated in service


class RateLimitErrorResponse(BaseModel):
    detail: str
    retry_after: int
