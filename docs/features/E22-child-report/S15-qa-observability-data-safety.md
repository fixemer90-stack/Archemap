# S15: QA, observability и data safety

## Статус

⬜ Не начато

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

- [ ] Exact/approximate/unknown и age boundaries покрыты.
- [ ] Negative safety corpus блокируется.
- [ ] Foreign/locked leakage tests зелёные.
- [ ] Backup/restore и row-count/checksum доказаны.
- [ ] Logs/metrics scan не находит name/DOB/answers/prose.
- [ ] Latency/cost/stuck-job budgets измерены на staging.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
