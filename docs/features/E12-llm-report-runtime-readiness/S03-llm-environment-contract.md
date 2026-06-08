# Story E12.S03: LLM environment contract — mock and real provider

**Feature:** [LLM Report Runtime Readiness](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Для E11 narrative pipeline недостаточно просто поднять backend и worker. Команда должна однозначно понимать, в каком из трёх режимов работает narrative layer:

1. `disabled` — LLM слой выключен и pipeline деградирует в deterministic fallback.
2. `mock` — pipeline проходит без network LLM calls, но narrative quality не является продуктовой.
3. `real provider` — worker реально вызывает внешний LLM provider и итог зависит от его ответа.

Без этого различия невозможно понять, что именно было проверено: сам async pipeline, fallback path или реальное качество narrative generation.

## Что было проверено

Проверены фактические источники истины:

- `backend/app/config.py`
- `backend/app/modules/llm/provider.py`
- `backend/app/modules/llm/providers/mock.py`
- `backend/app/modules/llm/providers/openrouter.py`
- `backend/app/modules/llm/exceptions.py`
- `backend/app/modules/report_narratives/service.py`
- `backend/app/modules/report_narratives/tasks.py`
- `backend/workers/tasks/reports.py`
- `docker-compose.yml`

## Фактический runtime contract из кода

### Базовые env-переменные

В `backend/app/config.py` сейчас определены:

- `LLM_ENABLED: bool = False`
- `LLM_PROVIDER: str = "mock"`
- `LLM_MODEL: str = "mock-self-v1"`
- `LLM_API_KEY: str = ""`
- `LLM_TIMEOUT_SECONDS: int = 30`
- `LLM_MAX_RETRIES: int = 2`

В compose эти переменные теперь прокинуты и в `backend`, и в `worker`, поэтому narrative runtime contract должен читаться обоими процессами одинаково.

### Какие provider values реально поддерживаются

По `backend/app/modules/llm/provider.py` фактически поддерживаются только:

- `mock`
- `openrouter`

Любое другое значение `LLM_PROVIDER` приводит к `LLMProviderUnavailableError("Unsupported LLM provider: ...")`.

То есть в документации нельзя писать абстрактное `LLM_PROVIDER=<real>` без уточнения: в текущем коде реальный provider = только `openrouter`.

## Три режима запуска

### 1. Disabled path

Конфиг:

```env
LLM_ENABLED=false
```

Что происходит:

- `get_llm_provider()` возвращает `DisabledLLMProvider`
- при генерации narrative provider выбрасывает `LLMDisabledError`
- `ReportNarrativeService` не переводит report в terminal failure
- вместо этого строится deterministic fallback через `build_deterministic_self_fallback(...)`
- итоговый `report.status` становится `ready`
- narrative сохраняется как `ready`, но с fallback payload

Практический смысл:

- pipeline не проверяет внешний LLM вообще
- UI получает narrative-ready результат, но это controlled degraded mode
- этот путь нужен для intentional disable/degraded launch path, а не для проверки реального narrative quality

### 2. Mock path

Конфиг:

```env
LLM_ENABLED=true
LLM_PROVIDER=mock
LLM_MODEL=mock-self-v1
LLM_API_KEY=
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

Что происходит:

- `get_llm_provider()` возвращает `MockLLMProvider`
- provider не делает network calls
- `MockLLMProvider` возвращает стабильный schema-valid JSON
- narrative доходит до `ready` как обычный успешный path

Практический смысл:

- это лучший режим для smoke/test pipeline
- он проверяет enqueue → worker → persistence → API/frontend path
- он НЕ проверяет качество prompt/provider/model
- он НЕ доказывает, что внешний LLM доступен и отвечает корректно

### 3. Real provider path

Конфиг:

```env
LLM_ENABLED=true
LLM_PROVIDER=openrouter
LLM_MODEL=<реальная openrouter model id>
LLM_API_KEY=<openrouter api key>
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

Что происходит:

- `get_llm_provider()` создаёт `OpenRouterProvider`
- worker отправляет HTTP POST на:
  `https://openrouter.ai/api/v1/chat/completions`
- в запрос уходят:
  - system prompt
  - `narrative_input.model_dump_json(indent=2)`
  - `response_format={"type": "json_object"}`
- ответ должен содержать JSON, валидный для `SelfNarrative`

Практический смысл:

- только этот режим является продуктовой проверкой narrative generation
- именно здесь проверяются внешний provider, API key, модель, timeout и реальная schema fidelity

## Минимальные env-примеры

### Local `.env` для mock smoke path

```env
LLM_ENABLED=true
LLM_PROVIDER=mock
LLM_MODEL=mock-self-v1
LLM_API_KEY=
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

### Local `.env` для real OpenRouter path

```env
LLM_ENABLED=true
LLM_PROVIDER=openrouter
LLM_MODEL=openai/gpt-4.1-mini
LLM_API_KEY=or-v1-...
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

Примечание:

- значение `LLM_MODEL` для real path должно быть реальным OpenRouter model id
- дефолт `mock-self-v1` подходит только для mock provider и не должен считаться production-like model config

### Compose env pattern

В `docker-compose.yml` для `backend` и `worker` используется один и тот же override pattern:

```yaml
LLM_ENABLED: ${LLM_ENABLED:-false}
LLM_PROVIDER: ${LLM_PROVIDER:-mock}
LLM_MODEL: ${LLM_MODEL:-mock-self-v1}
LLM_API_KEY: ${LLM_API_KEY:-}
LLM_TIMEOUT_SECONDS: ${LLM_TIMEOUT_SECONDS:-30}
LLM_MAX_RETRIES: ${LLM_MAX_RETRIES:-2}
```

Это означает:

- без внешнего override stack поднимется в safe default режиме
- по умолчанию narrative layer effectively disabled, потому что `LLM_ENABLED=false`
- чтобы получить mock smoke path, недостаточно одного `LLM_PROVIDER=mock` — нужно именно `LLM_ENABLED=true`

## Диагностика ошибок конфигурации и runtime

### Missing API key

Условие:

```env
LLM_ENABLED=true
LLM_PROVIDER=openrouter
LLM_API_KEY=
```

Фактическое поведение:

- `get_llm_provider()` выбрасывает `LLMProviderUnavailableError`
- текст ошибки:
  `LLM API key is required for openrouter provider`
- ошибка относится к retryable provider-unavailable class
- Celery будет ретраить до `LLM_MAX_RETRIES`
- после исчерпания retry вызывается `finalize_narrative_task_failure(...)`
- итог: `report.status = narrative_failed`

### Unsupported provider

Условие:

```env
LLM_ENABLED=true
LLM_PROVIDER=anything-else
```

Фактическое поведение:

- `get_llm_provider()` выбрасывает `LLMProviderUnavailableError`
- текст ошибки:
  `Unsupported LLM provider: anything-else`
- path аналогичен missing API key: retry → terminal `narrative_failed`

### Timeout

Условие:

- provider отвечает слишком долго
- `httpx.AsyncClient(timeout=self.timeout_seconds)` превышает `LLM_TIMEOUT_SECONDS`

Фактическое поведение:

- `OpenRouterProvider` выбрасывает `LLMTimeoutError(code="llm_timeout")`
- task считает такую ошибку retryable
- Celery делает retry до `LLM_MAX_RETRIES`
- после исчерпания retry narrative финализируется как `narrative_failed`

### Provider unavailable / bad HTTP status / network failure

Фактическое поведение:

- HTTP status error -> `LLMProviderUnavailableError("LLM provider request failed with status ...")`
- другой `httpx.HTTPError` -> `LLMProviderUnavailableError("LLM provider request failed")`
- обе ошибки считаются retryable
- после retry exhaustion итоговый report/narrative получают `narrative_failed`

### Invalid JSON / schema mismatch

Хотя это не чисто env-ошибка, это важный runtime diagnostic case для real provider:

- provider вернул не-JSON -> `LLMInvalidResponseError`
- provider вернул JSON не по `SelfNarrative` schema -> `LLMInvalidResponseError`
- такой path НЕ относится к provider-unavailable retry class
- service переводит narrative/report в `narrative_failed` сразу

## Как отличить disabled / mock / real на практике

### Disabled

Признаки:

- `LLM_ENABLED=false`
- narrative завершается `ready`, но через deterministic fallback
- это не terminal failure и не real LLM success

### Mock

Признаки:

- `LLM_ENABLED=true`
- `LLM_PROVIDER=mock`
- model/provider в narrative row будут mock-oriented
- network provider не вызывается
- narrative content детерминирован и стабилен между запусками

### Real OpenRouter

Признаки:

- `LLM_ENABLED=true`
- `LLM_PROVIDER=openrouter`
- `LLM_MODEL` задан как реальный model id
- worker делает внешний HTTP вызов к OpenRouter
- `report_narratives.model_provider` сохраняется как `openrouter`
- `report_narratives.model_name` сохраняется как выбранная реальная модель

Ключевая граница:

- `mock ready` = pipeline smoke success
- `real ready` = продуктовая narrative generation success
- `disabled ready` = controlled fallback success

Эти три состояния нельзя считать эквивалентными.

## Что должна понимать команда без чтения исходников

1. `LLM_PROVIDER=mock` сам по себе не включает narrative layer; нужен `LLM_ENABLED=true`.
2. Реальный provider в текущем коде только один: `openrouter`.
3. Отсутствующий API key и unsupported provider не дают "тихий mock" — они ведут к retry и затем `narrative_failed`.
4. `LLM_ENABLED=false` не даёт `narrative_failed`; он даёт controlled deterministic fallback.
5. Проверка на mock не равна продуктовой проверке narrative quality.

## Ограничения этой story

S03 фиксирует env/runtime contract, но не закрывает:

- bucket/bootstrap для PDF storage — это S04
- полный runbook с командами и smoke сценарием — это S05
- triage checklist для launch readiness — это S06

## Затронутые файлы

| Файл | Действие |
|---|---|
| `backend/app/config.py` | Сверен фактический env contract |
| `backend/app/modules/llm/provider.py` | Зафиксированы реальные supported providers и provider resolution rules |
| `backend/app/modules/llm/providers/mock.py` | Подтверждён deterministic non-network mock path |
| `backend/app/modules/llm/providers/openrouter.py` | Подтверждён реальный OpenRouter HTTP path и error mapping |
| `backend/app/modules/report_narratives/service.py` | Зафиксировано различие fallback/failed paths |
| `docs/features/E12-llm-report-runtime-readiness/S03-llm-environment-contract.md` | Описан mock/real env contract |

## Проверка

В этой story фактически проверено чтением кода и config contract:

- defaults из `Settings`
- mapping `LLM_PROVIDER -> provider implementation`
- mandatory API key rule для `openrouter`
- timeout/provider-unavailable/error mapping
- disabled path -> deterministic fallback -> `ready`
- unsupported/misconfigured real provider path -> retry -> `narrative_failed`

Ограничение текущей среды:

- реальный OpenRouter call не выполнялся, потому что в текущей сессии не задан валидный provider key и цель story — зафиксировать contract, а не прогонять боевой внешний API

## Критерии приёмки

- [x] Разница между disabled/mock/real path зафиксирована без двусмысленности.
- [x] Есть минимальный пример env для mock и real provider.
- [x] Документация объясняет, как понять, что narrative пришёл именно от real provider, а не от mock/fallback.
- [x] Ошибки конфигурации provider можно диагностировать по документации, не читая исходники.
