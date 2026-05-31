"""Chart snapshot schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ChartSnapshotResponse(BaseModel):
    id: str
    profile_id: str
    engine_version: str
    chart_data: dict[str, Any]
    socionics: dict[str, Any] = {}
    function_strengths: dict[str, Any] = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class ChartSnapshotListResponse(BaseModel):
    items: list[ChartSnapshotResponse]
