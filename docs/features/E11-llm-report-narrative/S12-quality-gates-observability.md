# Story E11.S12: Quality gates, tests and observability

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

LLM feature introduces cost, latency, nondeterminism and safety risk. Closure requires explicit tests, logging, metrics and CI gates proving no real network LLM calls happen in automated tests and no endless generation state remains.

## Что сделать

1. Add unit coverage for schemas, input builder, hash, provider factory, prompt guardrails, validators, service, tasks and API.
2. Add frontend regression checks for narrative section order, technical disclosure, generation timeout and fallback states.
3. Add logs around generation start/success/failure without secrets or raw sensitive prompt dumps.
4. Add metrics/counters if observability layer supports it: generation attempts, success, failure, validation failure, provider timeout, duration.
5. Add CI guard/fake provider configuration so tests cannot hit real LLM provider.
6. Document verification commands and expected pass criteria in this story when implemented.
7. Update `PROJECT_INDEX.md` and relevant docs if new modules/routes become permanent.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `backend/tests/unit/test_report_narratives/` | Complete unit coverage |
| `frontend/scripts/check-report-ux.mjs` | Narrative regression checks |
| `backend/app/modules/report_narratives/service.py` | Structured logs/metrics hooks |
| `.github/workflows/ci.yml` | Only if CI env needs explicit `LLM_PROVIDER=mock` |
| `PROJECT_INDEX.md` | Update project index after implementation paths stabilize |
| `docs/features/E11-llm-report-narrative/FEATURE.md` | Mark criteria only after real implementation passes |

## Критерии приёмки

- [ ] Backend unit tests cover all narrative service layers with mock provider.
- [ ] Frontend regression script checks narrative-first order and no endless spinner-only state.
- [ ] CI/test env uses `LLM_PROVIDER=mock` or equivalent fake provider.
- [ ] Logs do not include API keys or full raw prompts with sensitive profile data.
- [ ] Metrics/logs distinguish provider failure, validation failure and invalid input.
- [ ] All backend and frontend quality gates listed in `FEATURE.md` pass.
- [ ] Feature docs remain honest: no story marked done until code and tests are implemented.
