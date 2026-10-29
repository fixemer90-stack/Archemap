# S16: Rollout runbook и live evidence

## Статус

🟡 В процессе — staging flow/rollback/alerts и production global release `8869103` подтверждены. Численные budgets отложены владельцем для этого релиза; полное независимое исполнение runbook и оставшаяся формальная приёмка не закрыты. Production выложен, но не выдаётся за процентный canary или новое real-provider generation evidence.

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
- [x] Feature остаётся незакрытой до production/canary evidence по принятой rollout policy. Выполнен разрешённый global release вместо cohort canary; последующий production `3e3ee67` и один real-provider repair проверены. Это закрывает наличие rollout evidence, не остальные budget/operator/BUG-50 quality gates.

## Verification

Текущие review findings, выполненные проверки и незакрытые gates: [единый evidence report](../../reviews/2026-10-25/E22-S12-S16.md). Операционные процедуры: [rollout/rollback runbook](../../deployment/child-report-rollout.md). Локальные PASS не закрывают staging budgets, live telemetry, deployed SHA или canary.

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Staging evidence — 2026-10-25

Подтверждён runtime `06b72c0f06c6f50a1831d407ec1350eb2f9e7bf8`, exact-SHA CI `40211412900` (7/7). Новый сохранённый Self complete с шестью ready sections; Child native-mock flow exact/approximate/unknown прошёл реальные HTTPS, broker/worker, desktop/mobile browser, PDF body/confidence/age parity, export и access checks. Same-owner sibling session mismatch дал private 404 без изменений всех 21 protected table. Отдельная успешная synthetic fixture прошла archive/readback/archived export/purge с сохранением sibling, parent и account/billing tables.

Rollback проверен на этом exact runtime: три легитимные write-операции получили private/no-store 503, reader/PDF и все 21 table row/hash сохранились. Флаг прочитан false, затем восстановлен в `finally` и прочитан true во всех четырёх consumers. Новая full-pair generation после восстановления стала ready. Проверялось прекращение новой admission; in-flight external calls не прерывались. Opaque artifact IDs и результаты без child PII: [staging remediation evidence](../../reviews/2026-10-25/E22-S15-staging-remediation.md).

Исторический snapshot 2026-10-25: верхний staging-smoke checkbox не был закрыт автоматически, поскольку native flow не доказывает каждый шаг полного runbook и budgets. На тот момент production/canary не разрешались и не выполнялись. Позднейший явно разрешённый global production release записан ниже; полный independent operator-run/budgets по-прежнему не доказаны. Accepted staging marker не продвинут.

Инфраструктурный slice `40f3fb1b4aca2f39a48553689feaca893c2ceb2c` прошёл exact-SHA CI `40235132422` (8/8) и отдельный staging rollout без перезапуска приложения/production. Реальный Prometheus → Alertmanager → существующий Telegram drill подтвердил pending, literal `for: 1m`, firing, две завершённые notifier отправки без ошибок и normal resolution после ложного expression; probe затем удалён. Все 17 защищённых container identities сохранились. Source приложения остаётся `06b72c0`, source alerting — `40f3fb1`; эти идентичности не подменяют accepted marker. Подробности и private evidence paths — в том же staging remediation evidence.

## Late-expiry, stale-input и operator readiness — 2026-10-26

На unchanged app `06b72c0` реальные browser/API проверки прошли без API mocks: signed expired JWT после загрузки draft/autosave, confirmation и ready reader дал 401, сохранил загруженное содержимое и отключил записи. В каждом denied-action окне все 21 protected table hashes сохранились. Отдельная synthetic fixture прошла ready → открытая confirmation review → публичная correction birth date → старый questionnaire с новым report key: private/no-store 404, без новых generation/events/artifacts. Прежний принятый ключ вернул исходные generation/report; ранее выпущенный отчёт и parent не изменились. Сравнение начинается после намеренной correction, не скрывает саму смену исходных данных.

Независимый document-only audit `deleg_d9d6d989` нашёл шесть operator blockers. Исправлены dual-auth transport и read-only state helper; уточнены pinned Compose/migration boundary, acquisition/manifests, trigger recipes и backup SOP в [operator procedures](../../deployment/child-operator-procedures.md). Настоящий CLI через public HTTPS/Basic Auth + actor cookie прошёл все восемь enabled cases, включая C-owned resource после expiry; 21 таблица не изменилась во время CLI. Численные budgets/approval record и независимое полное исполнение runbook по-прежнему отсутствуют: эти checkbox не закрыты документацией или запуском автора. Новый helper также реально прочитал и сопоставил полный public application manifest; это read-only equality, не новая restore rehearsal. Private evidence: `/opt/astrotype-staging/evidence/6114db2cdbd2e5f64fec858c8133fd2b054c181a/`.

## Исправление входа из кабинета — 2026-10-27

Текущая runtime identity: API/frontend `562de0a979fcb39ca1e3f662300ce0614201a84b` (CI `40564647794`, 8/8 success); workers — прежний `06b72c0f06c6f50a1831d407ec1350eb2f9e7bf8`, alert infra — прежний `40f3fb1b4aca2f39a48553689feaca893c2ceb2c`. Исправлены жёстко disabled Child в sidebar и coming-soon карточка кабинета; доступность теперь берётся из backend billing metadata, отдельно от paid access. Предыдущие direct-link smoke этот дефект не покрывали.

Реальный desktop/mobile sidebar click без API mocks подтвердил видимый активный Child, правильный Plus CTA и сохранённый 402 для synthetic actor без paid grant. Новый paid generation не выполнялся. Перезапущены только staging API/frontend из off-host built exact-SHA образов: 270 API source files сверены, все 66 public tables/schema сохранились, 17 остальных containers и production/accepted markers не изменились. Provider остаётся mock. Evidence и границы — [entrypoint remediation](../../reviews/2026-10-27/E22-Child-entrypoints.md); private artifacts — `/opt/astrotype-staging/evidence/562de0a979fcb39ca1e3f662300ce0614201a84b/`. Глобальные checkbox S16 выше остаются открытыми по прежним причинам.

## Production global release — 2026-10-28

Владелец явно разрешил production и отложил лимиты: «выкладывай, лимиты решим потом». Разрешение и исключение записаны до переключения. Source `886910321d1efcb189b8a2296dd5c947146e8b4f` прошёл CI `40568791382` (8/8), семь миграций применены до `a8b9c0d1e2f3`, Child включён во всех четырёх backend consumers. Свежий production backup 49 tables / 40 nonempty восстановлен в disposable DB и сопоставлен; 48 non-revision legacy tables сохранили данные в frozen migration window. Source identity 270 Python files проверена в каждом consumer, реальные DeepSeek/model и refinement settings сохранены, public health 200, original Caddy config восстановлен.

Native desktop/mobile sidebar click без API mocks подтвердил production Child и canonical 402 для нового synthetic Free adult. Никаких paid grants/payments/Child records этой fixture и платных тестовых генераций не создавалось. Production имеет отдельные private collector/Prometheus/Alertmanager; real firing/resolved delivery завершил две отправки без ошибок, probe удалён. Семнадцать прочих containers и staging markers сохранились. `.deploy-sha`/`.deploy-release` записаны и прочитаны после smoke.

Это global release по явному разрешению, не процентный canary и не исполнение всего runbook независимым новым оператором. Budgets остаются неизмеренными; checkbox выше не закрываются исключением. Подробные результаты, private evidence и новая operational Compose entrypoint: [production evidence](../../reviews/2026-10-28/E22-production-rollout.md).

## Production repair и independent readback — 2026-10-29

Active release `/opt/astrotype-production/releases/3e3ee67b68e9ea53cb6e467b5596d8a6c75781b9`, CI `40782166066` (8/8), markers/source/image/readiness проверены. Migration delta 0; private 66-table backup/restore и frozen equality PASS, rollback images сохранены. Один разрешённый real-provider full repair создал core v3, 11 ready sections/четыре обоснованных omissions, 35 уникальных claims. Родительский read-only `readback-v2.py` заново подтвердил старые version/hash/109 owned rows, API/browser/PDF proof и paid accounting. Private evidence находится под `/opt/astrotype-production/evidence/3e3ee67b68e9ea53cb6e467b5596d8a6c75781b9/`; observability overlays — под старым `8869103` evidence, images override — под новым.

Это независимый post-deploy readback, **не** полноценное независимое исполнение всего S16 runbook. Open: numeric budgets/workload/window, дополнительные boundary/query-plan/accounting сценарии и negative safety/access STOP execution. Общий контентный verdict не принят: caveat sentence повторяется 26 раз, uncertainty — 18. BUG-50 и Feature не закрыты; [подробный evidence и root cause](../../reviews/2026-10-28/BUG-50-child-content-quality.md).

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
