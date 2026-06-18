# S05 — Calibration Questions and Feedback Loop

Статус: ⬜ Не начато
Эпик: `E13-report-depth-improvements`

## Контекст

Калибровочные вопросы обязательны для Astrotype: они превращают отчёт из статичного текста в проверяемую модель. На первом этапе можно показать вопросы без сохранения ответов; далее ответы смогут корректировать архетип, типаж и веса.

## Целевой пример

```text
Проверьте модель
1. Вам легче объяснить свою позицию через систему аргументов, чем через эмоцию?
2. Вы часто чувствуете, что ваша ценность должна быть подтверждена результатом?
3. Вы раздражаетесь, когда люди действуют без структуры, но сами можете уставать от чрезмерного контроля?
4. Вам важно не просто работать, а понимать большую идею за работой?
5. Вам знакомо чувство: “я сделал много, но всё равно недостаточно”?
```

## MVP scope

- Render-only questions in Self report.
- No persistence required in first iteration.
- Questions must be evidence-backed and not diagnostic.

## Later scope

- Store answers.
- Use answers as calibration signals.
- Feed calibration into:
  - archetype confidence;
  - socionics score adjustment;
  - narrative personalization;
  - report regeneration.

## Что сделать

1. Добавить `CalibrationQuestion` schema.
2. Генерировать 5–7 вопросов по главным механизмам/противоречиям.
3. Добавить validator:
   - questions are questions;
   - no diagnosis;
   - each question relates to known evidence or generated mechanism.
4. UI: block after maturity/development, before Career teaser.
5. Future-proof schema for answer type:
   - yes/no;
   - scale 1–5;
   - free text (later).

## Затрагиваемые файлы

| Файл | Изменение |
|---|---|
| `backend/app/modules/report_narratives/schemas.py` | `CalibrationQuestion` |
| `backend/app/modules/report_narratives/prompts/self_story_v2.md` | Question generation rules |
| `backend/app/modules/report_narratives/validators.py` | Question validation |
| `frontend/src/components/report/calibration-questions.tsx` | UI block |
| `backend/app/modules/reports/templates/report.html` | PDF parity |

## Критерии приёмки

- [ ] Self report shows 5–7 calibration questions.
- [ ] Questions are tied to model claims, not generic personality quiz filler.
- [ ] No answer persistence is required for MVP.
- [ ] Schema can later support answers without breaking API.
- [ ] PDF includes the questions.

## Проверка

```bash
cd frontend
node scripts/check-report-ux.mjs
npx tsc --noEmit --pretty false
```
