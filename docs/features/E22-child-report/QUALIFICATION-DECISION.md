# E22 S15–S16: пакет решений для завершающего прогона

## Статус разрешений

2026-10-31 владелец выбрал: **«Выполнить S15–S16 до закрытия E22»**. Следовательно, E22 остаётся открытым до исполнения критериев, а не закрывается переносом.

Последующий единый запрос staging scope, численных критериев и provider-cost boundary **истёк без ответа**. Это не отказ пользователя и не одобрение. Ни один предложенный ниже предел не записан как утверждённый или измеренный; мутации staging, выдача доступа, maintenance и новые provider calls по этому пакету не выполняются.

## Предложенный scope — ожидает ответа

- Только staging, никакого изменения production/customer data/payments.
- Временный canonical Child access только allowlisted synthetic A/B, срок/истечение и восстановление фиксируются до mutation; C остаётся expired.
- Разрешённые synthetic fixtures: создание/коррекция charts/answers/generations/age, native sessions, PDF/export, archived/deletion-pending и archive/purge только собственных тестовых агрегатов.
- Staging maintenance/controller, producer freeze, consumer/broker drain, restart/recreate, settings transitions и owned disposable restore DB; original settings, ingress и все cleanup obligations восстанавливаются с readback.
- Полный независимый operator-run по published SOP и explicit safety/access STOP decision. Наличие helper/manifests не засчитывается как исполнение.

## Предложенные количественные критерии — не утверждены

| Параметр                      | Предложение, не измерение                                              |
| ----------------------------- | ---------------------------------------------------------------------- |
| Positive samples              | 50 full native-mock generations, exact/approximate/unknown fixture mix |
| Concurrency                   | Не более 2                                                             |
| Read p95                      | Не более 2 секунд                                                      |
| Write p95                     | Не более 3 секунд                                                      |
| Deterministic publication p95 | Не более 60 секунд                                                     |
| Full mock narrative p95       | Не более 120 секунд                                                    |
| PDF p95                       | Не более 15 секунд                                                     |
| Queued/running maximum age    | Не более 300 секунд                                                    |
| Reconciliation latency        | Не более 120 секунд                                                    |
| Observation window            | 30 минут; exact UTC start/due/end записываются при разрешённом запуске |
| Unexpected errors             | 0; ожидаемые negative/failure fixtures учитываются отдельно            |

Отдельно до запуска требуется зафиксировать fixture/sample mix, measurement clocks, per-operation denominators, percentile calculation rule, equivalence comparison rule для foreign/missing latency и complete producer/controller inventory. Нельзя менять критерии задним числом под получившийся результат.

## Provider-cost boundary — ожидает выбора

1. Native-mock qualification без новых paid calls. Измеренная внешняя стоимость таких вызовов — нулевая, real-provider currency/distributions остаются явно открытым ограничением. Retained production usage и успешный v4 sample не заменяют staging distributions/receipt.
2. Отдельно разрешённая real-provider qualification: нужен явный лимит количества calls/generations, общей суммы и валюты, per-report token/cost/attempt limits и workload/window. Тариф/стоимость проверяются отдельно; не выдумываются по token count.

Ни один вариант пока не выбран. Предыдущие бюджеты production repair исчерпаны. До ответа разрешены только read-only сверка evidence и offline/docs/tooling verification; нельзя выдавать отсутствие ответа за пользовательский запрет или за разрешение.

## Связанные источники

- [S15](./S15-qa-observability-data-safety.md)
- [S16](./S16-rollout-runbook-live-evidence.md)
- [Follow-ups и gate inventory](./PRODUCT-FOLLOW-UPS.md)
- Новый продуктовый дефект `fixemer90-stack/Archemap#51` отложен к отдельному исправлению; его регистрация не закрывает эксплуатационные gates.
