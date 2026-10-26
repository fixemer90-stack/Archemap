# S16: Rollout runbook и live evidence

## Статус

🟡 В процессе — native staging flow, rollback и автоматические Telegram firing/resolved подтверждены; полный runbook acceptance, budgets и production/canary gates остаются открытыми.

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
- [x] Rollback прекращает новую generation admission и сохраняет artifacts; принятая in-flight работа не прерывается.
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

Верхний staging-smoke checkbox не закрыт автоматически: native flow не доказывает каждый шаг полного runbook и полные budget gates. Выполнение новым оператором отдельно не доказано. Production/canary не разрешены и не выполнялись. Accepted staging marker оставлен прежним; native functional PASS не равен принятому rollout.

Инфраструктурный slice `40f3fb1b4aca2f39a48553689feaca893c2ceb2c` прошёл exact-SHA CI `40235132422` (8/8) и отдельный staging rollout без перезапуска приложения/production. Реальный Prometheus → Alertmanager → существующий Telegram drill подтвердил pending, literal `for: 1m`, firing, две завершённые notifier отправки без ошибок и normal resolution после ложного expression; probe затем удалён. Все 17 защищённых container identities сохранились. Source приложения остаётся `06b72c0`, source alerting — `40f3fb1`; эти идентичности не подменяют accepted marker. Подробности и private evidence paths — в том же staging remediation evidence.

## Late-expiry, stale-input и operator readiness — 2026-10-26

На unchanged app `06b72c0` реальные browser/API проверки прошли без API mocks: signed expired JWT после загрузки draft/autosave, confirmation и ready reader дал 401, сохранил загруженное содержимое и отключил записи. В каждом denied-action окне все 21 protected table hashes сохранились. Отдельная synthetic fixture прошла ready → открытая confirmation review → публичная correction birth date → старый questionnaire с новым report key: private/no-store 404, без новых generation/events/artifacts. Прежний принятый ключ вернул исходные generation/report; ранее выпущенный отчёт и parent не изменились. Сравнение начинается после намеренной correction, не скрывает саму смену исходных данных.

Независимый document-only audit `deleg_d9d6d989` нашёл шесть operator blockers. Исправлены dual-auth transport и read-only state helper; уточнены pinned Compose/migration boundary, acquisition/manifests, trigger recipes и backup SOP в [operator procedures](../../deployment/child-operator-procedures.md). Настоящий CLI через public HTTPS/Basic Auth + actor cookie прошёл все восемь enabled cases, включая C-owned resource после expiry; 21 таблица не изменилась во время CLI. Численные budgets/approval record и независимое полное исполнение runbook по-прежнему отсутствуют: эти checkbox не закрыты документацией или запуском автора. Новый helper также реально прочитал и сопоставил полный public application manifest; это read-only equality, не новая restore rehearsal. Private evidence: `/opt/astrotype-staging/evidence/6114db2cdbd2e5f64fec858c8133fd2b054c181a/`.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
