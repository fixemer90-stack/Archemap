# Story E11.S08: Report API integration and regenerate endpoint

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Frontend должен видеть статус narrative generation, получать deterministic fallback data, читать готовый narrative JSON и запускать регенерацию только LLM-текста без пересчёта chart/rules.

## Что сделать

1. Обновить response schemas `ReportResponse`/detail response: добавить `deterministic`/`report_data`, `narrative`, `status`, generation metadata.
2. Обновить `POST /api/v1/reports/generate`: после deterministic calculation enqueue narrative task и вернуть status.
3. Обновить `GET /api/v1/reports/{report_id}`: вернуть `narrative: null` при generation и JSON при ready.
4. Добавить `POST /api/v1/reports/{report_id}/narrative/regenerate`.
5. В regenerate проверить permissions, product support, current state, idempotency/rate limiting basics.
6. Обновить `contracts/openapi.yaml`.
7. Добавить API tests.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `backend/app/modules/reports/router.py` | Extend existing report endpoints, add regenerate route |
| `backend/app/modules/reports/schemas.py` | Response schemas with narrative/status |
| `backend/app/modules/reports/service.py` | Generation integration |
| `backend/app/modules/report_narratives/router.py` | Optional sub-router if route is separated |
| `backend/app/api/v1/__init__.py` | Register router only if separate module prefix is used |
| `contracts/openapi.yaml` | API contract update |
| `backend/tests/unit/test_reports/test_reports.py` | Update existing tests |
| `backend/tests/unit/test_report_narratives/test_api.py` | New API tests |

## Критерии приёмки

- [ ] Generate response can return `status: generating_narrative`.
- [ ] Detail response with generation in progress has `narrative: null` and deterministic data available.
- [ ] Detail response ready includes persisted `narrative` with `prompt_version`, `model_name`, `sections`.
- [ ] Regenerate endpoint creates/enqueues a new narrative attempt without recomputing chart/rules.
- [ ] User cannot access/regenerate someone else’s report.
- [ ] OpenAPI contract matches implemented response shape.
- [ ] API tests cover in-progress, ready, narrative_failed, regenerate permission denied.
