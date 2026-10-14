# S04: Age Resolver и age snapshots

## Статус

⬜ Не начато

## Контекст

Возраст влияет на вопросы, приоритет dimensions, примеры и рекомендации, но не должен молча переписывать исторический core report.

## Что сделать

1. Реализовать календарный exact-age resolver и семь versioned age stages.
2. Хранить `as_of_date`, years/months/days, stage и rules version.
3. Определить stale policy для age guidance.
4. Создавать immutable age snapshot и отдельный guidance artifact.
5. Зафиксировать один snapshot на время web/PDF rendering.

## Затрагиваемые файлы

| Область                                                 | Действие          |
| ------------------------------------------------------- | ----------------- |
| `backend/app/modules/child/age_resolver.py`             | Изменить/добавить |
| `backend/app/modules/child/age_guidance.py`             | Изменить/добавить |
| `backend/tests/unit/test_child/test_age_resolver.py`    | Изменить/добавить |
| `backend/tests/integration/test_child_age_snapshots.py` | Изменить/добавить |

## Критерии приёмки

- [ ] Future DOB отклоняется.
- [ ] Leap-day, month-end и timezone boundaries покрыты.
- [ ] Возраст не принимается от клиента как source of truth.
- [ ] Core report не меняется после age update.
- [ ] Повторный update на те же inputs idempotent.
- [ ] Web и PDF получают одинаковый pinned snapshot.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
