# S06 — Self-to-Career Teaser

Статус: ✅ Готово
Эпик: `E13-report-depth-improvements`

## Контекст

Self report может содержать карьерный хвост, но он должен быть teaser-слоем, а не заменой Career report. Сейчас CTA может восприниматься как заглушка. Нужно дать реальный предварительный вектор и ясно показать, что глубокий разбор ролей/рисков/среды находится в Career.

## Целевой пример

```text
Предварительный карьерный вектор

Эта карта хорошо ложится на роли, где нужно:
- анализировать сложные системы;
- переводить хаос в структуру;
- работать с методологиями, правилами, архитектурой, знаниями;
- соединять практическую пользу с большой концепцией.

В Career-отчёте мы разберём это по ролям, рискам, рабочей среде и стратегии роста.
```

## Boundaries

Allowed in Self:

- 3–5 broad role directions;
- work style hints;
- one paragraph why Career would be useful;
- CTA to Career.

Not allowed in Self:

- full profession list with detailed ranking;
- money strategy;
- leadership profile;
- burnout/work environment deep dive;
- detailed career plan;
- management/entrepreneurship prescription.

## Что сделать

1. Replace generic Career CTA with evidence-backed `career_teaser`.
2. Ensure prompt explicitly limits Career depth.
3. Validator rejects Career leakage in Self narrative.
4. UI renders teaser after calibration/development, before PDF save block.
5. PDF includes teaser but keeps it compact.

## Затрагиваемые файлы

| Файл | Изменение |
|---|---|
| `backend/app/modules/report_narratives/schemas.py` | `CareerTeaser` contract |
| `backend/app/modules/report_narratives/prompts/self_story_v2.md` | Self/Career boundary rules |
| `backend/app/modules/report_narratives/validators.py` | Career leakage validation |
| `frontend/src/components/report/career-cta.tsx` | More useful teaser UI |
| `backend/app/modules/reports/templates/report.html` | PDF parity |

## Критерии приёмки

- [x] Career teaser is specific enough to be useful.
- [x] Career teaser remains bounded and does not replace Career report.
- [x] Validator catches detailed role/money/leadership plans inside Self.
- [x] CTA copy is commercial but not pushy.
- [x] UI and PDF render the same teaser content.

## Проверка

```bash
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives/test_validators.py -q'
cd frontend && node scripts/check-report-ux.mjs
```
