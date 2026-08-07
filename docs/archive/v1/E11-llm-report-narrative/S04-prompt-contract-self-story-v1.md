# Story E11.S04: Prompt contract self_story_v1

**Feature:** [LLM Report Narrative](Archemap/docs/features/v1/E11-llm-report-narrative/FEATURE.md)
**Статус:** ✅ Готово

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
| `backend/app/modules/report_narratives/__init__.py` | Экспорт prompt APIs |
| `backend/tests/unit/test_report_narratives/test_prompts.py` | Guardrail tests |

## Критерии приёмки

- [x] Prompt явно говорит: LLM не рассчитывает астрологию/соционику и не добавляет новые факты.
- [x] Prompt запрещает фатализм, диагнозы, мистический туман, обвиняющий тон.
- [x] Self boundary запрещает список профессий, деньги, карьерный план и управленческий профиль.
- [x] Career CTA обязателен для Self output.
- [x] Sexuality section описывает стиль близости неграфично и только для взрослых пользователей.
- [x] Prompt требует JSON по `SelfNarrative`, не Markdown.
- [x] Tests падают, если обязательные guardrails удалены.

## Реализация

Добавлены:

- `backend/app/modules/report_narratives/prompts/self_story_v1.md` — версионированный prompt-контракт `self_story_v1`
- `backend/app/modules/report_narratives/prompts.py` — `SELF_STORY_PROMPT_VERSION`, `load_prompt_template(...)`, `build_self_story_prompt(...)`
- `backend/app/modules/report_narratives/__init__.py` — экспорт prompt utilities
- `backend/tests/unit/test_report_narratives/test_prompts.py` — unit tests на guardrails и prompt builder

Что зафиксировано в prompt-контракте:

- LLM — narrative renderer, а не источник истины
- нельзя рассчитывать астрологию, соционику, архетипы и confidence
- нельзя добавлять новые факты, аспекты, дома, типы и диагнозы
- output должен быть только JSON по схеме `SelfNarrative`, без Markdown
- Self boundary запрещает профессии, деньги, карьерный план, управленческий профиль и career deep dive
- `career_cta` обязателен
- sexuality section обязательна, но описывается неграфично и только для взрослых пользователей
- при изменении тона/структуры/boundaries/safety нужно создавать новую версию prompt-а, например `self_story_v2`

## Верификация

Проверено в backend container:

```bash
cd /app
python -m pytest tests/unit/test_report_narratives/test_prompts.py -q
python -m ruff check app/modules/report_narratives tests/unit/test_report_narratives
python -m ruff format --check app/modules/report_narratives tests/unit/test_report_narratives
python -m mypy app/modules/report_narratives tests/unit/test_report_narratives
python -m pytest tests/unit/test_report_narratives -q
```
