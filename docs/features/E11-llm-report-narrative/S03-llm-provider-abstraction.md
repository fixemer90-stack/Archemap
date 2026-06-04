# Story E11.S03: LLM provider abstraction and settings

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ✅ Готово

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
| `backend/app/modules/llm/providers/openrouter.py` | MVP real provider |
| `backend/app/modules/llm/exceptions.py` | Provider exceptions |
| `backend/app/config.py` | LLM settings |
| `backend/.env.example` | Документированы LLM env vars |
| `backend/tests/unit/test_llm/test_provider.py` | Unit tests |

## Критерии приёмки

- [x] Narrative service зависит от `LLMProvider`, а не от конкретного SDK.
- [x] `LLM_PROVIDER=mock` работает без API key и без network.
- [x] При `LLM_ENABLED=false` generation не делает real provider call и возвращает controlled disabled/fallback path.
- [x] Timeout/retry settings читаются из config.
- [x] Provider errors не содержат secret/API key в logs или responses.
- [x] Unit tests используют только mock/fake provider.

## Реализация

Добавлены:

- `backend/app/modules/llm/provider.py` — `LLMProvider` protocol, `DisabledLLMProvider`, `get_llm_provider(...)`
- `backend/app/modules/llm/providers/mock.py` — deterministic `MockLLMProvider`
- `backend/app/modules/llm/providers/openrouter.py` — первый real adapter за abstraction boundary
- `backend/app/modules/llm/exceptions.py` — `LLMDisabledError`, `LLMTimeoutError`, `LLMProviderUnavailableError`, `LLMInvalidResponseError`
- `backend/app/config.py` — LLM settings
- `backend/.env.example` — пример env-переменных для narrative layer
- `backend/tests/unit/test_llm/test_provider.py` — unit tests для mock/factory/settings

Принятые решения:

- Для MVP выбран `OpenRouterProvider`, потому что его можно поднять через уже имеющийся `httpx`, без отдельного SDK.
- Фабрика возвращает `DisabledLLMProvider`, если `LLM_ENABLED=false`, чтобы верхний слой получал контролируемую ошибку `llm_disabled` и не пытался сходить в сеть.
- `MockLLMProvider` отдаёт фиксированный, schema-valid `SelfNarrative`, поэтому тесты deterministic и не требуют `LLM_API_KEY`.
- Реальный provider не парсит свободный Markdown: он ожидает JSON content и валидирует ответ через переданную Pydantic schema.
- Ошибки real provider не включают значение `LLM_API_KEY`; в сообщения попадает только безопасный технический контекст (`status`, timeout, invalid response).

## Верификация

Проверено в backend container:

```bash
cd /app
python -m pytest tests/unit/test_llm/test_provider.py -q
python -m ruff check app/modules/llm tests/unit/test_llm app/config.py
python -m ruff format --check app/modules/llm tests/unit/test_llm app/config.py
python -m mypy app/modules/llm tests/unit/test_llm app/config.py
python -m pytest tests/unit/test_llm tests/unit/test_report_narratives -q
```
