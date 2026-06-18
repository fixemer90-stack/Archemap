# S01 — Dominants and Inner Mechanism Contract

Статус: ⬜ Не начато
Эпик: `E13-report-depth-improvements`

## Контекст

Отчёт сейчас умеет показать отдельные факты карты, но не собирает их в ясную иерархию: что реально доминирует и как это превращается во внутренний механизм личности.

Пример целевого качества:

```text
Ключевые доминанты карты
1. Земля 53% — основной способ адаптации: практичность, проверка реальностью, устойчивые конструкции.
2. Меркурианско-девий акцент — анализ, детализация, исправление ошибок, систематизация.
3. Козерог во 2 доме — ресурсы, ценность, контроль, долгосрочная безопасность.
4. 9–10–11 дома — знание, профессия, общественные системы.
5. Луна напряжена с Сатурном/Нептуном — эмоциональная сдержанность и трудность доверять мягким ощущениям.
```

## Что сделать

1. Расширить deterministic narrative input:
   - dominant elements/modalities;
   - leading planet/sign/house clusters;
   - high-emphasis houses;
   - strongest repeated chart motifs;
   - key tensions that affect the psychological mechanism.
2. Добавить structured DTO для:
   - `dominants[]`;
   - `inner_mechanism.steps[]`.
3. Обновить prompt contract так, чтобы LLM объяснял механизм, а не повторял “вы практичны/структурны”.
4. Добавить deterministic fallback, который строит базовый mechanism без LLM.
5. Добавить validator:
   - все dominants имеют evidence refs;
   - mechanism содержит 3–5 шагов;
   - нет unsupported claims вне `NarrativeInput`.

## Затрагиваемые файлы

| Файл | Изменение |
|---|---|
| `backend/app/modules/report_narratives/schemas.py` | DTO для dominants/mechanism |
| `backend/app/modules/report_narratives/input_builder.py` | Подготовка evidence-backed доминант |
| `backend/app/modules/report_narratives/prompts/self_story_v2.md` | Новый prompt contract |
| `backend/app/modules/report_narratives/validators.py` | Проверки evidence refs и структуры |
| `backend/app/modules/report_narratives/fallback.py` | Fallback dominants/mechanism |
| `backend/tests/unit/test_report_narratives/` | Контрактные тесты |

## Критерии приёмки

- [ ] В `NarrativeInput` есть достаточные данные для доминант и внутреннего механизма.
- [ ] Self narrative содержит обязательный блок `dominants`.
- [ ] Self narrative содержит обязательный блок `inner_mechanism` с 3–5 шагами.
- [ ] Каждый пункт доминант ссылается на известные evidence ids.
- [ ] Validator отклоняет доминанту без evidence refs.
- [ ] Fallback narrative не подставляет выдуманные факты.
- [ ] Tests проходят в Docker backend.

## Проверка

```bash
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives -q'
```
