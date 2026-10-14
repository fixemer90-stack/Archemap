# S10: Modular LLM narrative

## Статус

⬜ Не начато

## Контекст

Narrative должен быть подробным и человечным, но строго ограниченным Guidance Facts, section contract и child-safety policy.

## Что сделать

1. Создать prompt family по секциям report contract.
2. Передавать каждой секции только owned/reference facts.
3. Валидировать structured output, evidence refs и prohibited claims.
4. Реализовать section retry и assembly без повторного deterministic calculation.
5. Версионировать prompt/model/provider и сохранять generation metadata без PII в telemetry.

## Затрагиваемые файлы

| Область                                                    | Действие          |
| ---------------------------------------------------------- | ----------------- |
| `backend/app/modules/child/prompts/*`                      | Изменить/добавить |
| `backend/app/modules/child/narrative.py`                   | Изменить/добавить |
| `backend/app/modules/child/assembly.py`                    | Изменить/добавить |
| `backend/tests/unit/test_child/test_narrative_pipeline.py` | Изменить/добавить |

## Критерии приёмки

- [ ] LLM не получает raw chart и не вычисляет scores.
- [ ] LLM не добавляет новые child facts/recommendations.
- [ ] Каждая section проходит schema/evidence/safety gates.
- [ ] Failed section можно повторить независимо.
- [ ] Mock и real-provider fixtures покрыты.
- [ ] Assembly сохраняет section order и age snapshot reference.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
