# S04 — Contradictions, Failures, and Maturity Levels

Статус: ⬜ Не начато
Эпик: `E13-report-depth-improvements`

## Контекст

Отчёт становится ценнее, когда показывает не только сильные стороны, но и центральные внутренние противоречия, сбои системы и зрелые формы проявления.

## Целевые блоки

### Главные внутренние противоречия

- Деталь против горизонта.
- Компетентность против признания.
- Контроль против доверия.
- Рациональность против эмоциональной зависимости от среды.

### Где система даёт сбой

- Перегрузка анализом.
- Отложенное действие.
- Эмоциональная самозаморозка.
- Сложность с признанием своей ценности.

### Уровни зрелости

```text
Низкий уровень: перфекционизм, тревога за результат, зависимость от внешней оценки.
Средний уровень: устойчивые системы, надёжность, улучшение процессов.
Высокий уровень: собственные методологии, передача знаний, зрелое лидерство.
```

## Что сделать

1. Добавить schemas:
   - `ContradictionInsight`;
   - `FailureMode`;
   - `MaturityLevels`.
2. Научить input builder выделять tension pairs:
   - sign/house contradiction;
   - element imbalance;
   - hard aspects;
   - repeated house/resource themes;
   - socionics/function contradictions if evidence exists.
3. Обновить prompt:
   - не делать фатальных прогнозов;
   - не использовать медицинскую/диагностическую лексику;
   - каждый конфликт должен иметь mature form.
4. Добавить validator для unsafe language и unsupported terms.

## Затрагиваемые файлы

| Файл | Изменение |
|---|---|
| `backend/app/modules/report_narratives/schemas.py` | New section schemas |
| `backend/app/modules/report_narratives/input_builder.py` | tension/failure signals |
| `backend/app/modules/report_narratives/prompts/self_story_v2.md` | Prompt section rules |
| `backend/app/modules/report_narratives/validators.py` | Safety + section validation |
| `frontend/src/components/report/` | Rendering новых блоков |

## Критерии приёмки

- [ ] В отчёте есть 3–5 central contradictions.
- [ ] Есть блок failure modes с конкретными поведенческими сбоями.
- [ ] Есть maturity levels: low / medium / high.
- [ ] Каждый конфликт имеет mature/reframe формулировку.
- [ ] Нет fatalistic/medical/diagnostic wording.
- [ ] Validator покрывает forbidden language.

## Проверка

```bash
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives/test_validators.py -q'
```
