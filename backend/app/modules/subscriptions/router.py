"""Subscriptions module."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
