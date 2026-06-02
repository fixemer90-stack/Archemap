"""Application settings loaded from environment variables / .env file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SECRET_KEY: str = "change-me"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://archemap:archemap@localhost:5432/archemap"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # ── Redis ─────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300

    # ── Auth / VK ID ──────────────────────────────────────────────────
    VK_CLIENT_ID: str = ""
    VK_CLIENT_SECRET: str = ""
    VK_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/vk/callback"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Stripe ────────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # ── YooKassa ──────────────────────────────────────────────────────
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    YOOKASSA_WEBHOOK_SECRET: str = ""

    # ── OAuth / Yandex ID ──────────────────────────────────────────────
    YANDEX_CLIENT_ID: str = ""
    YANDEX_CLIENT_SECRET: str = ""
    YANDEX_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/oauth/yandex/callback"
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Email / SMTP ───────────────────────────────────────────────────
    EMAIL_PROVIDER: str = "console"  # "console" or "smtp"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = "noreply@archemap.com"
    SMTP_FROM_NAME: str = "Archemap"

    # ── Celery ────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Sentry ────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # ── Object Storage ────────────────────────────────────────────────
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "archemap"
    S3_REGION: str = "us-east-1"

    # ── Rate Limiting ────────────────────────────────────────────────
    RATE_LIMIT_GLOBAL_PER_MINUTE: int = 100
    RATE_LIMIT_ANONYMOUS_PER_MINUTE: int = 20
    RATE_LIMIT_LOGIN_MAX_ATTEMPTS: int = 5
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 900  # 15 minutes
    RATE_LIMIT_GEOCODE_PER_MINUTE: int = 30

    # ── Logging ───────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"


settings = Settings()

# ── Production guards ────────────────────────────────────────────────
if settings.APP_ENV == "production":
    from app.core.secrets import validate_secrets

    errors = validate_secrets("production")
    if errors:
        raise RuntimeError(f"Secrets validation failed: {'; '.join(errors)}")
elif settings.APP_ENV == "staging":
    from app.core.secrets import validate_secrets

    validate_secrets("staging")
