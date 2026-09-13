# S05: Career archetypes и рабочая среда

## Статус

⬜ Не начато

## Контекст

Dimensions должны превращаться в понятные, но не жёсткие профессиональные модели: несколько архетипов и параметры среды. Один «тип» создаёт ложную определённость.

## Что сделать

1. Создать versioned archetype catalog и matching weights.
2. Возвращать Top-3, score, confidence, positive evidence и ограничения каждого архетипа.
3. Рассчитать оси среды: structured/flexible, stable/dynamic, individual/collaborative, expert/managerial, operational/strategic, predictable/experimental, supportive/competitive, small/large, local/global, execution/ownership.
4. Сформировать preferred-environment conditions.
5. Сформировать anti-environment как условия риска, а не запреты.
6. Учитывать Profile Resolver: например, высокий Leadership не равен people management.

## Формулировочный контракт

Плохо: «Вам нельзя работать в корпорации».

Хорошо: «В крупной организации вам особенно важны понятная зона ответственности и возможность влиять на решения внутри неё».

## Критерии приёмки

- [ ] Возвращаются Top-3, а не один обязательный архетип.
- [ ] Archetype result имеет evidence/confidence и scoring version.
- [ ] Environment axes детерминированы и нормализованы.
- [ ] Anti-environment формулируется условно, без категорических запретов.
- [ ] Contradictions/preferences Profile Resolver влияют предсказуемо и тестируемо.
- [ ] Нет прямого planet → archetype mapping.
- [ ] Golden tests покрывают минимум expert leader, people manager и autonomous specialist cases.
