# S05: Career archetypes и рабочая среда

## Статус

✅ Завершено

## Контекст

Dimensions должны превращаться в понятные, но не жёсткие профессиональные модели: несколько архетипов и параметры среды. Один «тип» создаёт ложную определённость.

## Что сделать

1. Создать versioned archetype catalog и matching weights.
2. Возвращать Top-3, score, confidence, positive evidence и ограничения каждого архетипа.
3. Рассчитать организационные оси среды и оси характера занятости: practice/abstract, conceptual/hands-on, behind-scenes/audience-stage, one-off/flow, client/system.
4. Сформировать preferred-environment conditions.
5. Сформировать anti-environment как условия риска, а не запреты.
6. Учитывать Profile Resolver: например, высокий Leadership не равен people management.

## Формулировочный контракт

Плохо: «Вам нельзя работать в корпорации».

Хорошо: «В крупной организации вам особенно важны понятная зона ответственности и возможность влиять на решения внутри неё».

## Критерии приёмки

- [x] Возвращаются Top-3, а не один обязательный архетип.
- [x] Archetype result имеет evidence/confidence и scoring version.
- [x] Environment axes детерминированы и нормализованы.
- [x] Anti-environment формулируется условно, без категорических запретов.
- [x] Contradictions/preferences Profile Resolver влияют предсказуемо и тестируемо.
- [x] Нет прямого planet → archetype mapping.
- [x] Golden tests покрывают минимум expert leader, people manager и autonomous specialist cases.

## Реализация и evidence

- `backend/app/modules/career/archetype_engine.py` — `career-archetypes-2`: versioned multi-dimension catalog, deterministic Top-3, прежние ключи и новые `maker`, `performer`, `practitioner`, `caregiver_service` с preference-aware modifiers.
- `backend/app/modules/career/environment_engine.py` — `career-environment-2`: 15 normalized axes, включая `practical_abstract`, `conceptual_hands_on`, `behind_scenes_audience_stage`, `one_off_flow`, `client_system`; preferred conditions и условные risk conditions без запретов.
- `backend/tests/unit/test_career/test_archetype_environment.py` — прежние golden cases, точный состав/полярность 15 осей, practical/audience preferences и persistence contracts.
- `uv run pytest tests/unit/test_career/test_archetype_environment.py -q` → `7 passed`.
