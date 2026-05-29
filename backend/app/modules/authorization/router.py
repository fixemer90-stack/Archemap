"""Authorization module — RBAC / permissions."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/authorization", tags=["authorization"])
