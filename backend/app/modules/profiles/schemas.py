"""Profile request/response schemas."""

from __future__ import annotations

from datetime import date, time

from pydantic import BaseModel, Field


class CreateProfileRequest(BaseModel):
    """Create a new person profile with birth data."""

    name: str = Field(..., min_length=1, max_length=120)
    birth_date: date
    birth_time: time | None = None
    birth_time_accuracy: str = Field(default="unknown", pattern=r"^(exact|approximate|unknown)$")
    birth_place: str = Field(..., min_length=1, max_length=300)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timezone: str = Field(..., min_length=1, max_length=60)


class UpdateProfileRequest(BaseModel):
    """Update an existing person profile. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    birth_date: date | None = None
    birth_time: time | None = None
    birth_time_accuracy: str | None = Field(default=None, pattern=r"^(exact|approximate|unknown)$")
    birth_place: str | None = Field(default=None, min_length=1, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, min_length=1, max_length=60)


class ProfileResponse(BaseModel):
    """Profile data returned to the client."""

    id: str
    user_id: str
    name: str
    birth_date: date
    birth_time: time | None
    birth_time_accuracy: str
    birth_place: str
    latitude: float
    longitude: float
    timezone: str

    model_config = {"from_attributes": True}


class ProfileListResponse(BaseModel):
    """Paginated list of profiles."""

    items: list[ProfileResponse]
    total: int
