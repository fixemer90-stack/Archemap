# S07: QA, stage и production rollout

## Статус

🟡 Локальные synthetic проверки в работе. Stage/production rollout, canary и observation заблокированы: сервер утрачен. Отсутствующий live evidence не заменяется CI или unit tests.

## Контекст

Retirement затрагивает access, historical artifacts, generic Self Report и два UI reader-а. Локальных unit tests недостаточно для закрытия.

## Что сделать

1. Выполнить backend unit/integration suites и frontend browser matrix.
2. На stage проверить пять identities/scenarios:
   - active Plus;
   - active grandfathered Career entitlement;
   - expired/revoked access;
   - existing legacy Career row;
   - profile без legacy row.
3. Проверить forbidden generic Career write и отсутствие DB mutation.
4. Проверить target E19 questionnaire → report → reader/PDF.
5. Проверить generic Self Report generation → narrative → reader/PDF.
6. Выполнить canary, telemetry readback, rollback rehearsal и production observation.

## Критерии приёмки

- [x] Backend targeted и reports/career regression suites зелёные.
- [x] Frontend typecheck, lint, build и Playwright matrix зелёные.
- [ ] Stage browser доказывает existing/missing legacy deep links и target Career flow.
- [ ] Stage DB before/after подтверждает отсутствие legacy mutation.
- [ ] Self Report non-regression подтверждён реальным flow.
- [ ] Grandfathered entitlement target flow подтверждён browser/API smoke.
- [ ] Rollback восстанавливает pre-retirement routing без потери данных.
- [ ] Production canary и observation window записаны с exact revision/evidence.
- [ ] Physical data deletion не выполнялась.

## Локальное evidence (не stage/production)

До P1 fix parent: **1477 unit / 230 integration**, targeted **16 passed** — прежний baseline, не post-fix evidence. После fix: author full units **1580 passed**; parent fresh **119 focused**, full Ruff/format/mypy PASS; independent SPEC **316 unit + ASGI probe**, CODE/security **119 tests**, оба PASS с совпавшими fingerprints. Parent post-fix full PostgreSQL/Redis integration suite: **230 passed**, 3 warnings in **1385.19s**, `postfix_integration_exit=0 cleanup_exit=0`; task-label readback подтвердил отсутствие контейнеров. Persisted archive JSON/versions/GET-HEAD-POST PDF, immutable before/after, queued/finalizer guards, entitlement/ownership и census входят в этот rerun.

Parent frontend: native E20 browser **54 passed**, desktop/tablet/mobile; 16 contract scripts, repo-wide lint/types/format/build — PASS. Existing warnings не превращены в errors и не выданы за отсутствие предупреждений. Source code/security verdict принят отдельно; CI publication и live gates не закрыты этими локальными результатами.
