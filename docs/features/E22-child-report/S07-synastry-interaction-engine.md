# S07: Synastry и Interaction engine

## Статус

⬜ Не начато

## Контекст

Главный deterministic слой должен объединять Parent Style, Child Needs и pair synastry, объясняя natural matches и friction без вредного compatibility score.

## Что сделать

1. Рассчитать разрешённые cross-chart aspects и overlays согласно confidence обоих charts.
2. Построить восемь MVP Interaction Dimensions.
3. Сохранять pair evidence, contribution, direction, caps и version.
4. Особо ограничить Saturn/pressure interpretations.
5. Сформировать patterns natural_match/moderate_tension/high_attention без verdict о совместимости.

## Затрагиваемые файлы

| Область                                                    | Действие          |
| ---------------------------------------------------------- | ----------------- |
| `backend/app/modules/child/synastry.py`                    | Изменить/добавить |
| `backend/app/modules/child/interaction.py`                 | Изменить/добавить |
| `backend/app/reference_data/child/*`                       | Изменить/добавить |
| `backend/tests/unit/test_child/test_interaction_engine.py` | Изменить/добавить |

## Критерии приёмки

- [ ] Нет общего compatibility percentage.
- [ ] House overlays отсутствуют при ненадёжном времени.
- [ ] Каждый interaction score multi-signal и evidence-backed.
- [ ] Saturn fixtures не создают blame/fatalism.
- [ ] Correlated evidence capped.
- [ ] Pair A/B и A/C не смешивают evidence/cache.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
