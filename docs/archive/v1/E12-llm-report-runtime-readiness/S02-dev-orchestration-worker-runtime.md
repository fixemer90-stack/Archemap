# Story E12.S02: Dev orchestration — compose/worker runtime contract

**Feature:** [LLM Report Runtime Readiness](Archemap/docs/features/v1/E12-llm-report-runtime-readiness/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

E11 narrative generation идёт только через Celery tasks. В текущем коде backend enqueue'ит как минимум два асинхронных job path:

- `reports.generate_pdf`
- `reports.generate_report_narrative`

Обе задачи зарегистрированы в `backend/workers/tasks/reports.py`, а narrative flow из `POST /api/v1/reports/generate` и `POST /api/v1/reports/{id}/narrative/regenerate` отправляется через `.delay(...)` прямо из `backend/app/modules/reports/router.py`.

Значит, без отдельного worker runtime локальный/dev stack не является narrative-ready: backend может принять запрос и перевести report в `generating_narrative`, но саму задачу выполнять будет некому.

## Что было проверено

Проверены текущие runtime-источники истины:

- `docker-compose.yml`
- `backend/workers/celery_app.py`
- `backend/workers/tasks/reports.py`
- `backend/app/modules/reports/router.py`
- `backend/app/config.py`
- `backend/Dockerfile`

По результату проверки зафиксировано:

1. `workers.celery_app` уже существует и использует:
   - `CELERY_BROKER_URL`
   - `CELERY_RESULT_BACKEND`
2. Worker autodiscover'ит `workers.tasks` и уже содержит narrative/PDF tasks.
3. Backend уже enqueue'ит narrative/PDF tasks в Celery.
4. В `docker-compose.yml` до этой story не было отдельного `worker` service, поэтому E11 runtime contract был неполным.
5. Backend image уже подходит для worker runtime, потому что Celery app и task-модули находятся в том же backend-коде и собираются тем же `backend/Dockerfile`.

## Что изменено

### 1. В `docker-compose.yml` добавлен отдельный `worker` service

Новый service:

- использует тот же build context, что и backend (`./backend`)
- использует тот же код (`./backend:/app`)
- получает те же базовые runtime env, что нужны для БД, Redis, S3 и LLM narrative layer
- зависит от `postgres`, `redis`, `minio`
- запускается командой:

```bash
celery -A workers.celery_app.app worker --loglevel=INFO
```

### 2. В backend compose env добавлены LLM runtime variables

Чтобы backend и worker читали один и тот же narrative runtime contract, в compose зафиксированы переменные:

- `LLM_ENABLED`
- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_API_KEY`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`

На этом этапе это именно orchestration contract: значения можно переопределять через окружение, а полный mock/real provider contract будет детализирован в S03.

## Итоговый dev runtime contract

Минимальный narrative-ready stack теперь выглядит так:

- `postgres` — persistence
- `redis` — app cache + Celery broker/result backend
- `minio` — object storage для PDF
- `backend` — API, deterministic report generation, enqueue задач
- `worker` — исполнение `reports.generate_pdf` и `reports.generate_report_narrative`
- `frontend` — UI/polling path

## Команды запуска

Основная команда narrative-ready стека:

```bash
docker compose up -d postgres redis minio backend frontend worker
```

Если окружение всё ещё использует legacy wrapper, эквивалентная команда:

```bash
docker-compose up -d postgres redis minio backend frontend worker
```

## Где смотреть readiness и логи

### Backend readiness

Backend считается поднятым, когда проходит health endpoint из compose healthcheck:

```bash
curl -f http://localhost:8000/api/v1/health
```

### Worker readiness

Worker считается поднятым, когда контейнер `worker` успешно стартует с `celery -A workers.celery_app.app worker --loglevel=INFO` и не завершается сразу после запуска.

Практические команды наблюдения:

```bash
docker compose logs -f backend worker
```

или legacy:

```bash
docker-compose logs -f backend worker
```

### Признак, что narrative tasks реально исполняются

Проверяемый факт не в том, что backend вернул 200, а в том, что после generate/regenerate есть полный async path:

1. backend enqueue'ит `generate_report_narrative.delay(...)`;
2. report получает статус `generating_narrative`;
3. worker исполняет task `reports.generate_report_narrative`;
4. дальше report переходит в `ready` или `narrative_failed`.

Для PDF path аналогично:

1. backend enqueue'ит `generate_pdf.delay(...)`;
2. worker исполняет `reports.generate_pdf`;
3. PDF загружается в object storage.

## Почему это закрывает runtime gap из S01

S01 зафиксировал, что E11 уже code-ready, но launch path ломается на orchestration-слое: Celery worker не был частью стандартного dev stack и запускался только как неявное знание.

После этой story:

- worker больше не является скрытым ручным шагом;
- compose contract явно показывает, что narrative flow требует отдельный Celery process;
- backend и worker читают согласованный набор runtime env для narrative layer;
- narrative-ready stack можно поднять одной командой, без reverse engineering по исходникам.

## Ограничения этой story

S02 закрывает orchestration contract, но не закрывает весь runtime launch path целиком:

- S03 детализирует mock/real provider env contract;
- S04 фиксирует object storage / bucket bootstrap;
- S05 собирает end-to-end runbook и smoke path;
- S06 оформляет failure triage и launch-readiness checklist.

## Затронутые файлы

| Файл | Действие |
|---|---|
| `docker-compose.yml` | Добавлен `worker` service и narrative runtime env contract для backend/worker |
| `docs/features/E12-llm-report-runtime-readiness/S02-dev-orchestration-worker-runtime.md` | Зафиксирован фактический dev orchestration contract |

## Проверка

Фактически проверено в этой story:

- `docker-compose.yml` успешно парсится как YAML;
- в parsed config присутствует service `worker`;
- command worker'а = `celery -A workers.celery_app.app worker --loglevel=INFO`.

Команда проверки:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

data = yaml.safe_load(Path('docker-compose.yml').read_text())
print(sorted(data['services'].keys()))
print(data['services']['worker']['command'])
PY
```

Ограничение текущей среды проверки:

- `docker compose` в этой WSL-сессии недоступен (`docker: unknown command: docker compose`)
- `docker-compose` тоже недоступен (WSL integration / Docker Desktop CLI gap)

То есть syntax/contract проверен, но фактический контейнерный старт этого story нужно гонять в среде, где Docker Compose реально доступен.

## Критерии приёмки

- [x] В dev stack включён отдельный worker runtime.
- [x] Есть однозначная команда запуска narrative-ready окружения.
- [x] Документировано, где смотреть worker logs и как понять, что narrative tasks реально исполняются.
- [x] Команда не должна догадываться, что Celery нужно запускать отдельно от backend.
