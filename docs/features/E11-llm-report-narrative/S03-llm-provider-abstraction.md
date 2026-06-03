# Story E11.S03: LLM provider abstraction and settings

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Бизнес-логика report narrative не должна зависеть напрямую от OpenAI/OpenRouter/Anthropic. Для dev/test нужен deterministic mock provider, чтобы тесты не ходили в сеть и не требовали API key.

## Что сделать

1. Создать `LLMProvider` protocol с методом `generate_structured`.
2. Реализовать `MockLLMProvider`, возвращающий валидный фиксированный `SelfNarrative`.
3. Реализовать первый real provider adapter только за abstraction boundary (`OpenAIProvider` или `OpenRouterProvider` — выбрать один для MVP).
4. Добавить config settings: `LLM_ENABLED`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`.
5. Добавить provider factory, которая в test/dev может возвращать mock.
6. Добавить errors: timeout, provider unavailable, invalid response, disabled.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `backend/app/modules/llm/__init__.py` | Новый generic LLM модуль |
| `backend/app/modules/llm/provider.py` | Protocol + provider factory |
| `backend/app/modules/llm/providers/mock.py` | Mock provider |
| `backend/app/modules/llm/providers/openrouter.py` или `openai.py` | MVP real provider |
| `backend/app/modules/llm/exceptions.py` | Provider exceptions |
| `backend/app/config.py` | LLM settings |
| `backend/.env.example` | Документировать LLM env vars |
| `backend/tests/unit/test_llm/test_provider.py` | Unit tests |

## Критерии приёмки

- [ ] Narrative service зависит от `LLMProvider`, а не от конкретного SDK.
- [ ] `LLM_PROVIDER=mock` работает без API key и без network.
- [ ] При `LLM_ENABLED=false` generation не делает real provider call и возвращает controlled disabled/fallback path.
- [ ] Timeout/retry settings читаются из config.
- [ ] Provider errors не содержат secret/API key в logs или responses.
- [ ] Unit tests используют только mock/fake provider.
