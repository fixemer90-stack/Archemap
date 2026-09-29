# S07: QA, stage и production rollout

## Статус

⬜ Не начато

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

- [ ] Backend targeted и reports/career regression suites зелёные.
- [ ] Frontend typecheck, lint, build и Playwright matrix зелёные.
- [ ] Stage browser доказывает existing/missing legacy deep links и target Career flow.
- [ ] Stage DB before/after подтверждает отсутствие legacy mutation.
- [ ] Self Report non-regression подтверждён реальным flow.
- [ ] Grandfathered entitlement target flow подтверждён browser/API smoke.
- [ ] Rollback восстанавливает pre-retirement routing без потери данных.
- [ ] Production canary и observation window записаны с exact revision/evidence.
- [ ] Physical data deletion не выполнялась.
