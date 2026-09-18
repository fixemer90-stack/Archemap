# S06: Role matching и карьерные траектории

## Статус

✅ Завершено

## Контекст

Отчёт должен идти от профессиональной механики к классам ролей и только затем к примерам профессий. Рекомендация конкретной должности без контекста опыта и рынка недостоверна.

## Что сделать

1. Создать versioned catalog role families: Architecture, Product, Strategy, Analytics, Consulting, Operations, Research, Management, Entrepreneurship и другие согласованные MVP-группы.
2. Определить dimension/environment/preference weights и minimum evidence rules.
3. Рассчитывать match score, confidence, reasons, tensions и context requirements.
4. Разделить результаты на `strong_match`, `possible_match`, `context_dependent`.
5. Примеры профессий привязывать к role family как иллюстрации, а не назначения.
6. Создать versioned career-path graph с переходами и prerequisites.
7. Строить 2–3 траектории из текущего контекста пользователя; без current context показывать archetypal paths с явной оговоркой.

## Ограничение формулировки

Запрещено: «Вам нужно стать архитектором».

Допустимо: «Роли, связанные с проектированием сложных систем, могут хорошо соответствовать профилю; Solution Architect — один из примеров».

## Критерии приёмки

- [x] Role match использует несколько dimensions, environment и preferences.
- [x] Каждый результат имеет reasons, tensions, confidence и catalog version.
- [x] Профессии не появляются раньше role families.
- [x] Категории strong/possible/context-dependent имеют фиксированные пороги.
- [x] Career path состоит из versioned graph edges, а не LLM-выдумки.
- [x] При отсутствии опыта/цели ограничения явно отражены.
- [x] Никакая роль не обещает доход, найм или гарантированный успех.
- [x] Golden tests проверяют несколько разных путей при одинаковом chart score и разных preferences.

## Реализация и evidence

- `backend/app/modules/career/role_matching.py` — versioned catalog из девяти role families, multi-signal scoring, фиксированные пороги, confidence, reasons, tensions, requirements и условные profession examples.
- `backend/app/modules/career/career_paths.py` — versioned deterministic graph, 2–3 preference-sensitive path и explicit archetypal limitations при неполном контексте.
- `backend/tests/unit/test_career/test_role_matching_paths.py` — catalog/category, explainability, low-evidence, preference-sensitive path и persistence contracts.
- `uv run pytest tests/unit/test_career/test_role_matching_paths.py -q` → `6 passed`.
