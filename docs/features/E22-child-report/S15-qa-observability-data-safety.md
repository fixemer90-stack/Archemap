# S15: QA, observability и data safety

## Статус

🟡 В процессе — staging native-mock flow, application backup/restore, rollback и collector/scrape подтверждены; alert delivery и полные provider budgets остаются открытыми.

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

Flag-off drill сохранил reader/PDF и все 21 protected table; три generation mutations дали private 503, затем флаг восстановлен во всех четырёх consumers и full-pair снова ready. Collector/Prometheus действительно получают Child instruments; scrape up. Есть native observation без новых failures/stuck jobs, но это не доказательство real-provider p95/token/currency budgets. Child alert rules и active Alertmanagers отсутствуют: firing/delivery/resolution не доказаны. Критерий budgets выше остаётся открытым.

Подробные opaque IDs, RED/GREEN, независимые reviews и границы acceptance: [staging remediation evidence](../../reviews/2026-10-25/E22-S15-staging-remediation.md). Production/canary не выполнялись; accepted staging marker не продвинут.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
