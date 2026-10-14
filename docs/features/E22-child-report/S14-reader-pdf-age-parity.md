# S14: Reader, dynamic age block и PDF

## Статус

⬜ Не начато

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

- [ ] Порядок и content web/PDF совпадают.
- [ ] PDF содержит core/report/age version metadata.
- [ ] Reader полезен в deterministic_ready/narrative_failed.
- [ ] Age stale state честно датирован.
- [ ] Нет fixed labels/diagnostic language в UI chrome.
- [ ] Mobile, print и accessibility verification проходят.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
