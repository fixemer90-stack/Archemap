# S14: Reader, dynamic age block и PDF

## Статус

🟡 Реализовано и независимо одобрено (`deleg_e6a8ff8b`); локальные browser/runtime/quality gates зелёные. Публикация и exact-SHA CI ещё не закрыты, production rollout не заявлен.

## Контекст

Reader должен быть narrative-first, показывать progressive deterministic result и использовать тот же persisted presentation contract, что PDF. Возрастной блок нельзя пересчитывать незаметно во время экспорта.

## Что сделать

1. Создать report reader с пятнадцатью sections и progressive states.
2. Показать confidence/technical basis через progressive disclosure, не открывая отчёт raw scores.
3. Отдельно рендерить датированный Current Age block и stale/update state.
4. Создать presentation manifest как единый источник web/PDF.
5. Фиксировать `age_snapshot_id` при PDF generation.

## Затрагиваемые файлы

| Область                                        | Действие          |
| ---------------------------------------------- | ----------------- |
| `frontend/src/app/(dashboard)/reports/child/*` | Изменить/добавить |
| `frontend/src/components/child-report/*`       | Изменить/добавить |
| `backend/app/modules/child/presentation.py`    | Изменить/добавить |
| `backend/app/modules/child/pdf.py`             | Изменить/добавить |
| `frontend/tests/*child-report*`                | Изменить/добавить |

## Критерии приёмки

- [x] Порядок и content web/PDF совпадают.
- [x] PDF содержит core/report/age version metadata.
- [x] Reader полезен в deterministic_ready/narrative_failed.
- [x] Age stale state честно датирован.
- [x] Нет fixed labels/diagnostic language в UI chrome.
- [x] Mobile, print и accessibility verification проходят.

## Verification

Текущие review findings, выполненные проверки и незакрытые gates: [единый evidence report](../../reviews/2026-10-25/E22-S12-S16.md). Операционные процедуры: [rollout/rollback runbook](../../deployment/child-report-rollout.md). Локальные PASS не закрывают staging budgets, live telemetry, deployed SHA или canary.

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
