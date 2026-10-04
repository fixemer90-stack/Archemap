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

- `backend/app/modules/career/role_matching.py` — `career-role-catalog-2` из 17 role families, multi-signal scoring, фиксированные пороги, confidence, reasons, tensions, requirements и русскоязычные условные profession examples.
- `backend/app/modules/career/career_paths.py` — `career-path-graph-2`, 2–3 preference-sensitive path, graph coverage всех catalog keys и explicit archetypal limitations при неполном контексте.
- `backend/tests/unit/test_career/test_role_matching_paths.py` — catalog/category, occupational coverage, русские примеры, graph closure, explainability, low-evidence, preference-sensitive path и persistence contracts.
- `uv run pytest tests/unit/test_career/test_role_matching_paths.py -q` → `9 passed`.

## Закрытие дизайн-дефекта occupational coverage

Дефект, зафиксированный 2026-10-01, закрыт локально 2026-10-04:

- `career-role-catalog-2` содержит 17 семейств: прежние девять и `visual_arts`, `word_and_media`, `performing_arts`, `craft_and_manual_work`, `practical_technology`, `care_and_service`, `land_and_nature`, `sales_and_field_work`;
- у каждого семейства 2–3 примера профессий на русском языке;
- `career-path-graph-2` содержит путь для каждого ключа каталога, а публичная сборка путей не обращается к графу через небезопасный индекс;
- `career-environment-2` добавляет capability-derived оси `practical_abstract`, `conceptual_hands_on`, `behind_scenes_audience_stage`, `one_off_flow`, `client_system` с зафиксированной полярностью;
- `career-archetypes-2` добавляет `maker`, `performer`, `practitioner`, `caregiver_service` и preference-aware boosts;
- `career-q-2` добавляет пять необязательных enum-предпочтений; для существующего completed q1 создаётся editable q2 draft с переносом совместимых ответов, поэтому пользователь может сохранить новые preferences без изменения исторической q1-сессии; resolver `career-resolver-2` публикует только namespaced preference keys, frontend даёт всем пяти вопросам русские labels и choices;
- `career_interpretation_facts_v2` / `career-facts-curation-2` передают очищенные `current_activity`, `change_goal`, `current_constraints` как reference facts только для `role_families` и `career_paths`; `career_section_render_input_v2` помечает их обязательными ссылками, validator отвергает секцию без context citation, а `career-segment-prompt-6` запрещает офисно-ИТ fallback и трактует пользовательский текст только как данные, а не инструкции;
- `career_report_presentation_v2` использует одинаковую русскую карту названий семейств в backend и frontend; persisted v1 payload определяется по catalog/facts version и сохраняет `career_report_presentation_v1`, прежние title/examples и PDF-семантику.

Границы релиза:

- схема БД и миграции не добавлялись: существующий versioned session contract допускает отдельные q1/q2 строки; профиль переключается на q2 до новой генерации;
- narrative regeneration старого отчёта сохраняет v1 deterministic payload и валидирует profession examples по `career-role-catalog-1`;
- ранее созданные отчёты не пересчитываются; reader/PDF распознают v1 persisted payload и применяют v1 presentation semantics, не смешивая старые английские examples с новыми русскими labels;
- live-provider smoke в этот slice не выполнялся и не заявляется.

Локальное evidence после реализации:

- RED: focused Career набор — `27 failed, 21 passed`, ожидаемые причины: отсутствующие новые семейства/оси/enum-поля/context facts/русские presentation labels;
- GREEN: `uv run pytest tests/unit/test_career -q` — `98 passed, 1 warning`;
- `node scripts/check-career-report-parity.mjs` — `Career report web/PDF semantic parity checks passed`;
- `node scripts/check-career-product-ux.mjs` — `Career product UX contract checks passed`;
- exact frontend Prettier и `npx tsc --noEmit --pretty false` — успешно;
- финальные ruff/mypy/docs checks перечислены в разделе 7 аудита.
