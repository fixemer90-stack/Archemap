"""Webhooks module — receive payment provider callbacks."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
