from __future__ import annotations

import pytest

from app.modules.child.narrative import DisabledChildSegmentProvider, MockChildSegmentProvider
from app.modules.child.service import configured_child_provider


@pytest.mark.parametrize("environment", ["development", "staging"])
def test_enabled_nonproduction_mock_uses_bounded_child_provider(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    monkeypatch.setattr("app.modules.child.service.settings.APP_ENV", environment)
    monkeypatch.setattr("app.modules.child.service.settings.LLM_ENABLED", True)
    monkeypatch.setattr("app.modules.child.service.settings.LLM_PROVIDER", "mock")

    def forbid_external_factory(*args: object, **kwargs: object) -> object:
        raise AssertionError("Native mock must not construct an external provider")

    monkeypatch.setattr("app.modules.child.service.get_llm_provider", forbid_external_factory)
    assert isinstance(configured_child_provider(), MockChildSegmentProvider)


@pytest.mark.parametrize("environment", ["development", "staging", "production"])
def test_disabled_mock_remains_zero_work(monkeypatch: pytest.MonkeyPatch, environment: str) -> None:
    monkeypatch.setattr("app.modules.child.service.settings.APP_ENV", environment)
    monkeypatch.setattr("app.modules.child.service.settings.LLM_ENABLED", False)
    monkeypatch.setattr("app.modules.child.service.settings.LLM_PROVIDER", "mock")
    assert isinstance(configured_child_provider(), DisabledChildSegmentProvider)


def test_production_mock_cannot_publish_synthetic_child_prose(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.child.service.settings.APP_ENV", "production")
    monkeypatch.setattr("app.modules.child.service.settings.LLM_ENABLED", True)
    monkeypatch.setattr("app.modules.child.service.settings.LLM_PROVIDER", "mock")
    assert isinstance(configured_child_provider(), DisabledChildSegmentProvider)
