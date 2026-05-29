"""Payments module — Stripe & YooKassa payment orchestration."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/payments", tags=["payments"])
