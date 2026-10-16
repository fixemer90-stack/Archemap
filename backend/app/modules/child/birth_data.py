"""Canonical hashing for persisted child birth-data corrections."""

from __future__ import annotations

import hashlib
import json
from datetime import date, time


def child_birth_data_hash(
    *,
    birth_date: date,
    birth_time: time | None,
    birth_time_confidence: str,
    birth_place: str,
    latitude: float,
    longitude: float,
    timezone: str,
) -> str:
    """Hash the complete persisted birth-data snapshot using canonical JSON."""
    if birth_time is not None and birth_time.tzinfo is not None:
        raise ValueError("Birth time must be offset-naive, not offset-aware")
    payload = {
        "birth_date": birth_date.isoformat(),
        "birth_place": birth_place,
        "birth_time": birth_time.isoformat() if birth_time is not None else None,
        "birth_time_confidence": birth_time_confidence,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()
