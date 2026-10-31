# E22 S15–S16: пакет решений для завершающего прогона

## Статус разрешений

2026-10-31 владелец выбрал: **«Выполнить S15–S16 до закрытия E22»**. Следовательно, E22 остаётся открытым до исполнения критериев, а не закрывается переносом.

Первый единый запрос staging scope, численных критериев и provider-cost boundary истёк без ответа; это не было отказом. После публикации пакета владелец ответил **«давйа»** на предложение продолжить согласование и запуск. С этого ответа принят описанный ниже staging-only scope и предложенные пределы, в безопасном режиме **native-mock без новых платных calls**. Это разрешение на исполнение, не доказательство прохождения измерений. Real-provider currency/distributions остаются явно неквалифицированными.

## Разрешённый staging-only scope

- Только staging, никакого изменения production/customer data/payments.
- Временный canonical Child access только allowlisted synthetic A/B, срок/истечение и восстановление фиксируются до mutation; C остаётся expired.
- Разрешённые synthetic fixtures: создание/коррекция charts/answers/generations/age, native sessions, PDF/export, archived/deletion-pending и archive/purge только собственных тестовых агрегатов.
- Staging maintenance/controller, producer freeze, consumer/broker drain, restart/recreate, settings transitions и owned disposable restore DB; original settings, ingress и все cleanup obligations восстанавливаются с readback.
- Полный независимый operator-run по published SOP и explicit safety/access STOP decision. Наличие helper/manifests не засчитывается как исполнение.

## Принятые количественные критерии — результаты ещё не получены

| Параметр                      | Предел, не измеренный результат                                        |
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

## Provider-cost boundary — native-mock, без платных calls

1. Native-mock qualification без новых paid calls. Нужно подтвердить отсутствие внешних provider calls и связанных внешних расходов; до результата нулевая стоимость не выдаётся за измерение. Real-provider currency/distributions остаются явно открытым ограничением. Retained production usage и успешный v4 sample не заменяют staging distributions/receipt.
2. Отдельно разрешённая real-provider qualification: нужен явный лимит количества calls/generations, общей суммы и валюты, per-report token/cost/attempt limits и workload/window. Тариф/стоимость проверяются отдельно; не выдумываются по token count.

Для текущего запуска используется вариант 1: ноль новых paid calls. Вариант 2 не разрешён и не выполняется; предыдущие production repair budgets исчерпаны. Native-mock qualification не выдаётся за прохождение real-provider currency/distribution критериев. Все S15–S16 checkbox остаются открытыми до фактического результата и независимого readback; scope-specific limitations фиксируются отдельно.

## Preflight STOP — 2026-10-31

Первичный и повторный read-only preflight (включая независимый parent readback) выявил два фактических isolation failures **до любых мутаций**:

- На `astrotype_edge` помимо staging gateway находятся staging backend/frontend. Существующая конфигурация даёт обход предусмотренной gateway-only сетевой границы; исправление должно сохранить proxy DNS на private staging network, не менять production Caddy.
- Fingerprints `YOOKASSA_SHOP_ID`/`YOOKASSA_SECRET_KEY` staging совпадают с production. Это не доказательство платежа или live-shop mode: payment/provider requests не отправлялись. Для native-mock qualification нужен явный no-payment контур без наследования production credentials и с fail-closed запретом HTTP при отсутствующих ключах, не выдуманные merchant credentials.

Отдельные PostgreSQL/Redis volumes, app/database secrets и effective `mock` во всех четырёх staging consumers подтверждены. Все 22 наблюдённых container identities/start times и production markers сохранились; production health 200. **0/50 measured samples**, observation window не начиналось; grants, maintenance, backup/restore/refresh и fixtures не выполнялись, cleanup obligations этого preflight отсутствуют.

Private evidence: `e22-s15-preflight-20261031T1340Z`, handoff `/home/balthier/.hermes/cache/scratch/e22-s15-staging-qualification-handoff.md`. Repository fix `4f104c8c6e6d297f99b382684ed8e62ebee7da03` независимо APPROVED; parent повторил **1309 unit tests**, Ruff/format/mypy PASS. Exact CI `41209406856` теперь **completed/success, 8/8**: прежний bounded wait не был failed run и не является текущим blocker. Код пока не применён к live staging.

Повторный preflight сохранил isolation STOP и выявил отсутствующий проверенный maintenance/all-producer freeze controller по опубликованным зависимостям. Его создание входит в разрешённый scope: начата реализация narrow stage-only controller с production-denial, inventory/drain/recovery/exact-restore тестами и независимым review до provision. Это не разрешение обойти STOP непроверенным скриптом. **0/50 samples**, окно не начато; никаких grants/restarts/provider calls или production mutations пока не выполнено.

Production credential values, payments и production runtime не изменяются. После provisioning проверенного controller выполняются fresh backup/restore, stage-only remediation, повторный isolation/DNS/auth/readiness preflight, frozen protocol, 50 samples и literal window; затем отдельный независимый S16 operator. Ни первый STOP, ни исходники controller не засчитываются как benchmark или full S16 PASS.

## Связанные источники

- [S15](./S15-qa-observability-data-safety.md)
- [S16](./S16-rollout-runbook-live-evidence.md)
- [Follow-ups и gate inventory](./PRODUCT-FOLLOW-UPS.md)
- Новый продуктовый дефект `fixemer90-stack/Archemap#51` отложен к отдельному исправлению; его регистрация не закрывает эксплуатационные gates.
