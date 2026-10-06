"""Profile endpoints — CRUD for PersonProfile."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.infrastructure.geocoding import NominatimGeocoder
from app.infrastructure.redis import get_redis_client
from app.infrastructure.timezone import TimezoneResolver
from app.modules.profiles.dispatch import dispatch_birth_data_revision
from app.modules.profiles.observability import birth_data_refinement_telemetry
from app.modules.profiles.refinement import (
    COOLDOWN_WINDOW,
    BirthDataAccuracyMismatchError,
    BirthDataCooldownError,
    BirthDataIdempotencyConflictError,
    BirthDataNoChangesError,
    BirthDataPlaceNotGeocodedError,
    BirthDataProfileNotFoundError,
    BirthDataProfileNotOwnedError,
    BirthDataRefinementService,
    BirthDataRevisionRepository,
    create_geocode_selection_token,
    map_generation_status,
)
from app.modules.profiles.schemas import (
    BirthDataRefinementAcceptedResponse,
    BirthDataRefinementRequest,
    BirthDataRefinementStatusResponse,
    BirthDataRevisionStatusResponse,
    CreateProfileRequest,
    GeocodeResultItem,
    GeocodeSearchResponse,
    ProfileListResponse,
    ProfileResponse,
    RefinementCooldownResponse,
    RefinementErrorResponse,
    UpdateProfileRequest,
)
from app.modules.profiles.service import ProfileService

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get(
    "/geocode",
    response_model=GeocodeSearchResponse,
    responses={
        429: {
            "model": RefinementErrorResponse,
            "headers": {"Retry-After": {"schema": {"type": "string"}}},
        }
    },
)
async def geocode_search(
    q: str,
    request: Request,
) -> Any:
    """Search for places by name. Returns lat/lon/city/country. Cached 24h.

    WARN-04: Public endpoint (needed for registration), but rate-limited per IP.
    """
    # Validate query length
    if len(q.strip()) < 2:
        return GeocodeSearchResponse(items=[])
    if len(q) > 200:
        q = q[:200]

    # Rate limit per IP.
    redis = get_redis_client()
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"rate:geocode:{client_ip}"
    current = await redis.get(rate_key)
    if current and int(current) >= settings.RATE_LIMIT_GEOCODE_PER_MINUTE:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=429,
            content={"detail": "Too many geocode requests. Try again later.", "code": "geocode_rate_limited"},
            headers={"Retry-After": "60"},
        )
    await redis.incr(rate_key)
    if not current:
        await redis.expire(rate_key, 60)

    geocoder = NominatimGeocoder(redis)
    results = await geocoder.search(q, limit=5)
    return GeocodeSearchResponse(
        items=[
            GeocodeResultItem(
                display_name=r.display_name,
                latitude=r.latitude,
                longitude=r.longitude,
                city=r.city,
                country=r.country,
                timezone=r.timezone,
                selection_token=create_geocode_selection_token(
                    secret=settings.SECRET_KEY,
                    place=r.display_name,
                    latitude=r.latitude,
                    longitude=r.longitude,
                    timezone=r.timezone,
                ),
            )
            for r in results
        ]
    )


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


@router.get(
    "/{profile_id}/birth-data-refinement-status",
    response_model=BirthDataRefinementStatusResponse,
    responses={
        401: {"model": RefinementErrorResponse},
        403: {"model": RefinementErrorResponse},
        404: {"model": RefinementErrorResponse},
    },
)
async def get_birth_data_refinement_status(
    profile_id: UUID,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> BirthDataRefinementStatusResponse | JSONResponse:
    service = BirthDataRefinementService(
        db,
        timezone_resolver=TimezoneResolver(get_redis_client()),
        geocode_token_secret=settings.SECRET_KEY,
    )
    try:
        return await service.get_status(user_id=current_user_id, profile_id=profile_id)
    except BirthDataProfileNotOwnedError as exc:
        return _refinement_error(exc, status.HTTP_403_FORBIDDEN)
    except BirthDataProfileNotFoundError as exc:
        return _refinement_error(exc, status.HTTP_404_NOT_FOUND)


@router.post(
    "/{profile_id}/birth-data-refinements",
    response_model=BirthDataRefinementAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": RefinementErrorResponse},
        401: {"model": RefinementErrorResponse},
        403: {"model": RefinementErrorResponse},
        404: {"model": RefinementErrorResponse},
        409: {"model": RefinementErrorResponse},
        422: {"model": RefinementErrorResponse},
        429: {"model": RefinementCooldownResponse},
        503: {"model": RefinementErrorResponse},
    },
)
async def create_birth_data_refinement(
    profile_id: UUID,
    body: BirthDataRefinementRequest,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    db: AsyncSession = Depends(get_db),
) -> BirthDataRefinementAcceptedResponse | JSONResponse:
    if not settings.BIRTH_DATA_REFINEMENT_ENABLED:
        birth_data_refinement_telemetry.record_request("disabled")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "Birth-data refinement is temporarily disabled",
                "code": "birth_data_refinement_disabled",
            },
        )
    service = BirthDataRefinementService(
        db,
        timezone_resolver=TimezoneResolver(get_redis_client()),
        geocode_token_secret=settings.SECRET_KEY,
    )
    try:
        result = await service.create(
            user_id=current_user_id,
            profile_id=profile_id,
            request=body,
            idempotency_key=idempotency_key,
        )
        await db.commit()
    except BirthDataAccuracyMismatchError as exc:
        birth_data_refinement_telemetry.record_request("validation_rejected")
        return _refinement_error(exc, status.HTTP_400_BAD_REQUEST)
    except BirthDataNoChangesError as exc:
        birth_data_refinement_telemetry.record_request("validation_rejected")
        return _refinement_error(exc, status.HTTP_400_BAD_REQUEST)
    except BirthDataPlaceNotGeocodedError as exc:
        birth_data_refinement_telemetry.record_request("validation_rejected")
        return _refinement_error(exc, status.HTTP_422_UNPROCESSABLE_ENTITY)
    except BirthDataProfileNotOwnedError as exc:
        birth_data_refinement_telemetry.record_request("forbidden")
        return _refinement_error(exc, status.HTTP_403_FORBIDDEN)
    except BirthDataProfileNotFoundError as exc:
        birth_data_refinement_telemetry.record_request("not_found")
        return _refinement_error(exc, status.HTTP_404_NOT_FOUND)
    except BirthDataIdempotencyConflictError as exc:
        birth_data_refinement_telemetry.record_request("conflict")
        return _refinement_error(exc, status.HTTP_409_CONFLICT)
    except BirthDataCooldownError as exc:
        birth_data_refinement_telemetry.record_request("cooldown")
        birth_data_refinement_telemetry.record_cooldown_rejection()
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(exc.retry_after_seconds)},
            content={
                "detail": exc.message,
                "code": exc.code,
                "next_available_at": exc.next_available_at.isoformat(),
                "retry_after_seconds": exc.retry_after_seconds,
            },
        )

    revision = result.revision
    dispatched = await dispatch_birth_data_revision(db, revision_id=revision.id)
    if not dispatched:
        birth_data_refinement_telemetry.record_request("enqueue_failed")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "Birth-data refinement could not be queued",
                "code": "refinement_enqueue_unavailable",
            },
        )

    birth_data_refinement_telemetry.record_request("accepted")
    return BirthDataRefinementAcceptedResponse(
        revision_id=revision.id,
        generation_id=revision.generation_id,
        profile_id=revision.profile_id,
        changed_fields=list(revision.changed_fields),
        status=revision.status,
        next_available_at=revision.created_at + COOLDOWN_WINDOW,
    )


@router.get(
    "/{profile_id}/birth-data-refinements/{revision_id}",
    response_model=BirthDataRevisionStatusResponse,
    responses={
        401: {"model": RefinementErrorResponse},
        403: {"model": RefinementErrorResponse},
        404: {"model": RefinementErrorResponse},
    },
)
async def get_birth_data_refinement_revision(
    profile_id: UUID,
    revision_id: UUID,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> BirthDataRevisionStatusResponse | JSONResponse:
    try:
        revision = await BirthDataRevisionRepository(db).get_revision(
            user_id=current_user_id,
            profile_id=profile_id,
            revision_id=revision_id,
        )
    except BirthDataProfileNotOwnedError as exc:
        return _refinement_error(exc, status.HTTP_403_FORBIDDEN)
    except BirthDataProfileNotFoundError as exc:
        return _refinement_error(exc, status.HTTP_404_NOT_FOUND)
    generation = await BirthDataRevisionRepository(db).get_generation(revision.generation_id)
    revision_status = map_generation_status(generation.status) if generation is not None else revision.status
    return BirthDataRevisionStatusResponse(
        revision_id=revision.id,
        generation_id=revision.generation_id,
        profile_id=revision.profile_id,
        changed_fields=list(revision.changed_fields),
        status=revision_status,
        chart_id=revision.chart_id,
        report_id=revision.report_id or (generation.report_id if generation is not None else None),
        error_code=revision.error_code,
        created_at=revision.created_at,
        updated_at=revision.updated_at,
    )


def _refinement_error(exc: Exception, status_code: int) -> JSONResponse:
    detail = getattr(exc, "message", str(exc))
    code = getattr(exc, "code", type(exc).__name__)
    return JSONResponse(status_code=status_code, content={"detail": detail, "code": code})


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


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={409: {"model": RefinementErrorResponse}},
)
async def delete_profile(
    profile_id: UUID,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a profile."""
    service = ProfileService(db)
    await service.delete(profile_id=profile_id, user_id=current_user_id)
