"""Reconciliation module — payment vs subscription consistency checks."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])
