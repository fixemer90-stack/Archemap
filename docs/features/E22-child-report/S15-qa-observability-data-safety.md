# S15: QA, observability и data safety

## Статус

🟡 В процессе — локальные инструменты и проверки реализованы; staging/production/canary gates остаются открытыми.

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

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
