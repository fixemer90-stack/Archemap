# Story E11.S11: PDF rendering from narrative JSON

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ✅ Завершено

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

## Verification

- Backend Docker image now installs the native WeasyPrint runtime libs required for real PDF generation (`libglib2.0-0`, `libpango-1.0-0`, `libpangocairo-1.0-0`, `libcairo2`, `libgdk-pixbuf-2.0-0`, `libharfbuzz0b`).
- Added a real smoke unit test `test_generate_report_pdf_smoke_returns_pdf_bytes` that calls WeasyPrint and asserts PDF bytes are produced.
- Verified inside the backend container that PDF rendering succeeds and no LLM call is needed.

## Notes

- Unit coverage for `ready narrative`, `narrative_failed`, `missing narrative`, PDF task wiring, and real PDF byte generation is green.
- PDF still renders from saved narrative JSON only; no second LLM call is introduced in the PDF path.
