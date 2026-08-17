"""Regression tests for backend settings env-file resolution."""

from __future__ import annotations

from pathlib import Path

from app.config import _BACKEND_ROOT, _ENV_FILES, _REPOSITORY_ROOT, Settings


def test_settings_env_files_are_absolute_and_root_env_wins() -> None:
    """Backend cwd must not hide root-level LLM configuration."""

    assert _BACKEND_ROOT.name == "backend"
    assert _BACKEND_ROOT.parent == _REPOSITORY_ROOT
    assert _ENV_FILES == (_BACKEND_ROOT / ".env", _REPOSITORY_ROOT / ".env")
    assert all(path.is_absolute() for path in _ENV_FILES)


def test_later_root_env_overrides_backend_env_for_llm_settings(tmp_path: Path) -> None:
    """The root env file is loaded after backend/.env, so real LLM config wins."""

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
