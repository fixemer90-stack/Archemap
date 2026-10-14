# S06: Child Needs engine

## Статус

⬜ Не начато

## Контекст

Child Needs должны описывать условия более лёгкого взаимодействия, а не фиксированные traits, способности или диагнозы ребёнка.

## Что сделать

1. Зафиксировать восемь MVP Child Needs dimensions.
2. Использовать только разрешённые child facts из birth-time policy.
3. Добавить age-aware applicability и confidence.
4. Сформировать safe machine labels и пользовательские определения.
5. Запретить API/narrative mapping dimension → fixed child trait.

## Затрагиваемые файлы

| Область                                                    | Действие          |
| ---------------------------------------------------------- | ----------------- |
| `backend/app/modules/child/child_needs.py`                 | Изменить/добавить |
| `backend/app/modules/child/scoring/*`                      | Изменить/добавить |
| `backend/app/reference_data/child/*`                       | Изменить/добавить |
| `backend/tests/unit/test_child/test_child_needs_engine.py` | Изменить/добавить |

## Критерии приёмки

- [ ] Все dimensions имеют score/confidence/evidence/version.
- [ ] Unknown-time exclusions сохраняются downstream.
- [ ] Низкая evidence coverage снижает confidence.
- [ ] Нет diagnosis, ability ranking или binary labels.
- [ ] Age-inapplicable signals не создают рекомендации.
- [ ] Negative wording fixtures проходят.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
