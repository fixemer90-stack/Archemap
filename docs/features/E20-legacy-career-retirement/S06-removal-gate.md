# S06: Telemetry, migration decision и final removal gate

## Статус

🟡 Runtime telemetry verified, fresh SPEC/code-security PASS; [runbook](../../deployment/legacy-career-retirement.md) подготовлен. Live readback/window/retention approval заблокированы до восстановления среды. Удаления не разрешены.

## Контекст

Legacy нельзя физически удалить по результатам grep или UI-аудита. Нужны измеряемое использование, data-retention решение и отдельный destructive gate.

## Что сделать

1. Добавить structured events/metrics:
   - blocked legacy Career generation;
   - legacy report read;
   - legacy PDF read;
   - missing legacy row/deep link;
   - target Career access via grandfathered entitlement.
2. Не включать payload, birth data, email или другие PII в labels/logs.
3. Определить observation window и dashboard queries.
4. По census выбрать стратегию rows: retain, export, explicit migration или later deletion.
5. Описать backup/restore и rollback.
6. Создать отдельный approval gate для удаления endpoint/rules/rows.

## Файлы

| Область                      | Действие                         |
| ---------------------------- | -------------------------------- |
| Backend observability        | Metrics/events                   |
| Prometheus/dashboard/runbook | Queries and thresholds           |
| E20 evidence docs            | Census and decision record       |
| Future migration             | Только после отдельного approval |

## Критерии приёмки

- [x] Метрики разделяют reads, PDF, blocked writes и grandfathered target access.
- [x] Labels имеют ограниченную cardinality и не содержат PII.
- [ ] Dashboard/readback подтверждены на stage.
- [ ] Observation window и zero/acceptable-use threshold определены заранее.
- [ ] Стратегия существующих rows утверждена и документирована.
- [ ] Backup/restore rehearsal выполнен до destructive proposal.
- [x] E20 не содержит автоматического `DELETE`/`DROP` legacy Career data.

## Local evidence и незакрытые gates

Native OTel `legacy_career_operations`, sole label `operation`, fixed allowlist; unknown/malformed values ничего не записывают. SPEC `deleg_644a7521`: PASS по runtime scope; independent ASGI probe подтвердил no PDF double-counting. Parent unit/integration regressions проверяют recorder arguments, denied paths и native naming. Fixture-only temporary-table/schema cleanup выполняется только в own disposable test DB, не является customer migration или разрешением удалить legacy rows.

Grafana query templates и default retain boundary записаны в runbook. Ни numeric observation duration/threshold, ни definitive owner retention approval не придуманы вместо отсутствующего census. Stage scrape/readback, full observation window, backup/restore rehearsal и removal approval остаются открытыми.
