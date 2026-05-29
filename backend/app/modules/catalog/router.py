"""Catalog module — plans, features, pricing."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/catalog", tags=["catalog"])
