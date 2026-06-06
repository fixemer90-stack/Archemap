# Story E11.S12: Quality gates, tests and observability

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ✅ Завершено

## Контекст

LLM feature introduces cost, latency, nondeterminism and safety risk. Closure requires explicit tests, logging, metrics-like observability signals and CI gates proving no real network LLM calls happen in automated tests and no endless generation state remains.

## Что сделано

1. Дополнено backend unit coverage для narrative service/observability и stable input hash.
2. Подтверждено, что frontend regression script уже проверяет narrative-first order, timeout/fallback states и отсутствие endless spinner-only state.
3. В narrative service добавлены structured logs для start/cache-hit/success/failure/invalid-input без prompt dump и без API key.
4. В CI добавлен явный guard test env: `LLM_ENABLED=false`, `LLM_PROVIDER=mock`, `LLM_MODEL=mock-self-v1`.
5. Создан `PROJECT_INDEX.md` с актуальной картой narrative modules/routes/checks.
6. Зафиксированы реальные verification commands и pass criteria.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `backend/tests/unit/test_report_narratives/test_hash.py` | Stable hash coverage |
| `backend/tests/unit/test_report_narratives/test_tasks.py` | Observability/service logging coverage |
| `backend/app/modules/report_narratives/service.py` | Structured logs, duration, failure kinds |
| `frontend/scripts/check-report-ux.mjs` | Existing narrative regression checks verified |
| `.github/workflows/ci.yml` | Explicit mock-provider CI env guard |
| `PROJECT_INDEX.md` | Project/module/API index for stable narrative paths |
| `docs/features/E11-llm-report-narrative/FEATURE.md` | Story status sync |

## Verification commands

Backend:

```bash
cd /home/balthier/archemap
docker compose exec -T backend sh -lc '
  cd /app && \
  python -m ruff check app/modules/report_narratives tests/unit/test_report_narratives tests/unit/test_reports/test_pdf.py && \
  python -m ruff format --check app/modules/report_narratives tests/unit/test_report_narratives tests/unit/test_reports/test_pdf.py && \
  python -m mypy app/modules/report_narratives app/modules/llm tests/unit/test_report_narratives tests/unit/test_reports/test_pdf.py && \
  python -m pytest tests/unit/test_report_narratives tests/unit/test_reports/test_pdf.py -q
'
```

Frontend:

```bash
cd /home/balthier/archemap/frontend
npm test
npx tsc --noEmit --pretty false
npx prettier --check .
npx eslint .
```

Expected pass criteria:
- backend checks green
- frontend checks green
- no real LLM provider/network required in tests
- structured logs include event type / duration / failure kind, but not raw prompt dump or API key

## Критерии приёмки

- [x] Backend unit tests cover all narrative service layers with mock provider.
- [x] Frontend regression script checks narrative-first order and no endless spinner-only state.
- [x] CI/test env uses `LLM_PROVIDER=mock` or equivalent fake provider.
- [x] Logs do not include API keys or full raw prompts with sensitive profile data.
- [x] Metrics/logs distinguish provider failure, validation failure and invalid input.
- [x] All backend and frontend quality gates listed in `FEATURE.md` pass.
- [x] Feature docs remain honest: no story marked done until code and tests are implemented.

## Notes

- Frontend regression coverage for timeout/fallback/order already lived in `frontend/scripts/check-report-ux.mjs`; S12 verifies and relies on it rather than duplicating the script.
- Observability is implemented here as structured logs with `duration_ms`, `failure_kind`, `recovery_action`, `error_type` and explicit event names. A separate metrics backend was not present in the project, so no Prometheus/counter layer was added.
- E11 feature as a whole is still not fully shipped while S11 runtime PDF smoke remains blocked by missing WeasyPrint system libs in the backend container.
