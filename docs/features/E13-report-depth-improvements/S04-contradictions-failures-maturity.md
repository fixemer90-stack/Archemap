# S04 — Contradictions, Failures, and Maturity Levels

Статус: ✅ Готово
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

| Файл                                                             | Изменение                                                      |
| ---------------------------------------------------------------- | -------------------------------------------------------------- |
| `backend/app/modules/report_narratives/schemas.py`               | New section schemas                                            |
| `backend/app/modules/report_narratives/input_builder.py`         | Deterministic contradictions / failure modes / maturity levels |
| `backend/app/modules/report_narratives/prompts/self_story_v5.md` | Prompt rules for S04 blocks                                    |
| `backend/app/modules/report_narratives/validators.py`            | Safety + section validation                                    |
| `backend/app/modules/report_narratives/fallback.py`              | Preserve S04 blocks in degraded mode                           |
| `backend/app/modules/reports/templates/report.html`              | PDF parity for contradictions / failures / maturity            |
| `frontend/src/lib/report/view-model.ts`                          | Adapter types + normalizers                                    |
| `frontend/src/components/report/pattern-tensions-section.tsx`    | Rendering новых блоков                                         |
| `frontend/src/components/report/report-narrative-page.tsx`       | Narrative order wiring                                         |

## Критерии приёмки

- [x] В отчёте есть 3–5 central contradictions.
- [x] Есть блок failure modes с конкретными поведенческими сбоями.
- [x] Есть maturity levels: low / medium / high.
- [x] Каждый конфликт имеет mature/reframe формулировку.
- [x] Нет fatalistic/medical/diagnostic wording.
- [x] Validator покрывает forbidden language.

## Проверка

```bash
cd backend
.venv/bin/python -m pytest tests/unit/test_report_narratives/test_schemas.py tests/unit/test_report_narratives/test_input_builder.py tests/unit/test_report_narratives/test_validators.py tests/unit/test_report_narratives/test_fallback.py tests/unit/test_report_narratives/test_prompts.py tests/unit/test_reports/test_pdf.py tests/unit/test_reports/test_reports.py -q
.venv/bin/ruff check app/modules/report_narratives app/modules/reports tests/unit/test_report_narratives tests/unit/test_reports -q
```
