# S05 — Orchestration, Cache, Retry and Statuses

> Статус: ✅ Готово
> Базовый backend commit: `e7528b8`
> Последняя синхронизация с кодом: 2026-06-30

## Контекст

Staged generation needs orchestration beyond the current single `generate_report_narrative` flow. It must remain observable, retryable and safe under worker failures.

## Что уже сделано

1. Добавлен typed stage artifact contract.
2. Добавлен расчёт per-stage input hashes.
3. Добавлено cache reuse для ready stage artifacts.
4. Добавлен retry-safe behavior: failed stage можно вернуть в pending без потери ready siblings.
5. Добавлен progress snapshot contract для `GET /reports/{id}` payload metadata.
6. Добавлены unit tests на stage gating / retry / cache reuse.

## Что уже закрыто поверх baseline

1. Staged orchestration подключена в реальный `generate_report_narrative` / worker flow.
2. `plan -> section stages -> assembly` реально исполняются в shipped runtime.
3. Top-level `ready` проставляется только после успешной staged assembly и final validation.
4. Runtime progress snapshots persist-ятся в `narrative.content.stage_progress` / `stage_artifacts` и доступны live polling path.

## Что ещё осталось

Blocking runtime gaps в рамках S05 больше не осталось.

Отдельная persisted table для stage artifacts не требуется для shipped MVP: текущий metadata-in-JSON runtime contract (`narrative.content.stage_progress` / `stage_artifacts`) принят как достаточный baseline. Вынос в отдельное storage layer остаётся только будущим архитектурным упрощением, а не незакрытой частью story.

## Затрагиваемые файлы

| Файл                                                               | Действие                                       |
| ------------------------------------------------------------------ | ---------------------------------------------- |
| `backend/app/modules/report_narratives/models.py`                  | Baseline metadata contract remains JSON-backed |
| `backend/app/modules/report_narratives/service.py`                 | Staged orchestration helpers                   |
| `backend/app/modules/report_narratives/tasks.py`                   | Runtime task wiring и failure handling         |
| `backend/workers/tasks/reports.py`                                 | Celery entrypoint для staged runtime path      |
| `backend/app/modules/reports/schemas.py`                           | Progress response contract                     |
| `backend/tests/unit/test_report_narratives/test_staged_service.py` | Orchestration tests                            |

## Acceptance criteria

- [x] Stage artifacts have status, prompt_version, model, input_hash, attempt count and error message.
- [x] Ready cached stages are reused.
- [x] Failed stage can be retried without deleting ready stages.
- [x] Section stages start only after a valid `NarrativePlan` stage and now run in parallel inside the shipped runtime.
- [x] Top-level `ready` is set only after final assembly validation passes.
- [x] Runtime logs include per-stage `stage_id`, `duration`, `failure_kind`, `recovery_action`, `model_name` and retry metadata without prompt bodies.

## Verification

- `pytest tests/unit/test_report_narratives/test_staged_service.py tests/unit/test_report_narratives/test_staged_prompts.py tests/unit/test_report_narratives/test_chart_dynamics.py tests/unit/test_report_narratives/test_aspect_synthesis.py tests/unit/test_report_narratives/test_deep_synthesis.py tests/unit/test_report_narratives/test_input_builder.py -q` → `20 passed`
- `pytest tests/unit/test_report_narratives tests/unit/test_reports -q` → `119 passed`
- `ruff check app/modules/report_narratives/service.py app/modules/report_narratives/schemas.py app/modules/reports/schemas.py tests/unit/test_report_narratives/test_staged_service.py`
- `mypy app/modules/report_narratives/service.py app/modules/report_narratives/schemas.py app/modules/reports/schemas.py tests/unit/test_report_narratives/test_staged_service.py`
