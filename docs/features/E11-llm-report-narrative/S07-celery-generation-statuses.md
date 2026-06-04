# Story E11.S07: Celery generation task, statuses and retry

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Пользователь не должен ждать LLM внутри HTTP-запроса. Narrative generation должна идти асинхронно, иметь явные статусы и не превращаться в бесконечный spinner при timeout/provider error/validation failure.

## Что сделано

1. Добавлены report lifecycle statuses вокруг narrative layer: `deterministic_ready`, `generating_narrative`, `ready`, `narrative_failed`.
2. Реализован Celery task `generate_report_narrative(report_id)` в `workers/tasks/reports.py`.
3. Добавлен orchestration service `ReportNarrativeService.generate_for_report(report_id)`.
4. Добавлена retry policy: retry только для timeout/provider unavailable; no retry для invalid input/report not found/validation failed after repair.
5. Использованы поля `generation_started_at`, `generation_finished_at`, `error_message`, `generation_attempts` в `report_narratives`.
6. Гарантирована idempotency через cache lookup и reuse existing narrative row по `report_id + prompt_version + input_hash + model_name`.
7. Добавлены unit tests через direct task invocation и fake providers, без реального Celery broker.

## Затронутые файлы

| Файл | Действие |
|---|---|
| `backend/workers/tasks/reports.py` | Celery task for narrative generation + retry/final failure handling |
| `backend/app/modules/report_narratives/tasks.py` | Sync/async task bridge, retry classification, terminal failure finalizer |
| `backend/app/modules/reports/service.py` | `deterministic_ready` status after deterministic save |
| `backend/app/modules/reports/router.py` | Enqueue narrative task and switch to `generating_narrative` / fallback to `deterministic_ready` |
| `backend/app/modules/report_narratives/service.py` | Narrative generation orchestration |
| `backend/app/modules/report_narratives/prompts/__init__.py` | Prompt loader package export for typed imports |
| `backend/tests/unit/test_report_narratives/test_tasks.py` | Task/status/retry/idempotency tests |

## Критерии приёмки

- [x] `POST /reports/generate` не ждёт real LLM call.
- [x] После deterministic save report получает статус `generating_narrative` или controlled fallback status.
- [x] Successful task сохраняет narrative и переводит report в `ready`.
- [x] Failed task сохраняет error и переводит report/narrative в `narrative_failed`, а не оставляет вечную генерацию.
- [x] Retries ограничены `LLM_MAX_RETRIES`.
- [x] Повторный task не создаёт duplicate completed narrative для того же hash/prompt/model.

## Проверка

```bash
cd backend
docker compose exec -T backend python -m ruff check app/modules/report_narratives app/modules/reports workers/tasks tests/unit/test_report_narratives
docker compose exec -T backend python -m ruff format --check app/modules/report_narratives app/modules/reports workers/tasks tests/unit/test_report_narratives
docker compose exec -T backend python -m mypy app/modules/report_narratives app/modules/reports workers/tasks tests/unit/test_report_narratives
docker compose exec -T backend python -m pytest tests/unit/test_report_narratives -q
```
