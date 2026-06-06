# Story E11.S08: Report API integration and regenerate endpoint

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Frontend должен видеть статус narrative generation, получать deterministic fallback data, читать готовый narrative JSON и запускать регенерацию только LLM-текста без пересчёта chart/rules.

## Что сделано

1. Обновлены response schemas `ReportResponse`: теперь API возвращает deterministic `report_data`, `status`, `error_message` и `narrative` с generation metadata.
2. `POST /api/v1/reports/generate` теперь возвращает актуальный status (`generating_narrative` / `deterministic_ready`) и latest narrative state.
3. `GET /api/v1/reports/{report_id}` возвращает `narrative: null` во время генерации и полный persisted narrative JSON при `ready`/`narrative_failed`.
4. Добавлен `POST /api/v1/reports/{report_id}/narrative/regenerate`.
5. В regenerate проверяются ownership и product support; повторный вызов при уже идущей генерации не делает лишний enqueue.
6. Для regenerate добавлен `force=True`, чтобы новый LLM attempt не переиспользовал cache hit готового narrative.
7. Обновлён `contracts/openapi.yaml`.
8. Добавлены API tests на in-progress, ready payload, generate response shape, forced regenerate и denied access.

## Затрагиваемые файлы

| Файл                                                    | Действие                                                     |
| ------------------------------------------------------- | ------------------------------------------------------------ |
| `backend/app/modules/reports/router.py`                 | Extend existing report endpoints, add regenerate route       |
| `backend/app/modules/reports/schemas.py`                | Response schemas with narrative/status + serializer helpers  |
| `backend/app/modules/report_narratives/service.py`      | Latest narrative lookup + force regeneration path            |
| `backend/app/modules/report_narratives/tasks.py`        | Force flag propagation for task bridge                       |
| `backend/workers/tasks/reports.py`                      | Celery task accepts `force` regenerate mode                  |
| `contracts/openapi.yaml`                                | API contract update                                          |
| `backend/tests/unit/test_reports/test_reports.py`       | Existing schema tests continue covering report serialization |
| `backend/tests/unit/test_report_narratives/test_api.py` | New API tests                                                |

## Критерии приёмки

- [x] Generate response can return `status: generating_narrative`.
- [x] Detail response with generation in progress has `narrative: null` and deterministic data available.
- [x] Detail response ready includes persisted `narrative` with `prompt_version`, `model_name`, `sections`.
- [x] Regenerate endpoint creates/enqueues a new narrative attempt without recomputing chart/rules.
- [x] User cannot access/regenerate someone else’s report.
- [x] OpenAPI contract matches implemented response shape.
- [x] API tests cover in-progress, ready, narrative_failed/regenerate permission path.

## Проверка

```bash
cd backend
docker compose exec -T backend python -m ruff check app/modules/report_narratives app/modules/reports workers/tasks tests/unit/test_report_narratives tests/unit/test_reports
docker compose exec -T backend python -m ruff format --check app/modules/report_narratives app/modules/reports workers/tasks tests/unit/test_report_narratives tests/unit/test_reports
docker compose exec -T backend python -m mypy app/modules/report_narratives app/modules/reports workers/tasks tests/unit/test_report_narratives tests/unit/test_reports
docker compose exec -T backend python -m pytest tests/unit/test_report_narratives tests/unit/test_reports/test_reports.py -q
```
