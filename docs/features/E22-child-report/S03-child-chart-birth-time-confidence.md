# S03: Child chart и birth-time confidence

## Статус

⬜ Не начато

## Контекст

Расчёт детской карты должен переиспользовать v2 natal engine, но явно ограничивать факты при приблизительном или неизвестном времени. Synthetic defaults нельзя выдавать за точные данные.

## Что сделать

1. Создать child chart adapter поверх v2 chart calculation/persistence.
2. Реализовать `exact|approximate|unknown` policy и versioned exclusions.
3. Для approximate времени оценивать устойчивость факта в заданном окне.
4. Исключать houses/angles/overlays/time-sensitive Moon signals при недостаточной уверенности.
5. При исправлении birth data создавать новую chart lineage без overwrite.

## Затрагиваемые файлы

| Область                                                       | Действие                          |
| ------------------------------------------------------------- | --------------------------------- |
| `backend/app/modules/child/chart_adapter.py`                  | Изменить/добавить                 |
| `backend/app/modules/child/birth_time_policy.py`              | Изменить/добавить                 |
| `backend/app/modules/astrotype_v2/*`                          | reuse, без ослабления v2 contract |
| `backend/tests/unit/test_child/test_birth_time_confidence.py` | Изменить/добавить                 |

## Критерии приёмки

- [ ] Unknown time не создаёт houses, ASC, MC или house synastry.
- [ ] Approximate facts имеют stability evidence и exclusions.
- [ ] Confidence снижается объяснимо, а не случайно.
- [ ] Gender не влияет на chart/scoring.
- [ ] Golden fixtures покрывают exact/approximate/unknown и Moon sign boundary.
- [ ] Birth-data correction сохраняет старую chart/report lineage.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
