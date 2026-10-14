# S08: Questionnaire и Context Resolver

## Статус

⬜ Не начато

## Контекст

Астрология не знает реальную семейную ситуацию. Versioned ответы должны уточнять контекст и противоречия, не переписывая chart-derived scores.

## Что сделать

1. Создать 8–12 общих/age-filtered вопросов MVP и versioned catalog.
2. Реализовать draft, resume, complete и immutable completed answers.
3. Разделить caregiver context, observations, preferences и family constraints.
4. Построить resolver natural strengths/friction/compensation/ambiguities.
5. Оставить extension point для adaptive questions без включения score-driven flow в MVP.

## Затрагиваемые файлы

| Область                                                  | Действие          |
| -------------------------------------------------------- | ----------------- |
| `backend/app/modules/child/questionnaire.py`             | Изменить/добавить |
| `backend/app/modules/child/context_resolver.py`          | Изменить/добавить |
| `backend/app/modules/child/questionnaire_persistence.py` | Изменить/добавить |
| `backend/tests/unit/test_child/test_context_resolver.py` | Изменить/добавить |

## Критерии приёмки

- [ ] Backend определяет age-filtered набор.
- [ ] Completed answers immutable и versioned.
- [ ] Contradictions сохраняются как результат.
- [ ] Answers не меняют natal/interaction scores.
- [ ] Raw answers не уходят напрямую в LLM.
- [ ] Draft одного ребёнка нельзя использовать для другого.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
