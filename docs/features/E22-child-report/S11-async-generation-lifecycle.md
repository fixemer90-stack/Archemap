# S11: Async generation lifecycle

## Статус

⬜ Не начато

## Контекст

Полный pair calculation и modular narrative не должны выполняться в одном HTTP-запросе. Нужен durable lifecycle с полезным deterministic-ready состоянием.

## Что сделать

1. Добавить Celery/task orchestration для pair foundation, facts, sections и assembly.
2. Реализовать атомарные status transitions и generation claim.
3. Публиковать deterministic report до narrative completion.
4. Добавить retry/backoff/timeout и stuck-job reconciliation.
5. Отделить full generation от age-update lifecycle.

## Затрагиваемые файлы

| Область                                                        | Действие          |
| -------------------------------------------------------------- | ----------------- |
| `backend/workers/tasks/child.py`                               | Изменить/добавить |
| `backend/app/modules/child/service.py`                         | Изменить/добавить |
| `backend/app/modules/child/status.py`                          | Изменить/добавить |
| `backend/tests/integration/test_child_generation_lifecycle.py` | Изменить/добавить |

## Критерии приёмки

- [ ] HTTP create быстро возвращает generation ID.
- [ ] Deterministic-ready полезен без LLM.
- [ ] Provider failure ведёт в narrative_failed, а не стирает result.
- [ ] Повторный worker claim не дублирует artifacts/provider calls.
- [ ] Age update не запускает полный pair pipeline.
- [ ] Stuck/retry transitions покрыты integration tests.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
