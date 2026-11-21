"""Business integrations are opt-in and never use ambient provider keys."""

from __future__ import annotations

from app.config import Settings


def test_business_integrations_default_to_disabled() -> None:
    required = {
        "BUSINESS_MONITORING_ENABLED",
        "BUSINESS_ALERTS_ENABLED",
        "YANDEX_METRICA_EXPORT_ENABLED",
    }
    assert required <= set(Settings.model_fields)
    settings = Settings(_env_file=None)
    assert settings.BUSINESS_MONITORING_ENABLED is False
    assert settings.BUSINESS_ALERTS_ENABLED is False
    assert settings.YANDEX_METRICA_EXPORT_ENABLED is False
