# Story E11.S04: Prompt contract self_story_v1

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Prompt должен быть версионированным контрактом, а не строкой внутри service. Он обязан фиксировать роль LLM как narrative renderer, product boundary Self vs Career, tone, evidence discipline и safety-контур сексуальности.

## Что сделать

1. Создать prompt directory для narrative prompts.
2. Добавить `self_story_v1.md` с system role, product boundary, tone rules, evidence discipline, sexuality safety, output schema instruction.
3. Добавить prompt loader/builder, который подставляет serialized `NarrativeInput`.
4. Зафиксировать prompt version constant `self_story_v1`.
5. Добавить tests, что prompt содержит обязательные guardrails.
6. Добавить docs/comment о процедуре создания `self_story_v2` при изменении структуры/тона/boundaries.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `backend/app/modules/report_narratives/prompts/self_story_v1.md` | Новый prompt contract |
| `backend/app/modules/report_narratives/prompts.py` | Prompt loader/builder |
| `backend/app/modules/report_narratives/service.py` | Использовать prompt version constant позже |
| `backend/tests/unit/test_report_narratives/test_prompts.py` | Guardrail tests |

## Критерии приёмки

- [ ] Prompt явно говорит: LLM не рассчитывает астрологию/соционику и не добавляет новые факты.
- [ ] Prompt запрещает фатализм, диагнозы, мистический туман, обвиняющий тон.
- [ ] Self boundary запрещает список профессий, деньги, карьерный план и управленческий профиль.
- [ ] Career CTA обязателен для Self output.
- [ ] Sexuality section описывает стиль близости неграфично и только для взрослых пользователей.
- [ ] Prompt требует JSON по `SelfNarrative`, не Markdown.
- [ ] Tests падают, если обязательные guardrails удалены.
