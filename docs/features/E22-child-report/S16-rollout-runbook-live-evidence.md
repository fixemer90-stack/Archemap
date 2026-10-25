# S16: Rollout runbook и live evidence

## Статус

🟡 В процессе — native staging flow и rollback подтверждены; полный runbook acceptance, alert/budget и production/canary gates остаются открытыми.

## Контекст

Фичу с данными несовершеннолетних нельзя включать только по unit/CI evidence. Нужны точный runbook, stage smoke, canary, rollback и зафиксированные live artifacts.

## Что сделать

1. Подготовить preflight, deploy, feature-flag, smoke, canary и rollback steps.
2. Указать auth/profile/child/report IDs acquisition без публикации PII.
3. Проверить exact и unknown birth time end-to-end.
4. Проверить two-child isolation, locked/foreign access, provider failure и PDF.
5. Зафиксировать deployed SHA, timestamps, metrics, artifact IDs и rollback result.

## Затрагиваемые файлы

| Область                                                               | Действие          |
| --------------------------------------------------------------------- | ----------------- |
| `docs/deployment/child-report-rollout.md`                             | Изменить/добавить |
| `docs/features/E22-child-report/S16-rollout-runbook-live-evidence.md` | Изменить/добавить |
| CI/staging smoke scripts                                              | Изменить/добавить |
| feature flag and observability config                                 | Изменить/добавить |

## Критерии приёмки

- [ ] Runbook исполним новым оператором без скрытых шагов.
- [ ] Staging smoke покрывает все обязательные сценарии.
- [ ] Canary не начинается при safety/access failures.
- [x] Rollback прекращает generation и сохраняет artifacts.
- [x] Live evidence содержит exact SHA/IDs/results без child PII.
- [ ] Feature остаётся незакрытой до production/canary evidence по принятой rollout policy.

## Verification

Текущие review findings, выполненные проверки и незакрытые gates: [единый evidence report](../../reviews/2026-10-25/E22-S12-S16.md). Операционные процедуры: [rollout/rollback runbook](../../deployment/child-report-rollout.md). Локальные PASS не закрывают staging budgets, live telemetry, deployed SHA или canary.

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Staging evidence — 2026-10-25

Подтверждён runtime `06b72c0f06c6f50a1831d407ec1350eb2f9e7bf8`, exact-SHA CI `40211412900` (7/7). Новый сохранённый Self complete с шестью ready sections; Child native-mock flow exact/approximate/unknown прошёл реальные HTTPS, broker/worker, desktop/mobile browser, PDF body/confidence/age parity, export и access checks. Same-owner sibling session mismatch дал private 404 без изменений всех 21 protected table. Отдельная успешная synthetic fixture прошла archive/readback/archived export/purge с сохранением sibling, parent и account/billing tables.

Rollback проверен на этом exact runtime: три легитимные write-операции получили private/no-store 503, reader/PDF и все 21 table row/hash сохранились. Флаг прочитан false, затем восстановлен в `finally` и прочитан true во всех четырёх consumers. Новая full-pair generation после восстановления стала ready. Проверялось прекращение новой admission; in-flight external calls не прерывались. Opaque artifact IDs и результаты без child PII: [staging remediation evidence](../../reviews/2026-10-25/E22-S15-staging-remediation.md).

Верхний staging-smoke checkbox не закрыт автоматически: native flow не доказывает каждый шаг полного runbook, например late-expiry UI/stale-input matrices и полные budget/alert-delivery gates. Выполнение новым оператором отдельно не доказано. Alert rules/active Alertmanagers для Child отсутствуют; production/canary не разрешены и не выполнялись. Accepted staging marker оставлен прежним; native functional PASS не равен принятому rollout.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
