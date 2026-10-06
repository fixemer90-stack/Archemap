"""Regression tests for backend settings env-file resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import _BACKEND_ROOT, _ENV_FILES, _REPOSITORY_ROOT, Settings


def test_settings_env_files_are_absolute_and_root_env_wins() -> None:
    """Backend cwd must not hide root-level LLM configuration."""

    assert _BACKEND_ROOT.name == "backend"
    assert _BACKEND_ROOT.parent == _REPOSITORY_ROOT
    assert _ENV_FILES == (_BACKEND_ROOT / ".env", _REPOSITORY_ROOT / ".env")
    assert all(path.is_absolute() for path in _ENV_FILES)


def test_later_root_env_overrides_backend_env_for_llm_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The root env file is loaded after backend/.env, so real LLM config wins."""

    for key in (
        "LLM_ENABLED",
        "LLM_PROVIDER",
        "LLM_MODEL",
        "LLM_API_KEY",
        "LLM_TIMEOUT_SECONDS",
        "LLM_MAX_RETRIES",
    ):
        monkeypatch.delenv(key, raising=False)

    backend_env = tmp_path / "backend.env"
    root_env = tmp_path / "root.env"
    backend_env.write_text(
        "\n".join(
            [
                "LLM_ENABLED=false",
                "LLM_PROVIDER=mock",
                "LLM_MODEL=mock-self-v1",
                "LLM_API_KEY=",
                "LLM_TIMEOUT_SECONDS=30",
                "LLM_MAX_RETRIES=2",
            ]
        ),
        encoding="utf-8",
    )
    root_env.write_text(
        "\n".join(
            [
                "LLM_ENABLED=true",
                "LLM_PROVIDER=deepseek",
                "LLM_MODEL=deepseek-v4-flash",
                "LLM_API_KEY=test-key",
                "LLM_TIMEOUT_SECONDS=180",
                "LLM_MAX_RETRIES=2",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=(backend_env, root_env))

    assert settings.LLM_ENABLED is True
    assert settings.LLM_PROVIDER == "deepseek"
    assert settings.LLM_MODEL == "deepseek-v4-flash"
    assert bool(settings.LLM_API_KEY)
    assert settings.LLM_TIMEOUT_SECONDS == 180
    assert settings.LLM_MAX_RETRIES == 2


def test_production_rejects_email_auto_verification() -> None:
    with pytest.raises(ValueError, match="AUTO_VERIFY_EMAIL"):
        Settings(APP_ENV="production", AUTO_VERIFY_EMAIL=True, _env_file=None)


@pytest.mark.parametrize(
    ("variable", "invalid_value"),
    [
        ("BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES", "0"),
        ("BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES", "-1"),
        ("BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES", "1441"),
        ("BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES", "0"),
        ("BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES", "-1"),
        ("BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES", "1441"),
        ("BIRTH_DATA_REFINEMENT_MONITOR_INTERVAL_SECONDS", "0"),
        ("BIRTH_DATA_REFINEMENT_MONITOR_INTERVAL_SECONDS", "-1"),
        ("BIRTH_DATA_REFINEMENT_MONITOR_INTERVAL_SECONDS", "3601"),
    ],
)
def test_refinement_monitor_settings_reject_out_of_bounds_env_values(
    variable: str, invalid_value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(variable, invalid_value)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert variable in str(exc_info.value)


@pytest.mark.parametrize(
    ("variable", "boundary"),
    [
        ("BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES", 1),
        ("BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES", 1440),
        ("BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES", 1),
        ("BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES", 1440),
        ("BIRTH_DATA_REFINEMENT_MONITOR_INTERVAL_SECONDS", 30),
        ("BIRTH_DATA_REFINEMENT_MONITOR_INTERVAL_SECONDS", 3600),
    ],
)
def test_refinement_monitor_settings_accept_boundary_env_values(
    variable: str, boundary: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(variable, str(boundary))

    config = Settings(_env_file=None)

    assert getattr(config, variable) == boundary
