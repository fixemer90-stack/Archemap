"""Child durable-call policy must not change another product's provider settings."""

import pytest

from app.modules.child.service import configured_child_provider
from app.modules.llm.provider import get_llm_provider


@pytest.mark.parametrize("provider_name", ["deepseek", "openrouter"])
def test_child_configured_adapter_disables_only_its_private_provider_retries(
    monkeypatch: pytest.MonkeyPatch, provider_name: str
) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "LLM_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_PROVIDER", provider_name)
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-no-network")
    monkeypatch.setattr(settings, "LLM_MAX_RETRIES", 4)
    child = configured_child_provider()
    assert child._provider.max_retries == 0  # type: ignore[attr-defined]
    other_product = get_llm_provider()
    assert other_product.max_retries == 4  # type: ignore[attr-defined]
    assert settings.LLM_MAX_RETRIES == 4
