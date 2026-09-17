# S04: Контрольные вопросы и Profile Resolver

## Статус

✅ Завершено

## Контекст

Натальная карта не знает текущую профессию, опыт, карьерную стадию, цели, отношение к риску и желание управлять людьми. Ответы не должны подменять chart score, но должны уточнять применение потенциала.

## Что сделать

1. Создать versioned банк 8–12 MVP-вопросов.
2. Покрыть leadership/people management, autonomy, risk, expert/manager/entrepreneur preference, current context, experience и change goal.
3. Создать questionnaire session с draft/completed state и idempotent submit.
4. Реализовать Profile Resolver, который сопоставляет dimensions и answers.
5. Выделять `confirmed_traits`, `contradictions`, `preferences`, `context_constraints`, `unresolved_ambiguities`.
6. Не понижать детерминированный score только потому, что пользователь не хочет применять качество; хранить capability и preference отдельно.
7. Подготовить extension point для adaptive questions после MVP.

## Пример разрешения

```text
high leadership score
+ low people-management motivation
+ expert-track preference
→ expert leadership / architect / lead specialist scenarios
```

Это не «ошибка пользователя» и не причина проигнорировать его ответ.

## Критерии приёмки

- [x] Questionnaire version сохраняется вместе с answers.
- [x] Обязательные вопросы валидируются до запуска полного отчёта.
- [x] Capability, motivation, preference и current constraints не смешиваются в одно число.
- [x] Contradictions сохраняются явно и объяснимо.
- [x] Resolver полностью детерминирован и тестируется без LLM.
- [x] Raw free text ограничен, очищен и не становится инструкцией для LLM.
- [x] Пользователь может вернуться к незавершённому draft.
- [x] Adaptive questions остаются отдельным post-MVP расширением.

## Реализация и evidence

- `backend/app/modules/career/questionnaire.py` — versioned 10-question bank, draft/completed DTO, bounded sanitization, answer hash и idempotent completion.
- `backend/app/modules/career/profile_resolver.py` — deterministic capability/preference resolver с explicit contradictions и без raw free text в output.
- `backend/app/modules/career/questionnaire_persistence.py` — FK-safe ordered persistence parent → answers/resolution.
- `backend/app/modules/career/repository.py` — чтение существующего draft и его answers.
- `backend/alembic/versions/f5a6b7c8d9e0_add_career_questionnaire_idempotency.py` — additive completion idempotency lineage.
- `backend/tests/unit/test_career/test_questionnaire_resolver.py` — обязательность, draft, sanitization, contradiction, idempotency, persistence order и adaptive-extension contracts.
- Local PostgreSQL smoke: migration upgrade/downgrade/upgrade до `f5a6b7c8d9e0`; completed session и `10` answers восстановлены из DB; smoke rows удалены.
- Backup перед migration: `backend/backups/pre-e19-s04-20260917T045654Z.dump`.
