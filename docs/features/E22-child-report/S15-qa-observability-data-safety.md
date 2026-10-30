# S15: QA, observability и data safety

## Статус

🟡 В процессе — staging native-mock flow, application backup/restore, rollback, collector/scrape и автоматические Telegram firing/resolved подтверждены; полные provider budgets остаются открытыми.

## Контекст

Unit tests отдельных формул недостаточны. Нужны сквозные доказательства safety, ownership, multiple-child isolation, backup/restore и отсутствие PII в telemetry.

## Что сделать

1. Собрать golden/boundary/property corpus всех deterministic engines.
2. Добавить negative child-safety и unsupported-advice suites.
3. Проверить migration upgrade/downgrade, backup/restore, export/delete.
4. Добавить metrics/traces для lifecycle без child PII.
5. Провести web/PDF parity, access leakage и multiple-child E2E.

## Затрагиваемые файлы

| Область                                  | Действие          |
| ---------------------------------------- | ----------------- |
| `backend/tests/unit/test_child/*`        | Изменить/добавить |
| `backend/tests/integration/test_child_*` | Изменить/добавить |
| `frontend/tests/*child*`                 | Изменить/добавить |
| `docs/deployment/*child*`                | Изменить/добавить |
| observability dashboards/alerts          | Изменить/добавить |

## Критерии приёмки

- [x] Exact/approximate/unknown и age boundaries покрыты.
- [x] Negative safety corpus блокируется.
- [x] Foreign/locked leakage tests зелёные.
- [x] Локальный synthetic backup/restore: populated history во всех 17 Child tables, schema/row-count/JSON-checksum equality и неизменность источника доказаны; это не application/staging backup.
- [x] Локальные logs/SDK-metrics privacy tests не находят name/DOB/answers/prose; deployed collector/scrape/alert delivery остаются live gate, не доказаны unit tests.
- [ ] Latency/cost/stuck-job budgets измерены на staging.

## Verification

Текущие review findings, выполненные проверки и незакрытые gates: [единый evidence report](../../reviews/2026-10-25/E22-S12-S16.md). Операционные процедуры: [rollout/rollback runbook](../../deployment/child-report-rollout.md). Локальные PASS не закрывают staging budgets, live telemetry, deployed SHA или canary.

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Staging evidence — 2026-10-25

Runtime `06b72c0f06c6f50a1831d407ec1350eb2f9e7bf8`, CI `40211412900`: все 7 jobs success. Реальный staging application dump восстановлен и сопоставлен: 66 tables, 56 nonempty, schema/rows равны, источник не изменён. Native Self сохранён complete (6 ready sections); Child exact/approximate/unknown прошли API→broker→worker→browser/PDF/export с owner/foreign/free/expired и same-owner sibling negative checks. Реальные archive/export/purge отдельной успешной synthetic fixture сохранили sibling, parent report, account и hashes четырёх account/billing tables.

Flag-off drill сохранил reader/PDF и все 21 protected table; три generation mutations дали private 503, затем флаг восстановлен во всех четырёх consumers и full-pair снова ready. Collector/Prometheus действительно получают Child instruments; scrape up. Есть native observation без новых failures/stuck jobs, но это не доказательство real-provider p95/token/currency budgets. Критерий budgets выше остаётся открытым.

Alerting source `40f3fb1b4aca2f39a48553689feaca893c2ceb2c`, exact-SHA CI `40235132422`: все 8 jobs success, включая native promtool/amtool gate. Изолированно запущен private Alertmanager и пересоздан только staging Prometheus; application runtime остался `06b72c0`, 17 защищённых container identities не изменились. Реальный probe прошёл pending → firing после 62.294404 секунды при `for: 1m` → inactive. Native Telegram notifier завершил две отправки (firing/resolved), без failed requests; временное правило удалено и отсутствие прочитано обратно. Два постоянных Child rules загружены и inactive; active Alertmanager — один. Health/Basic Auth/noindex, metrics UI и сохранённые Self/Child повторно прочитаны успешно. Это delivery evidence, не provider-budget evidence.

Подробные opaque IDs, RED/GREEN, независимые reviews и границы acceptance: [staging remediation evidence](../../reviews/2026-10-25/E22-S15-staging-remediation.md). Production/canary не выполнялись; accepted staging marker не продвинут.

## Production и отложенные budgets — 2026-10-28

Production source `886910321d1efcb189b8a2296dd5c947146e8b4f` выложен после явного разрешения владельца и исключения «выкладывай, лимиты решим потом». Это не закрывает budget checkbox: численные p95/token/currency/stuck-job budgets не объявлены измеренными. Сохранён реальный DeepSeek, новых платных тестовых генераций не было. Fresh production backup/restore доказал equality 49 tables / 40 nonempty, frozen migration comparison сохранил данные всех 48 non-revision legacy tables. Отдельные production telemetry/alerts и native Telegram firing/resolved проверены, native Free browser gate сохранил 402. Полный release record и границы: [production evidence](../../reviews/2026-10-28/E22-production-rollout.md).

## Production BUG-50 repair — 2026-10-29

Source `3e3ee67b68e9ea53cb6e467b5596d8a6c75781b9`, exact CI `40782166066` (8/8), новая core version 3: одна полная DeepSeek generation, 11 section calls/по одной попытке, lifecycle 39.120948 s. Persisted/API/native desktop/mobile/PDF readback прошёл, включая независимый родительский readback; 66-table backup/restore и сохранение старых 109 Child rows подтверждены. Это один sample без записанных token/currency totals, не p95 и не закрытие budget checkbox. Четыре обоснованных omissions дают `limited`; стандартные caveat/uncertainty sentences всё ещё повторяются. Подробности и remaining gates: [BUG-50 evidence](../../reviews/2026-10-28/BUG-50-child-content-quality.md).

## BUG-50 V4 accepted sample — 2026-10-31

Production `cf3a4e6`, exact CI `41133238682` (8/8): одна разрешённая full DeepSeek generation core version 5, **11 ready / 0 failed / 0 missing**, четыре justified omissions; все26 dimensions/refs и native desktop/mobile/PDF parity независимо проверены. **11 HTTP attempts**, по одной на applicable section; usage **13,899 prompt + 6,132 completion = 20,031 tokens**. Это конкретный measured sample, не currency receipt, статистический p95, repeat-run reliability или утверждённый numeric budget. Checkbox budgets остаётся открыт. Fresh **66-table** backup/restore, **264 historical Child rows**, **49 non-Child tables**, **17 protected containers** и cleanup подтверждены; новые paid calls не разрешены. [Финальная BUG-50 приёмка](../../reviews/2026-10-28/BUG-50-child-content-quality.md) не закрывает S15/E22.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
