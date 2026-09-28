"""Profile request/response schemas."""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

    @model_validator(mode="after")
    def _coordinates_must_be_geocoded(self) -> CreateProfileRequest:
        if self.latitude == 0.0 and self.longitude == 0.0:
            raise ValueError("Выберите место рождения из списка: координаты места рождения не определены")
        return self


class UpdateProfileRequest(BaseModel):
    """Update profile metadata; birth data uses the refinement endpoint."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)


class BirthDataRefinementRequest(BaseModel):
    """Complete final birth time/place snapshot; birth date is intentionally absent."""

    model_config = ConfigDict(extra="forbid")

    birth_time: time | None
    birth_time_accuracy: str = Field(pattern=r"^(exact|approximate|unknown)$")
    birth_place: str = Field(min_length=1, max_length=300)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = Field(min_length=1, max_length=60)


class BirthDataRefinementStatusResponse(BaseModel):
    profile_id: UUID
    can_refine: bool
    last_refined_at: datetime | None
    next_available_at: datetime | None
    retry_after_seconds: int


class BirthDataRefinementAcceptedResponse(BaseModel):
    revision_id: UUID
    generation_id: UUID
    profile_id: UUID
    changed_fields: list[str]
    status: str
    next_available_at: datetime


class BirthDataRevisionStatusResponse(BaseModel):
    revision_id: UUID
    generation_id: UUID
    profile_id: UUID
    changed_fields: list[str]
    status: str
    chart_id: UUID | None
    report_id: UUID | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime


class RefinementErrorResponse(BaseModel):
    detail: str
    code: str


class RefinementCooldownResponse(RefinementErrorResponse):
    next_available_at: datetime
    retry_after_seconds: int


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


class GeocodeResultItem(BaseModel):
    """A single geocoding search result."""

    display_name: str
    latitude: float
    longitude: float
    city: str
    country: str
    timezone: str


class GeocodeSearchResponse(BaseModel):
    """Geocoding search results."""

    items: list[GeocodeResultItem]
