# S07 — Rendering, Prompt Contract, and Quality Gates

Статус: ⬜ Не начато
Эпик: `E13-report-depth-improvements`

## Контекст

E13 меняет не только текст, но и контракт отчёта. Чтобы не получить свободный LLM blob, нужен versioned prompt, строгий JSON contract, frontend rendering, PDF parity и regression checks.

## Что сделать

1. Создать `self_story_v2` вместо тихого изменения текущего prompt.
2. Расширить `SelfNarrative` schema или создать backward-compatible `DeepSelfNarrative` fields.
3. Обновить normalizer в frontend view-model.
4. Добавить новые report components.
5. Обновить PDF template.
6. Обновить structural regression script.
7. Добавить tests for:
   - section order;
   - required fields;
   - evidence refs;
   - Self/Career boundary;
   - unsafe language;
   - PDF includes new blocks.

## Required section order

1. Hero.
2. Main formula.
3. Dominants.
4. Inner mechanism.
5. House/life scenarios.
6. Strengths.
7. Contradictions.
8. System failures.
9. Relationships/closeness/sexuality.
10. Development and maturity levels.
11. Calibration questions.
12. Career teaser.
13. Final summary.

## Затрагиваемые файлы

| Файл | Изменение |
|---|---|
| `backend/app/modules/report_narratives/prompts/self_story_v2.md` | New prompt contract |
| `backend/app/modules/report_narratives/prompts.py` | Prompt version export |
| `backend/app/modules/report_narratives/schemas.py` | New fields |
| `backend/app/modules/report_narratives/validators.py` | New validation rules |
| `backend/app/modules/report_narratives/fallback.py` | Complete fallback |
| `frontend/src/lib/report/view-model.ts` | Normalize new fields |
| `frontend/src/components/report/` | New components |
| `frontend/scripts/check-report-ux.mjs` | Structural regression |
| `backend/app/modules/reports/templates/report.html` | PDF rendering |
| `backend/tests/unit/test_reports/test_pdf.py` | PDF checks |

## Критерии приёмки

- [ ] `self_story_v2` exists and old prompt is not silently mutated.
- [ ] New schema fields are validated and normalized.
- [ ] Frontend renders sections in required order.
- [ ] Missing required E13 section fails tests.
- [ ] PDF includes E13 blocks.
- [ ] Structural check protects narrative-first ordering.
- [ ] Backend + frontend gates pass.

## Проверка

Backend:

```bash
docker compose exec -T backend sh -lc 'cd /app && python -m ruff check app/modules/report_narratives app/modules/reports tests/unit/test_report_narratives tests/unit/test_reports && python -m ruff format --check app/modules/report_narratives app/modules/reports tests/unit/test_report_narratives tests/unit/test_reports && python -m mypy app/modules/report_narratives app/modules/reports && python -m pytest tests/unit/test_report_narratives tests/unit/test_reports -q'
```

Frontend:

```bash
cd frontend
node scripts/check-report-ux.mjs
npm test
npx tsc --noEmit --pretty false
npx prettier --check .
npx eslint .
```
