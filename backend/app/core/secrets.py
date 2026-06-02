"""Secrets validation — checks for insecure defaults and missing secrets."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

# Secrets that must not use default values in production
INSECURE_DEFAULTS: dict[str, str] = {
    "SECRET_KEY": "change-me",
    "S3_ACCESS_KEY_ID": "minioadmin",
    "S3_SECRET_ACCESS_KEY": "minioadmin",
    "DATABASE_URL": "postgresql+asyncpg://archemap:archemap@localhost:5432/archemap",
}

# Secrets that must be set in production
REQUIRED_IN_PRODUCTION: list[str] = [
    "SECRET_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "FRONTEND_URL",
]

# Secrets that should be rotated periodically
ROTATION_SCHEDULE: dict[str, str] = {
    "SECRET_KEY": "90 days",
    "DATABASE_URL": "On password change",
    "YANDEX_CLIENT_SECRET": "On Yandex Console rotation",
    "SMTP_PASSWORD": "On SMTP password change",
    "S3_SECRET_ACCESS_KEY": "On key rotation",
}


def validate_secrets(env: str) -> list[str]:
    """Validate secrets for the current environment.

    Returns list of warnings/errors. Empty list = all OK.
    """
    from app.config import settings

    errors: list[str] = []
    warnings: list[str] = []

    if env == "production":
        # Check required secrets
        for key in REQUIRED_IN_PRODUCTION:
            value = getattr(settings, key, None)
            if not value:
                errors.append(f"Missing required secret: {key}")

        # Check for insecure defaults
        for key, default in INSECURE_DEFAULTS.items():
            value = getattr(settings, key, None)
            if value == default:
                errors.append(f"Insecure default for {key}: must not be '{default}'")

        # Check debug mode
        if settings.APP_DEBUG:
            errors.append("APP_DEBUG must be False in production")

    elif env == "staging":
        # Staging: warn on insecure defaults but don't fail
        for key, default in INSECURE_DEFAULTS.items():
            value = getattr(settings, key, None)
            if value == default:
                warnings.append(f"Staging: {key} uses default value")

    # Log results
    for error in errors:
        logger.error("secret_validation_error", error=error)
    for warning in warnings:
        logger.warning("secret_validation_warning", warning=warning)

    return errors


def get_secret_status() -> dict[str, bool]:
    """Get status of all secrets (set or not)."""
    from app.config import settings

    secrets = [
        "SECRET_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        "YANDEX_CLIENT_ID",
        "YANDEX_CLIENT_SECRET",
        "SMTP_PASSWORD",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "SENTRY_DSN",
    ]

    return {key: bool(getattr(settings, key, None)) for key in secrets}
