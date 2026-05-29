"""Billing module — invoices, billing cycles."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/billing", tags=["billing"])
