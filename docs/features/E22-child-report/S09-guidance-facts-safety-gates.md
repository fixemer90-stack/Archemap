# S09: Guidance Facts и child-safety gates

## Статус

⬜ Не начато

## Контекст

Перед LLM нужен ограниченный детерминированный объект рекомендаций и исполняемые guardrails, иначе модель сможет создавать labels, диагнозы и неподтверждённые советы.

## Что сделать

1. Собрать versioned `ChildGuidanceFacts` из resolver/interaction/age artifacts.
2. Определить section ownership и evidence registry.
3. Реализовать pre-LLM completeness/contradiction/confidence gates.
4. Реализовать post-LLM diagnosis/label/fatalism/blame/unsafe-discipline/age checks.
5. Создать negative corpus на запрещённые формулировки.

## Затрагиваемые файлы

| Область                                                    | Действие          |
| ---------------------------------------------------------- | ----------------- |
| `backend/app/modules/child/guidance_facts.py`              | Изменить/добавить |
| `backend/app/modules/child/quality.py`                     | Изменить/добавить |
| `backend/app/modules/child/safety.py`                      | Изменить/добавить |
| `backend/tests/unit/test_child/test_child_safety_gates.py` | Изменить/добавить |

## Критерии приёмки

- [ ] Guidance Facts не содержат raw chart/unrestricted answers.
- [ ] Каждое действие поддержано evidence/context rule.
- [ ] Low confidence требует условной формулировки.
- [ ] Adult-action framing проверяется машинно.
- [ ] Negative corpus блокируется до публикации.
- [ ] Safety failure не уничтожает deterministic artifact.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
