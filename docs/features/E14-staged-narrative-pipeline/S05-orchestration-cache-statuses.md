# S05 — Orchestration, Cache, Retry and Statuses

> Статус: 🟡 В процессе
> Базовый backend commit: `e7528b8`

## Контекст

Staged generation needs orchestration beyond the current single `generate_report_narrative` flow. It must remain observable, retryable and safe under worker failures.

## Что уже сделано

1. Добавлен typed stage artifact contract.
2. Добавлен расчёт per-stage input hashes.
3. Добавлено cache reuse для ready stage artifacts.
4. Добавлен retry-safe behavior: failed stage можно вернуть в pending без потери ready siblings.
5. Добавлен progress snapshot contract для `GET /reports/{id}` payload metadata.
6. Добавлены unit tests на stage gating / retry / cache reuse.

## Что ещё осталось

1. Подключить stage orchestration в реальный `generate_report_narrative` / worker flow.
2. Реально запускать section stages после plan stage, а не только держать helper-контракт.
3. Проставлять top-level `ready` только после end-to-end staged assembly/validation.
4. Добавить реальные worker logs: `stage_id`, `duration`, `failure_kind`, `recovery_action`.
5. Решить вопрос отдельного persisted stage storage vs metadata-only baseline.

## Затрагиваемые файлы

| Файл                                                               | Действие                                  |
| ------------------------------------------------------------------ | ----------------------------------------- |
| `backend/app/modules/report_narratives/models.py`                  | Baseline metadata contract remains JSON-backed |
| `backend/app/modules/report_narratives/service.py`                 | Staged orchestration helpers              |
| `backend/app/modules/report_narratives/tasks.py`                   | Ещё требует full runtime wiring           |
| `backend/workers/tasks/reports.py`                                 | Ещё требует staged worker entrypoints     |
| `backend/app/modules/reports/schemas.py`                           | Progress response contract                |
| `backend/tests/unit/test_report_narratives/test_staged_service.py` | Orchestration tests                       |

## Acceptance criteria

- [x] Stage artifacts have status, prompt_version, model, input_hash, attempt count and error message.
- [x] Ready cached stages are reused.
- [x] Failed stage can be retried without deleting ready stages.
- [x] Parallel section stages are gated to start only after plan is valid.
- [ ] Top-level `ready` is set only after final assembly validation passes.
- [ ] Worker logs include stage id, duration, failure kind and recovery action.

## Verification

- `pytest tests/unit/test_report_narratives/test_staged_service.py tests/unit/test_report_narratives/test_staged_prompts.py tests/unit/test_report_narratives/test_chart_dynamics.py tests/unit/test_report_narratives/test_aspect_synthesis.py tests/unit/test_report_narratives/test_deep_synthesis.py tests/unit/test_report_narratives/test_input_builder.py -q` → `20 passed`
- `pytest tests/unit/test_report_narratives tests/unit/test_reports -q` → `119 passed`
- `ruff check app/modules/report_narratives/service.py app/modules/report_narratives/schemas.py app/modules/reports/schemas.py tests/unit/test_report_narratives/test_staged_service.py`
- `mypy app/modules/report_narratives/service.py app/modules/report_narratives/schemas.py app/modules/reports/schemas.py tests/unit/test_report_narratives/test_staged_service.py`
