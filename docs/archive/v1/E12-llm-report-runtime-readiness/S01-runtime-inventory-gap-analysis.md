# Story E12.S01: Runtime inventory and gap analysis

**Feature:** [LLM Report Runtime Readiness](Archemap/docs/features/v1/E12-llm-report-runtime-readiness/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Прежде чем менять compose/runbook, нужно зафиксировать текущее состояние запуска E11 и список конкретных блокеров. Иначе E12 расползётся в неявные инфраструктурные правки.

S01 отвечает на один главный вопрос:

> Что уже реализовано в E11 как код, и чего всё ещё не хватает, чтобы narrative report реально запускался end-to-end?

## Что было проверено

Проверены текущие runtime-источники истины:

- `docker-compose.yml`
- `backend/app/config.py`
- `backend/app/modules/llm/provider.py`
- `backend/workers/tasks/reports.py`
- `backend/app/modules/report_narratives/service.py`
- `backend/app/modules/reports/tasks.py`
- `backend/app/modules/reports/storage.py`

## Итоговый runtime inventory для E11 launch path

### Обязательные сервисы

Для реального запуска narrative report нужны:

1. `postgres`
   - хранит users, profiles, reports, `report_narratives`
2. `redis`
   - нужен как Celery broker/result backend
3. `backend`
   - принимает `POST /api/v1/reports/generate`
   - создаёт deterministic report
   - ставит narrative/PDF задачи в очередь
4. `frontend`
   - показывает polling/status/fallback flow
5. `celery worker`
   - исполняет `reports.generate_report_narrative`
   - исполняет `reports.generate_pdf`
6. `object storage` (`minio` / S3-compatible)
   - нужен для PDF upload и signed URL
7. `LLM provider`
   - либо `mock` для smoke pipeline
   - либо real provider для настоящего LLM report

### Обязательные env/runtime настройки

Из `backend/app/config.py` следует минимальный narrative runtime contract:

- `LLM_ENABLED`
- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_API_KEY`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `S3_ENDPOINT_URL`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `S3_BUCKET_NAME`
- `DATABASE_URL`
- `REDIS_URL`

## Что уже code-ready в E11

На уровне кода narrative pipeline уже реализован:

1. Generate endpoint существует
   - `POST /api/v1/reports/generate`
2. Для `product=self` backend enqueue-ит narrative task
3. Есть provider factory и режимы disabled/mock/openrouter
4. Есть Celery task `reports.generate_report_narrative`
5. Есть narrative statuses:
   - `generating_narrative`
   - `ready`
   - `narrative_failed`
   - `deterministic_ready`
6. Есть regenerate endpoint
7. Есть frontend polling/fallback contract
8. Есть PDF task, использующий уже сохранённый narrative JSON

Иными словами: E11 как feature-код не является главным блокером.

## Что сейчас фактически мешает реальному запуску

### Gap 1. В `docker-compose.yml` нет worker service

Текущее compose-окружение поднимает только:

- `postgres`
- `redis`
- `minio`
- `backend`
- `frontend`

Отдельного `worker` service нет.

Практическое следствие:
- backend может вызвать `generate_report_narrative.delay(...)`
- задача уйдёт в Redis
- но никто её не исполнит
- report застрянет в `generating_narrative`, пока frontend не уйдёт в timeout/fallback

Это главный runtime blocker.

### Gap 2. LLM выключен по умолчанию

В `backend/app/config.py`:

- `LLM_ENABLED = False`
- `LLM_PROVIDER = "mock"`
- `LLM_MODEL = "mock-self-v1"`

В `backend/app/modules/llm/provider.py` это означает:
- если `LLM_ENABLED=false`, используется `DisabledLLMProvider`
- реальный narrative call не делается

Практическое следствие:
- даже при поднятом worker без включения LLM нельзя получить реальный provider-backed narrative
- возможен только degraded path через disabled/fallback логику

### Gap 3. Real-provider env contract не оформлен как launch contract

В коде сейчас поддержан только понятный real provider path через `openrouter`, но:

- нет отдельного launch doc с required env
- нет runbook, чем mock отличается от real provider path
- нет operational checklist, по которому QA/разработчик может понять, что narrative пришёл реально от LLM, а не от mock/fallback

### Gap 4. Storage bootstrap для PDF не закреплён

`backend/app/modules/reports/storage.py` содержит `ensure_bucket()`, но в фактическом PDF path:

- `backend/app/modules/reports/tasks.py`
- создаётся `S3Storage()`
- вызывается `upload(...)`
- bucket existence перед upload явно не гарантируется

Практическое следствие:
- narrative может успешно сгенерироваться
- но PDF deliverable может упасть отдельно из-за отсутствующего bucket или плохого storage bootstrap

### Gap 5. Нет единого runbook и smoke-пути

Сейчас знания о запуске размазаны по:
- исходникам backend
- compose
- E11 feature/API/workflow docs

Но нет одного документа, который отвечает:
- что поднять;
- какие env выставить;
- где смотреть worker logs;
- как прогнать generate → polling → ready;
- как проверить regenerate;
- как проверить PDF.

## Разделение сценариев: mock vs real

### Smoke path через mock provider

Цель:
- проверить pipeline и orchestration, а не качество текста

Минимальные условия:
- `LLM_ENABLED=true`
- `LLM_PROVIDER=mock`
- worker поднят
- Redis доступен

Что подтверждает этот сценарий:
- enqueue narrative task работает
- worker исполняет задачу
- report выходит в `ready`
- frontend polling/status flow работает

Что он НЕ подтверждает:
- реальную сетевую интеграцию с LLM provider
- качество реального narrative текста
- поведение timeout/provider errors реального API

### Real narrative path

Цель:
- получить настоящий LLM Self-report

Минимальные условия:
- `LLM_ENABLED=true`
- `LLM_PROVIDER=openrouter`
- `LLM_MODEL=<real model>`
- `LLM_API_KEY=<valid key>`
- worker поднят
- provider доступен из backend/worker runtime

Что подтверждает этот сценарий:
- вся E11 цепочка реально работает с настоящим LLM
- ready narrative приходит не из mock/fallback path

## Минимальный gap list для следующих stories

### Для S02

Нужно закрыть orchestration gap:
- добавить/описать отдельный Celery worker runtime
- зафиксировать narrative-ready compose stack

### Для S03

Нужно закрыть provider/env gap:
- описать disabled/mock/real режимы
- зафиксировать required env
- дать понятные env examples

### Для S04

Нужно закрыть storage gap:
- определить bucket bootstrap contract
- отделить narrative success от PDF success

### Для S05

Нужно закрыть operational usability gap:
- написать пошаговый runbook
- добавить команды запуска, логов и smoke checks

### Для S06

Нужно закрыть triage gap:
- symptoms -> causes -> checks
- финальный checklist «готовы запускать LLM-report»

## Вывод S01

Текущее состояние проекта такое:

- E11 как код уже реализован;
- runtime для реального запуска narrative report — ещё нет в завершённом виде;
- главный недостающий слой — не feature-логика, а orchestration/configuration/operations.

То есть утверждение «достаточно просто включить E11» неверно.

Корректная формулировка:

> Чтобы реально запускать LLM-report, нужно завершить E12: worker runtime, env contract, storage bootstrap, runbook и readiness checklist.

## Критерии приёмки

- [x] Есть явный список обязательных сервисов и env-настроек для E11 runtime.
- [x] Письменно отделены code-ready части E11 от runtime-missing частей.
- [x] Зафиксирован минимальный gap list, закрываемый stories S02-S06.
- [x] После чтения story понятно, почему «просто включить E11» недостаточно.
