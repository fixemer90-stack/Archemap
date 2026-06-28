# S05 — Orchestration, Cache, Retry and Statuses

> Статус: ⬜ Не начато

## Контекст

Staged generation needs orchestration beyond the current single `generate_report_narrative` flow. It must remain observable, retryable and safe under worker failures.

## Что сделать

1. Add storage for stage artifacts.
2. Compute per-stage input hashes.
3. Reuse cached ready stages when upstream inputs did not change.
4. Run section stages in parallel after `NarrativePlan` is ready.
5. Retry only failed/invalid stages when possible.
6. Expose high-level progress in `GET /reports/{id}`.
7. Keep top-level report status backward compatible.

## Затрагиваемые файлы

| Файл                                                               | Действие                                  |
| ------------------------------------------------------------------ | ----------------------------------------- |
| `backend/app/modules/report_narratives/models.py`                  | Stage artifact model or metadata contract |
| `backend/app/modules/report_narratives/service.py`                 | Staged orchestration                      |
| `backend/app/modules/report_narratives/tasks.py`                   | Stage task helpers                        |
| `backend/workers/tasks/reports.py`                                 | Worker entrypoints                        |
| `backend/app/modules/reports/schemas.py`                           | Progress response contract                |
| `backend/tests/unit/test_report_narratives/test_staged_service.py` | Orchestration tests                       |

## Acceptance criteria

- [ ] Stage artifacts have status, prompt_version, model, input_hash, attempt count and error message.
- [ ] Ready cached stages are reused.
- [ ] Failed stage can be retried without deleting ready stages.
- [ ] Parallel section stages start only after plan is valid.
- [ ] Top-level `ready` is set only after final assembly validation passes.
- [ ] Worker logs include stage id, duration, failure kind and recovery action.
