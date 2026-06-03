# Story E11.S07: Celery generation task, statuses and retry

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Пользователь не должен ждать LLM внутри HTTP-запроса. Narrative generation должна идти асинхронно, иметь явные статусы и не превращаться в бесконечный spinner при timeout/provider error/validation failure.

## Что сделать

1. Добавить statuses report/narrative lifecycle: `deterministic_ready`, `generating_narrative`, `ready`, `narrative_failed`.
2. Реализовать Celery task `generate_report_narrative_task(report_id)`.
3. В task вызвать `ReportNarrativeService.generate_for_report`.
4. Добавить retry policy: retry для timeout/429/5xx provider error, no retry для invalid input/report not found/validation failed after repair.
5. Сохранять `generation_started_at`, `generation_finished_at`, `generation_error`, `generation_attempts`.
6. Гарантировать idempotency при повторном запуске task.
7. Добавить tests без реального Celery broker через eager/fake service или direct task invocation.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `backend/workers/tasks/reports.py` | Добавить narrative task или import |
| `backend/app/modules/report_narratives/tasks.py` | Narrative task wrapper, если выбран отдельный файл |
| `backend/app/modules/reports/models.py` | Status enum/fields при необходимости |
| `backend/app/modules/reports/service.py` | Enqueue после deterministic save |
| `backend/app/modules/report_narratives/service.py` | Generation orchestration |
| `backend/tests/unit/test_report_narratives/test_tasks.py` | Task/status tests |

## Критерии приёмки

- [ ] `POST /reports/generate` не ждёт real LLM call.
- [ ] После deterministic save report получает статус `generating_narrative` или controlled fallback status.
- [ ] Successful task сохраняет narrative и переводит report в `ready`.
- [ ] Failed task сохраняет error и переводит report/narrative в `narrative_failed`, а не оставляет вечную генерацию.
- [ ] Retries ограничены `LLM_MAX_RETRIES`.
- [ ] Повторный task не создаёт duplicate completed narrative для того же hash/prompt/model.
