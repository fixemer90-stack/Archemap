# Story E11.S11: PDF rendering from narrative JSON

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** 🟨 В работе (код и тесты готовы, runtime smoke blocked by WeasyPrint system libs)

## Контекст

PDF должен использовать тот же saved narrative JSON, что и frontend. Нельзя делать второй LLM call для PDF: это дороже, недетерминированно и может дать другой текст.

## Что сделать

1. Обновить PDF rendering pipeline: брать `ReportNarrative.content`, если narrative ready.
2. Добавить fallback PDF для `narrative_failed`: deterministic report + warning.
3. Обновить Jinja2 template под narrative sections/hero/career_cta/evidence notes.
4. Сохранить technical appendix с deterministic evidence/details ниже narrative.
5. Не запускать LLM из PDF task.
6. Добавить PDF tests/smoke: narrative ready, narrative_failed fallback, missing narrative.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `backend/app/modules/reports/pdf.py` | PDF data source update |
| `backend/app/modules/reports/templates/report.html` | Narrative template sections |
| `backend/workers/tasks/reports.py` | Ensure PDF task does not call LLM |
| `backend/tests/unit/test_reports/test_pdf.py` | PDF unit/smoke tests |
| `backend/tests/unit/test_report_narratives/fixtures/` | Narrative JSON fixtures |

## Критерии приёмки

- [x] PDF for ready narrative uses stored JSON exactly as source text.
- [x] PDF generation never calls `LLMProvider`.
- [x] `narrative_failed` still produces a useful deterministic PDF/fallback or explicit unavailable state.
- [x] PDF contains Career CTA for Self narrative.
- [x] Technical appendix remains available but does not precede narrative content.
- [x] PDF tests pass without external services except existing mocked storage as needed.

## Notes / blockers

- Unit coverage for `ready narrative`, `narrative_failed`, `missing narrative`, and PDF task wiring is green.
- Real PDF smoke inside the current backend container is still blocked by missing WeasyPrint system library `libgobject-2.0-0` (`OSError: cannot load library 'libgobject-2.0-0'`).
- Story code changes are in place, but container/runtime dependencies still need to be provisioned before calling the story fully shipped.
