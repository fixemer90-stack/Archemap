# S03 — Evidence Tracing in Narrative and PDF

Статус: ✅ Готово
Эпик: `E13-report-depth-improvements`

## Контекст

Сейчас technical appendix и narrative могут восприниматься как два разных слоя. Пользователь должен видеть, что выводы не взяты “из воздуха”: каждый сильный тезис должен быть связан с основаниями.

## Целевой пример

```text
Вывод: выраженное системное мышление.

Основания:
- Меркурий в Деве — точность, аналитика, работа с деталями.
- Меркурий в 10 доме — применение мышления в профессиональной/социальной роли.
- Меркурий трин Сатурн — способность удерживать структуру и доводить мысль до формы.
- Земля 53% — практическая ориентация.

Ограничение:
- Луна в Весах в 11 доме добавляет зависимость от контекста и реакции группы.
```

## Что сделать

1. Нормализовать evidence refs в `NarrativeInput`:
   - placements;
   - aspects;
   - features;
   - house emphasis;
   - socionics/function signals when relevant.
2. Добавить `evidence_notes` к новым E13 sections.
3. Обновить validators:
   - unknown evidence ref → validation error;
   - claim без evidence для ключевых блоков → validation error;
   - limitation/counter-evidence разрешён, но тоже должен ссылаться на известный факт.
4. В UI оставить evidence collapsed by default, чтобы Self не становился техническим отчётом.
5. В PDF сделать компактный evidence sub-block под ключевыми выводами или appendix cross-reference.

## Затрагиваемые файлы

| Файл | Изменение |
|---|---|
| `backend/app/modules/report_narratives/input_builder.py` | stable evidence id map |
| `backend/app/modules/report_narratives/validators.py` | strict evidence validation |
| `backend/app/modules/report_narratives/schemas.py` | evidence-backed insight schemas |
| `frontend/src/components/report/evidence-notes.tsx` | UI для оснований |
| `backend/app/modules/reports/templates/report.html` | PDF evidence rendering |
| `frontend/scripts/check-report-ux.mjs` | Structural checks |

## Критерии приёмки

- [x] Главные выводы E13 имеют evidence refs.
- [x] Unknown refs отклоняются validator-ом.
- [x] Evidence в UI не доминирует над narrative.
- [x] PDF сохраняет трассировку.
- [x] Regression tests покрывают missing/unknown evidence refs.

## Проверка

```bash
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives/test_validators.py tests/unit/test_reports/test_pdf.py -q'
```
