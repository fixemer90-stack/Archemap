from app.modules.llm.providers.deepseek import DeepSeekProvider
from app.modules.llm.providers.mock import MockLLMProvider
from app.modules.llm.providers.openrouter import OpenRouterProvider


def test_runtime_providers_explicitly_advertise_staged_pipeline_support() -> None:
    deepseek = DeepSeekProvider(api_key="test", model="deepseek-v4-flash", timeout_seconds=30, max_retries=1)
    openrouter = OpenRouterProvider(api_key="test", model="openai/gpt-4.1-mini", timeout_seconds=30, max_retries=1)
    mock = MockLLMProvider()

    assert getattr(deepseek, "supports_staged_pipeline", False) is True
    assert getattr(openrouter, "supports_staged_pipeline", False) is True
    assert getattr(mock, "supports_staged_pipeline", False) is True
