# S05: Parent Style engine

## Статус

⬜ Не начато

## Контекст

Нужно детерминированно описать естественный стиль взрослого, используя persisted v2 facts, не превращая пол или одно положение карты в parenting label.

## Что сделать

1. Зафиксировать восемь MVP Parent Style dimensions и scoring config.
2. Собирать positive/counter/missing evidence из parent natal facts.
3. Добавить correlated-signal caps, calibration и confidence.
4. Сохранять breakdown, scoring/reference versions и parent chart lineage.
5. Не зависеть от mutable Self narrative.

## Затрагиваемые файлы

| Область                                                     | Действие          |
| ----------------------------------------------------------- | ----------------- |
| `backend/app/modules/child/parent_style.py`                 | Изменить/добавить |
| `backend/app/modules/child/scoring/*`                       | Изменить/добавить |
| `backend/tests/unit/test_child/test_parent_style_engine.py` | Изменить/добавить |
| `backend/app/reference_data/child/*`                        | Изменить/добавить |

## Критерии приёмки

- [ ] Все восемь dimensions воспроизводимы без LLM.
- [ ] Каждый score имеет evidence/counter-evidence/confidence.
- [ ] Нет gender weights и single-factor labels.
- [ ] Correlated facts не раздувают score.
- [ ] Golden fixtures проверяют ranges и low-evidence confidence.
- [ ] Output сохраняется versioned в PostgreSQL.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
