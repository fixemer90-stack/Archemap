"""Validation errors and recovery actions for report narratives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

NarrativeRecoveryAction = Literal["repair", "fallback", "narrative_failed"]


@dataclass(slots=True, frozen=True)
class NarrativeValidationError:
    """Deterministic validation failure for a narrative payload."""

    code: str
    message: str
    location: str
    recoverable: bool = True


class NarrativeValidationAggregateError(Exception):
    """Raised when a narrative payload fails deterministic validation."""

    def __init__(self, errors: list[NarrativeValidationError]) -> None:
        self.errors = errors
        super().__init__("; ".join(error.message for error in errors))
