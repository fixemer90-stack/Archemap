# S04: Контрольные вопросы и Profile Resolver

## Статус

⬜ Не начато

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

- [ ] Questionnaire version сохраняется вместе с answers.
- [ ] Обязательные вопросы валидируются до запуска полного отчёта.
- [ ] Capability, motivation, preference и current constraints не смешиваются в одно число.
- [ ] Contradictions сохраняются явно и объяснимо.
- [ ] Resolver полностью детерминирован и тестируется без LLM.
- [ ] Raw free text ограничен, очищен и не становится инструкцией для LLM.
- [ ] Пользователь может вернуться к незавершённому draft.
- [ ] Adaptive questions остаются отдельным post-MVP расширением.
