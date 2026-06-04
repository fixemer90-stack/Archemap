"""Stable hashing for NarrativeInput payloads."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.modules.report_narratives.schemas import NarrativeInput


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        canonical_items = [_canonicalize(item) for item in value]
        return sorted(canonical_items, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    return value


def compute_input_hash(narrative_input: NarrativeInput) -> str:
    """Compute a stable SHA256 hash for semantic NarrativeInput content."""
    payload = narrative_input.model_dump(mode="json")
    normalized = _canonicalize(payload)
    serialized = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
