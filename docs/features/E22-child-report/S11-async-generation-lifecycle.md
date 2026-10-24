# S11: Async generation lifecycle

## Статус

✅ Завершено — acceptance criteria подтверждены local/runtime evidence; R1/R2/R3 независимо одобрены. Backend commit `939fd40f47cd430422d4f34ec72e6787249d4cfb`. [Review](../../reviews/2026-10-24/E22-S11-lifecycle.md).

## Контекст

Полный pair calculation и modular narrative не должны выполняться в одном HTTP-запросе. Нужен durable lifecycle с полезным deterministic-ready состоянием.

## Что сделать

1. Добавить Celery/task orchestration для pair foundation, facts, sections и assembly.
2. Реализовать атомарные status transitions и generation claim.
3. Публиковать deterministic report до narrative completion.
4. Добавить retry/backoff/timeout и stuck-job reconciliation.
5. Отделить full generation от age-update lifecycle.

## Затрагиваемые файлы

| Область                                                        | Действие          |
| -------------------------------------------------------------- | ----------------- |
| `backend/workers/tasks/child.py`                               | Изменить/добавить |
| `backend/app/modules/child/service.py`                         | Изменить/добавить |
| `backend/app/modules/child/status.py`                          | Изменить/добавить |
| `backend/tests/integration/test_child_generation_lifecycle.py` | Изменить/добавить |

## Критерии приёмки

- [x] HTTP create быстро возвращает generation ID.
- [x] Deterministic-ready полезен без LLM.
- [x] Provider failure ведёт в narrative_failed, а не стирает result.
- [x] Повторный worker claim не дублирует artifacts/provider calls; crash, transport и concurrent siblings покрыты общим source-report/section fence и PostgreSQL barrier regressions.
- [x] Age update не запускает полный pair pipeline.
- [x] Stuck/retry transitions покрыты integration tests.

## Реализация

- `POST /api/v1/child/reports` принимает только `child_profile_id` и completed `questionnaire_session_id` с `Idempotency-Key`, проверяет backend Plus/direct Child access и active ownership до записи задания. Chart lineage выбирается сервером; stale age/confidence отклоняются без generation/event/dispatch side effects.
- PostgreSQL хранит generation, dispatch/worker leases, claim tokens, attempt counters, retry deadlines и append-only events. Celery выполняет stages и reconciliation; Redis не является единственным durable store.
- Deterministic report публикуется отдельным commit до narrative. Каждый provider intent и завершённая section checkpoint-ятся отдельно. Повторная доставка не повторяет outcome-unknown external call.
- Временная provider failure переводит post-report работу в `narrative_retry_waiting` с exponential backoff; исчерпание попыток — в `narrative_failed`. Published deterministic artifact не скрывается и не пересчитывается при narrative recovery.
- Manual retry сохраняет failed source segment pins, canonical input hashes отсутствующих sections и Guidance Facts hash; после раннего exhaustion восстанавливает также не начатые sections, не меняя опубликованные artifacts. Age update имеет отдельный lifecycle и не пересчитывает pair foundation.
- Read/write/transport timeout (включая wrapped errors) сохраняет `child_narrative_provider_outcome_unknown`; такой outcome нельзя повторно вызвать через automatic/manual/sibling retry. Child использует private copied provider settings с нулевыми internal retries, не меняя другие продукты.
- Перед каждым provider intent full/retry workers берут общий PostgreSQL transaction-advisory lock по source report + section, проверяют sibling intents и фиксируют свой intent одним checkpoint commit. После commit durable `in_progress`/unknown/completed intent не допускает sibling recall; во время external call DB-lock не удерживается. Sibling acceptance не меняется: competing workers fail closed с bounded backoff/exhaustion, не переиспользуют и не мутируют чужой completed result.
- При `LLM_ENABLED=false`/mock configuration production adapter возвращает явный `child_narrative_disabled`, без fake-ready prose и без provider calls. Test-only mock остаётся injectable.
- Published segments, report assemblies и lifecycle events immutable на ORM/DB boundary; additive migration отказывается от lossy downgrade и сохраняет privacy purge path.
- HTTP read/status/regenerate/age-update endpoints относятся к S12; reader/PDF — к S14. S11 не заявляет готовность всего API/UX.

## Verification — 2026-10-24

- После всех fixes parent повторил `pytest tests/unit -q --tb=short` — `1043 passed, 5 warnings` (WeasyPrint/legacy AsyncMock).
- `TEST_DATABASE_URL=<disposable> pytest tests/integration/test_child*.py -q --tb=short` — `120 passed`: все прежние Child Stories, S11 HTTP/access/lifecycle/provider/migration, 24 review regressions и шесть PostgreSQL concurrency scenarios (включая наблюдаемый `pg_locks` wait).
- `ruff check .`, `ruff format --check .` — pass (451 files); `mypy .` — `Success: no issues found in 450 source files`; Alembic — один head `a8b9c0d1e2f3`; `git diff --check` — pass.
- Review regressions покрывают disabled→enabled recovery, early-section exhaustion→healthy recovery, corrupt/missing/injected retry pins, configured DeepSeek/OpenRouter one-POST transport fencing, 429 durable backoff и cross-retry unknown-outcome protection, без реальных provider calls.
- Реальный isolated smoke после fix: fresh Alembic head → Uvicorn HTTP → Redis → Celery solo worker → PostgreSQL. Health `200`, create `202`, replay `202` с тем же generation ID; persisted `narrative_failed`, report `deterministic_ready`, одна assembly, 15 sections (`failed`/`not_applicable`), только `child_narrative_disabled`, без ready prose.
- Smoke использовал отдельную disposable DB/Redis и отключённый LLM, без paid provider calls; локальный основной stack/production не изменялся. Evidence: `/home/balthier/.hermes/cache/scratch/e22-s11-smoke/result.json`, `api.log`, `worker.log`.
- Финальный независимый R3 recheck: approved, security/logic blockers отсутствуют; parent gates и smoke выполнены после последнего code fix.
- GitHub CI run `40103346362` для backend commit: `Lint Backend`, `Test Backend` (полные unit/integration), `Lint Frontend`, `Test & Build Frontend`, `Validate Contracts` — success. Единственное падение `Security Audit/npm audit` исправлено отдельным dependency commit `566ccdd` (Zod 4.6.7); локальный audit — 0 vulnerabilities.
- Registry image builds и staging/production deploy jobs skipped по configured rollout gate; production rollout не заявляется. Staging/reader/PDF smoke остаётся S14–S16.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
