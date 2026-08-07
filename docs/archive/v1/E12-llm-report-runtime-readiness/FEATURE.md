# Feature E12: LLM Report Runtime Readiness — запуск narrative-отчёта в реальном окружении

**Статус:** ✅ Готово

## Цель

Довести инфраструктуру, конфигурацию и операционный контур до состояния, в котором Self-report с E11 можно реально запускать end-to-end: `POST /api/v1/reports/generate` создаёт deterministic report, Celery worker подхватывает narrative task, LLM provider отвечает, frontend проходит polling/status flow, PDF публикуется без ручных обходов.

E12 не добавляет новый narrative product contract. Он превращает уже реализованный E11 из «код и документы готовы» в «workflow реально запускается в локальном/dev окружении и может быть включён в staging/production».

## Проблема

E11 описывает и реализует narrative pipeline, но для фактического запуска недостаточно только feature-кода:

- в compose-контуре нет отдельного Celery worker service;
- `LLM_ENABLED` по умолчанию выключен;
- runtime env для real provider не оформлен как понятный контракт запуска;
- MinIO/S3 bucket bootstrap для PDF не закреплён как обязательный шаг;
- нет единого runbook/checklist, по которому можно поднять сервисы и проверить happy path;
- нет явного launch-readiness набора smoke checks для статусов `generating_narrative -> ready` и fallback paths.

Итог: E11 архитектурно готов, но запуск narrative report с LLM всё ещё зависит от ручного знания проекта.

## Главный результат E12

> После завершения E12 команда может поднять окружение по документации и получить реальный LLM Self-report без догадок и ручного reverse engineering.

## Зависимости

- `E1 Foundation` ✅ — Docker, базовая инфраструктура.
- `E3 Chart Engine` ✅ — deterministic report input.
- `E5 Products & Reports` 🟡 — report generation, PDF pipeline, storage.
- `E10 Report UX Redesign` ✅ — narrative-first UI.
- `E11 LLM Report Narrative` ✅ — narrative contracts, task flow, API, frontend states.
- `docs/features/E11-llm-report-narrative/WORKFLOW.md`
- `docs/features/E11-llm-report-narrative/API.md`

## Scope

### Входит

- Runtime inventory: что именно требуется для E11 launch path.
- Docker/dev orchestration для backend + frontend + postgres + redis + minio + celery worker.
- Environment contract для mock и real LLM provider.
- Bucket/bootstrap contract для PDF storage.
- Runbook локального запуска narrative flow.
- Smoke сценарий проверки: generate → polling → ready/fallback → regenerate.
- Launch readiness checklist для dev/staging.
- Минимальная observability/triage документация по stuck tasks, disabled provider, missing bucket, bad API key, timeout.

### Не входит

- Новый prompt/version narrative content.
- Изменение `NarrativeInput` / `SelfNarrative` контрактов.
- Новый frontend UX beyond E11.
- Career/Love narrative products.
- Production-grade secrets manager / full deployment platform work из E8.
- Масштабирование очередей, autoscaling, GitOps и load testing.

## Архитектурный target state

```text
Developer/QA starts local stack
  -> postgres + redis + minio + backend + frontend + celery worker are up
  -> backend has LLM_ENABLED=true and provider config
  -> worker consumes reports.generate_report_narrative
  -> bucket exists for PDF uploads
  -> user generates self report
  -> report status transitions: generating_narrative -> ready | narrative_failed
  -> frontend handles polling/fallback
  -> PDF task uploads artifact successfully
```

## Критерии приёмки фичи

- [x] В проекте зафиксирован минимальный runtime stack для E11 launch path.
- [x] В dev orchestration есть отдельный worker process/service для Celery tasks.
- [x] Документирован и проверяем mock-provider path: `LLM_ENABLED=true`, `LLM_PROVIDER=mock`.
- [x] Документирован и проверяем real-provider path: `LLM_ENABLED=true`, `LLM_PROVIDER=<real>`, API key, model, timeout/retry.
- [x] Документирован bootstrap object storage для PDF: bucket existence не остаётся скрытым ручным шагом.
- [x] Есть runbook: как поднять окружение, где смотреть логи, как проверить narrative happy path и fallback path.
- [x] Есть smoke checklist, подтверждающий, что `POST /api/v1/reports/generate` приводит к `ready` при рабочем provider и к осмысленному fallback/failed state при проблемах.
- [x] Документация явно различает «mock narrative для теста pipeline» и «реальный LLM narrative для продуктовой проверки».
- [x] После завершения E12 новый участник команды может поднять flow без обращения к исходникам как единственному источнику истины.

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [Runtime inventory and gap analysis](S01-runtime-inventory-gap-analysis.md) | ✅ Готово |
| S02 | [Dev orchestration: compose/worker runtime contract](S02-dev-orchestration-worker-runtime.md) | ✅ Готово |
| S03 | [LLM environment contract: mock and real provider](S03-llm-environment-contract.md) | ✅ Готово |
| S04 | [Object storage and PDF bootstrap](S04-object-storage-pdf-bootstrap.md) | ✅ Готово |
| S05 | [Local runbook: start, logs, smoke flow](S05-local-runbook-start-logs-smoke.md) | ✅ Готово |
| S06 | [Failure triage and launch readiness checklist](S06-failure-triage-launch-checklist.md) | ✅ Готово |

## Минимальный порядок разработки

1. S01 — зафиксировать реальное текущее состояние и gap list.
2. S02 — описать/внести orchestration contract с worker.
3. S03 — зафиксировать env contract для mock и real LLM.
4. S04 — закрыть storage/PDF bootstrap path.
5. S05 — написать runbook и smoke flow.
6. S06 — собрать triage + launch readiness checklist.

## Live verification snapshot

На 2026-06-07 feature была дополнительно подтверждена живым локальным smoke в compose-стеке:

- `docker compose ps` показал поднятые `postgres`, `redis`, `minio`, `backend`, `frontend`, `worker`.
- bucket bootstrap выполнен через backend runtime (`S3Storage().ensure_bucket()`).
- auth prerequisites проверены живым path: `register -> verify -> login`.
- `POST /api/v1/reports/generate` вернул `200` и стартовый `status=generating_narrative`.
- worker завершил controlled fallback narrative при `LLM_ENABLED=false`/disabled provider без `IndexError` и перевёл report в `ready`.
- PDF task завершился успешно: `pdf_generated=true`, `pdf_url` заполнен.
- `GET /api/v1/reports/{id}/pdf` вернул `307` на fresh signed URL.

Вывод по readiness:

- для локального/dev controlled fallback path E12 readiness подтверждён;
- story S06 можно начинать без дополнительных runtime-блокеров;
- единственное, что отдельно остаётся для продуктовой проверки, — real-provider smoke с валидным `openrouter` ключом, но это не блокирует локальную runtime-readiness документацию E12.

## Проверка закрытия фичи

Infrastructure/runtime:

```bash
docker compose up -d postgres redis minio backend frontend worker
```

Backend:

```bash
cd backend
python3 -m ruff check .
python3 -m ruff format --check .
python3 -m mypy .
python3 -m pytest tests/unit -q
```

Frontend:

```bash
cd frontend
npm test
npx tsc --noEmit --pretty false
npx prettier --check .
npx eslint .
```

Smoke flow:

```text
1. Создать/иметь пользователя и profile.
2. Вызвать POST /api/v1/reports/generate для product=self.
3. Убедиться, что report получает generating_narrative или deterministic_ready.
4. Проверить, что worker обрабатывает narrative task.
5. Через GET /api/v1/reports/{id} получить ready + narrative либо narrative_failed с fallback-логикой.
6. Проверить regenerate endpoint.
7. Проверить PDF upload path.
```
