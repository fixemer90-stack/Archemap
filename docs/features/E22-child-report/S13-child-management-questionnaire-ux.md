# S13: Child management и questionnaire UX

## Статус

⬜ Не начато

## Контекст

Пользователь должен явно видеть выбранного ребёнка, качество времени рождения, возрастной контекст и состояние draft, чтобы не создать отчёт на неверных данных.

## Что сделать

1. Создать product page/list для нескольких child records.
2. Реализовать create/edit birth data и caregiver context flow.
3. Объяснить exact/approximate/unknown без принуждения к догадке.
4. Реализовать age-filtered questionnaire, autosave/resume и review before complete.
5. Добавить progress/polling/locked/error states из API contract.

## Затрагиваемые файлы

| Область                                         | Действие          |
| ----------------------------------------------- | ----------------- |
| `frontend/src/app/(dashboard)/products/child/*` | Изменить/добавить |
| `frontend/src/components/child/*`               | Изменить/добавить |
| `frontend/src/lib/api/child.ts`                 | Изменить/добавить |
| `frontend/src/types/child.ts`                   | Изменить/добавить |
| `frontend/tests/*child*`                        | Изменить/добавить |

## Критерии приёмки

- [ ] Любое действие показывает выбранного child record.
- [ ] Unknown time является полноценным UX path.
- [ ] Birth-data edit предупреждает о новой lineage.
- [ ] Draft изолирован между детьми.
- [ ] Keyboard/mobile/accessibility checks проходят.
- [ ] UI не вычисляет age/access/scores самостоятельно.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
