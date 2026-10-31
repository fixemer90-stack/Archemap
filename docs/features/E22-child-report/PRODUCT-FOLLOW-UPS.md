# E22: продуктовые follow-ups и границы завершения

## Открытый продуктовый дефект: избыточное отсечение разделов

GitHub: `fixemer90-stack/Archemap#51` — `[Child] Избыточные пороги скрывают тематические разделы при наличии данных`.

Статус: **зафиксирован к последующему исправлению**, не реализован. Владелец 2026-10-31 поручил сохранить эту задачу отдельно и завершать текущий E22. Регистрация задачи не разрешает новые платные генерации, не меняет production и не является отказом от остальных эксплуатационных критериев.

### Симптом и подтверждение

Принятый production `cf3a4e6`, narrative V4, core version 5: все 26 source dimensions присутствуют, 11 ready sections, 0 failed/missing, но четыре тематических раздела имеют omission notice. Для текущего контракта это корректное поведение; его продуктовая полезность оспорена владельцем.

`strong_matches`/`friction_points` требуют порогов выраженности; `natural_contact`/`friction_zones` допускают только соответствующие семьи фактов. `conflict_cycle`/`not_personal` ограничены соответствующими `avoid_patterns`. Наличие исходных расчётов со средними/смешанными сигналами поэтому не гарантирует содержательное пояснение темы. Средняя зона в основном перенесена в `conscious_adjustments`.

### Требуемое изменение

- Отделить safety/grounding от редакционного допуска темы: отсутствие сильного сигнала не равно отсутствию информации.
- Варьировать уверенность и тип пояснения, а не автоматически скрывать весь раздел при непройденном пороге выраженности.
- Различать отсутствующие входы, неоднозначные сигналы и отсутствие выраженного перекоса; не называть всё «недостатком данных».
- Давать содержательные тематические объяснения и привязанные к источникам шаги наблюдения, не выдумывая свойства ребёнка или конкретные конфликтные сценарии.
- Не исправлять проблему снижением порогов ради filled sections, generic prose, length quotas или ослаблением child-safety/evidence/ownership.

Критерии приёмки и RED-сценарий зафиксированы в issue #51. Новый контракт должен быть версионирован, проверен на средних/смешанных/противоречивых случаях через persistence/API/desktop/mobile/PDF; старые immutable reports/read/retry не переинтерпретируются. Текущий принятый отчёт и закрытый BUG-50 остаются на своём контракте. Не объявлять #51 выполненным только после изменения текста заглушки.

## Закрытый BUG-50 — отдельная область приёмки

[BUG-50](../../reviews/2026-10-28/BUG-50-child-content-quality.md) закрыт после устранения collapse, narrative repetition, потери facts и ошибки citation contract; выполнены явно разрешённый real-provider repair и независимая приёмка. Это не утверждение, что четыре omissions продуктово оптимальны. S09/S10/S14 сохраняют закрытый статус по своим проверенным критериям; #51 — новый продуктовый follow-up, а не задним числом расширенный критерий старого бага.

## Оставшиеся критерии текущего E22

Источники истины — [S15](./S15-qa-observability-data-safety.md) и [S16](./S16-rollout-runbook-live-evidence.md), не число галочек в родительском FEATURE.

| Критерий                       | Текущее подтверждение                                                                   | Что остаётся                                                                                          |
| ------------------------------ | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| S15 latency/cost/stuck budgets | Реальные accepted samples, numeric token usage, healthy lifecycle и telemetry есть      | Утверждённые workload/window/budgets и измеренные distributions/currency evidence; один sample не p95 |
| S16 independent operator-run   | Runbook, private launcher/manifests и частичный независимый negative run есть           | Действующие synthetic positive actors, полный запуск новым оператором без скрытых steps               |
| S16 complete staging scenarios | Native mock exact/approximate/unknown, access, PDF, rollback и alerting ранее проверены | Остальные обязательные runbook-сценарии и актуальный scope-bound readback                             |
| S16 safety/access STOP         | Проверенные safety/access отказы и fail-closed реализация есть                          | Явное независимое исполнение негативного STOP gate перед mutation/canary                              |

Production permission и бюджет последней single full generation уже исполнены. Дополнительные paid calls не разрешены. Прошлое решение отложить budgets для отдельного rollout не является доказательством их измерения. E22 нельзя отметить завершённым, пока оставшиеся критерии не выполнены либо владелец явно не изменит область приёмки; перенос отмечается как перенос, а не PASS.

## Независимая сверка оставшегося объёма — 2026-10-31

Read-only аудит подтвердил, что retained staging A/B/C на момент проверки закрыты по canonical access policy: positive operator run останавливается до session issuance. Все 26 indexed evidence files имеют действительные checksums; шесть retained negative probes — PASS. Это не новый positive run, не permission renew grants и не measured p95. Runtime production `cf3a4e6` и parent acceptance относятся только к BUG-50.

Для полного S15–S16 execution одним пакетом нужны решения:

- Scope: полный первоначальный E22 acceptance либо явный перенос невыполненной эксплуатационной qualification в отдельную задачу. Перенос не отмечается как пройденная проверка.
- Measurement contract: latency/attempt/token/currency/stuck limits, sample mix/count/concurrency, сравнение access timing и literal observation window. Реальные samples не заменяют утверждение этих параметров.
- Только synthetic staging: allowlisted A/B access duration/expiry/restore, C остаётся expired; native sessions, fixture correction, generation/age/PDF/export, archived/deletion-pending и purge только согласованных synthetic fixtures. Customer records и реальные платежи вне scope.
- Maintenance/controller: staging-only producer freeze, scheduler/consumers/broker drain, нужные settings/recreation и owned disposable restore DB с cleanup; production не затрагивать.
- Provider boundary: native-mock qualification без платных calls; unmeasured real-provider currency/distributions либо явно перенесены, либо сохраняют открытый gate. Новый paid budget не подразумевается.

В сценарный inventory полного operator run входят questionnaire autosave/resume/review/invalid completion, changed-source/idempotent/stale lineage, active-owner foreign/nonexistent/archived/deletion-pending, equivalent-load access timing, controlled terminal/unknown-outcome mock failures без redispatch, desktop/tablet/mobile/keyboard/a11y/expiry, age/PDF/export/archive/purge и explicit safety/access STOP decision. Исторические proof можно переиспользовать в их границах, но не выдавать за полный свежий независимый запуск.
