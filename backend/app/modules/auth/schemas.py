"""Auth request/response schemas."""

from __future__ import annotations

from datetime import date, time

from pydantic import BaseModel, EmailStr, Field, model_validator


def _validate_birth_coordinates(latitude: float, longitude: float) -> None:
    """Reject the default (0, 0) placeholder that means 'place not geocoded'."""
    if latitude == 0.0 and longitude == 0.0:
        raise ValueError("Выберите место рождения из списка: координаты места рождения не определены")


class RegisterRequest(BaseModel):
    """Register with full birth data for immediate chart computation."""

    email: EmailStr
    password: str  # min 8 chars validated in service
    name: str = Field(..., min_length=1, max_length=120, description="Display name")
    birth_date: date = Field(..., description="Date of birth (YYYY-MM-DD)")
    birth_time: time | None = Field(None, description="Time of birth (HH:MM). Null if unknown")
    birth_time_accuracy: str = Field(
        default="unknown",
        pattern=r"^(exact|approximate|unknown)$",
        description="Time accuracy: exact, approximate, or unknown",
    )
    birth_place: str = Field(..., min_length=1, max_length=300, description="City of birth")
    latitude: float = Field(..., ge=-90, le=90, description="Birth place latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Birth place longitude")
    timezone: str = Field(..., min_length=1, max_length=60, description="IANA timezone, e.g. Europe/Moscow")

    @model_validator(mode="after")
    def _coordinates_must_be_geocoded(self) -> RegisterRequest:
        _validate_birth_coordinates(self.latitude, self.longitude)
        return self


class CompleteProfileRequest(BaseModel):
    """Complete OAuth profile with name and birth data (no email/password needed)."""

    name: str = Field(..., min_length=1, max_length=120, description="Display name")
    birth_date: date = Field(..., description="Date of birth (YYYY-MM-DD)")
    birth_time: time | None = Field(None, description="Time of birth (HH:MM). Null if unknown")
    birth_time_accuracy: str = Field(
        default="unknown",
        pattern=r"^(exact|approximate|unknown)$",
        description="Time accuracy: exact, approximate, or unknown",
    )
    birth_place: str = Field(..., min_length=1, max_length=300, description="City of birth")
    latitude: float = Field(..., ge=-90, le=90, description="Birth place latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Birth place longitude")
    timezone: str = Field(..., min_length=1, max_length=60, description="IANA timezone, e.g. Europe/Moscow")

    @model_validator(mode="after")
    def _coordinates_must_be_geocoded(self) -> CompleteProfileRequest:
        _validate_birth_coordinates(self.latitude, self.longitude)
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    birth_date: date | None
    account_tier: str = "free"
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


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str  # min 8 chars validated in service


class RateLimitErrorResponse(BaseModel):
    detail: str
    retry_after: int


class LinkedProviderResponse(BaseModel):
    """Linked OAuth provider info."""

    provider: str
    provider_email: str | None
    provider_name: str | None
    linked_at: str  # ISO datetime

    model_config = {"from_attributes": True}


class LinkedProvidersListResponse(BaseModel):
    """List of linked providers."""

    providers: list[LinkedProviderResponse]
    has_password: bool
