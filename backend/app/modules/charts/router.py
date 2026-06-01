"""Chart endpoints — compute and retrieve chart snapshots."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.charts.schemas import ChartSnapshotListResponse, ChartSnapshotResponse
from app.modules.charts.service import ChartService

router = APIRouter(prefix="/profiles/{profile_id}/chart", tags=["charts"])


@router.post("", response_model=ChartSnapshotResponse, status_code=status.HTTP_201_CREATED)
async def compute_chart(
    profile_id: UUID,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    force: bool = Query(False, description="Force recompute even if cached"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Compute a natal chart for a profile. Returns cached snapshot if available."""
    service = ChartService(db)
    snapshot = await service.get_or_compute(
        profile_id=profile_id,
        user_id=current_user_id,
        force_recompute=force,
    )
    return ChartSnapshotResponse(
        id=str(snapshot.id),
        profile_id=str(snapshot.profile_id),
        engine_version=snapshot.engine_version,
        chart_data=snapshot.chart_data,
        socionics=snapshot.socionics,
        function_strengths=snapshot.function_strengths,
        created_at=snapshot.created_at,
    )


@router.get("", response_model=ChartSnapshotListResponse)
async def list_snapshots(
    profile_id: UUID,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all chart snapshots for a profile."""
    service = ChartService(db)
    snapshots = await service.list_by_profile(profile_id=profile_id, user_id=current_user_id)
    return ChartSnapshotListResponse(
        items=[
            ChartSnapshotResponse(
                id=str(s.id),
                profile_id=str(s.profile_id),
                engine_version=s.engine_version,
                chart_data=s.chart_data,
                socionics=s.socionics,
                function_strengths=s.function_strengths,
                created_at=s.created_at,
            )
            for s in snapshots
        ]
    )


@router.get("/{snapshot_id}", response_model=ChartSnapshotResponse)
async def get_snapshot(
    profile_id: UUID,
    snapshot_id: UUID,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a specific chart snapshot by ID."""
    service = ChartService(db)
    snapshot = await service.get_by_id(
        snapshot_id=snapshot_id,
        user_id=current_user_id,
        profile_id=profile_id,
    )
    return ChartSnapshotResponse(
        id=str(snapshot.id),
        profile_id=str(snapshot.profile_id),
        engine_version=snapshot.engine_version,
        chart_data=snapshot.chart_data,
        socionics=snapshot.socionics,
        function_strengths=snapshot.function_strengths,
        created_at=snapshot.created_at,
    )
