"""Chart snapshot schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ChartSnapshotResponse(BaseModel):
    id: str
    profile_id: str
    engine_version: str
    chart_data: dict[str, object]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChartSnapshotListResponse(BaseModel):
    items: list[ChartSnapshotResponse]
