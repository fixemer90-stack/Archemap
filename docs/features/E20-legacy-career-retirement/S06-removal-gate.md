# S06: Telemetry, migration decision и final removal gate

## Статус

⬜ Не начато

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

- [ ] Метрики разделяют reads, PDF, blocked writes и grandfathered target access.
- [ ] Labels имеют ограниченную cardinality и не содержат PII.
- [ ] Dashboard/readback подтверждены на stage.
- [ ] Observation window и zero/acceptable-use threshold определены заранее.
- [ ] Стратегия существующих rows утверждена и документирована.
- [ ] Backup/restore rehearsal выполнен до destructive proposal.
- [ ] E20 не содержит автоматического `DELETE`/`DROP` legacy Career data.
