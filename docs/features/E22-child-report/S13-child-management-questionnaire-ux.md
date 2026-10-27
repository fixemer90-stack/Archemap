# S13: Child management и questionnaire UX

## Статус

✅ Завершено. Пользовательский вход исправлен и выложен на staging 2026-10-27: API/frontend source `562de0a979fcb39ca1e3f662300ce0614201a84b`, CI `40564647794` — 8/8 success. Native desktop/mobile sidebar click-through проверен без API mocks; 83 browser tests PASS / 1 existing skip. Доступность продукта отделена от paid entitlement: без него карточка показывает Plus CTA, Child API сохраняет 402. Предыдущие management/questionnaire проверки остаются доказанными. [Remediation/evidence](../../reviews/2026-10-27/E22-Child-entrypoints.md). Production rollout не заявлен.

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

- [x] Любое действие показывает выбранного child record.
- [x] Unknown time является полноценным UX path.
- [x] Birth-data edit предупреждает о новой lineage.
- [x] Draft изолирован между детьми.
- [x] Keyboard/mobile/accessibility checks проходят.
- [x] UI не вычисляет age/access/scores самостоятельно.
- [x] При server-owned Child availability `true` раздел доступен из desktop/mobile меню и карточки кабинета; paid gate сохраняется, false/legacy/failed metadata не включают продукт.

## Verification

Текущие review findings, выполненные проверки и незакрытые gates: [единый evidence report](../../reviews/2026-10-25/E22-S12-S16.md). Операционные процедуры: [rollout/rollback runbook](../../deployment/child-report-rollout.md). Локальные PASS не закрывают staging budgets, live telemetry, deployed SHA или canary.

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
