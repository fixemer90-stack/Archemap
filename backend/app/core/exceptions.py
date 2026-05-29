"""Domain-level exception hierarchy."""

from __future__ import annotations


class ArchemapError(Exception):
    """Base exception for all Archemap domain errors."""

    def __init__(self, message: str = "", code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__


class NotFoundError(ArchemapError):
    """Requested entity does not exist."""


class ConflictError(ArchemapError):
    """Operation conflicts with current state (e.g. duplicate)."""


class AuthorizationError(ArchemapError):
    """User is not allowed to perform the action."""


class ValidationError(ArchemapError):
    """Input validation or business rule violation."""


class PaymentError(ArchemapError):
    """Payment processing failed."""
