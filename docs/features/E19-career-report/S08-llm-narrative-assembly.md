# S08: Modular LLM narrative и assembly

## Статус

⬜ Не начато

## Контекст

LLM отвечает только за язык и объяснение уже рассчитанной профессиональной модели. Один большой prompt повышает риск повторов, generic prose и самовольных профессий.

## Что сделать

1. Создать schema-backed prompt contract для каждой MVP-секции.
2. Передавать секции только owned facts + bounded references.
3. Генерировать секции независимо/параллельно через текущий staged LLM runtime.
4. Сохранять provider/model/prompt version, input hash, status, payload и безопасную ошибку.
5. Валидировать ответы на evidence coverage, profession prescription, contradiction loss, duplication и запрещённые гарантии.
6. Собрать report deterministic-first: summary/calculation доступен до завершения всех narratives.
7. Поддержать section retry без пересчёта карты/dimensions/questions.
8. Сделать mock/fallback payload содержательным и явно отличимым в диагностике, но не техническом UI.

## Секции MVP

- professional_summary;
- work_style;
- strengths;
- decision_making;
- leadership_and_influence;
- optimal_environment;
- risk_environment;
- career_archetypes;
- role_families;
- career_paths.

## Запреты для LLM

- Не вычислять scores/confidence/matches.
- Не добавлять роль, профессию или path, отсутствующие в curated facts.
- Не превращать астрологический фактор в прямое карьерное назначение.
- Не давать обещаний дохода/успеха и не использовать диагностический язык.
- Не игнорировать ответы пользователя или contradictions.

## Критерии приёмки

- [ ] Один bounded запрос соответствует одной section contract.
- [ ] Payload проходит Pydantic/schema validation.
- [ ] Regenerate section не меняет deterministic artifacts.
- [ ] Partial/complete/failure statuses persisted и доступны API.
- [ ] Assembler не добавляет новые карьерные факты.
- [ ] Duplicate/generic/overclaim/profession-prescription validators имеют RED/GREEN tests.
- [ ] Mock и реальный provider проходят один output contract.
- [ ] Provider failure сохраняет deterministic-ready отчёт.
