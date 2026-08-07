# S05 — Frontend/PDF Readability and Pacing

Статус: ✅ Готово
Эпик: `E15-self-report-human-storytelling`

## Контекст

Humanized prose may be longer than the current compact report. UI/PDF must support rhythm: paragraphs, progressive disclosure and scan-friendly sections, not a single wall of text.

## Что сделать

1. Audit current `ReportNarrativePage` rendering with longer section bodies.
2. Ensure paragraphs are preserved from narrative JSON.
3. Keep evidence notes collapsed/secondary.
4. Keep PDF/save actions below the first meaningful narrative flow.
5. Add structural UX checks for:
   - recognition-first hero;
   - no technical-first top screen;
   - paragraph rendering;
   - evidence after narrative.

## Затрагиваемые файлы

| Файл                                                       | Изменение                          |
| ---------------------------------------------------------- | ---------------------------------- |
| `frontend/src/components/report/report-narrative-page.tsx` | Pacing/layout if needed            |
| `frontend/src/components/report/narrative-section.tsx`     | Paragraph rendering                |
| `frontend/src/components/report/evidence-notes.tsx`        | Disclosure behavior                |
| `frontend/src/lib/report/view-model.ts`                    | Normalize paragraph arrays/strings |
| `frontend/scripts/check-report-ux.mjs`                     | Structural checks                  |
| `backend/app/modules/reports/templates/report.html`        | PDF paragraph parity               |
| `backend/tests/unit/test_reports/test_pdf.py`              | PDF parity test                    |

## Acceptance criteria

- [x] Web preserves paragraph breaks from narrative sections.
- [x] PDF preserves the same reading order and does not flatten all prose into one block.
- [x] Evidence remains secondary and does not interrupt first-read flow.
- [x] Structural UX script catches a technical-first hero regression.
- [x] Longer humanized report remains readable on mobile.

## Реализация

- `view-model.ts` теперь нормализует narrative body как string/array input в `body_paragraphs`, сохраняя `body` для обратной совместимости.
- Web rendering использует `renderNarrativeParagraphs(...)` для `hero`, секций и `final_summary`, поэтому `\n\n` больше не схлопывается в один `<p>`.
- `check-report-ux.mjs` проверяет paragraph-preserving markers, отсутствие flattened `<p>{section.body}</p>`, recognition-first hero flow, evidence-after-narrative и PDF action below-first-flow.
- PDF renderer получил Jinja filter `paragraphs`, а шаблон `report.html` рендерит hero/sections/final summary отдельными `<p>` в том же reading order.
- Добавлен backend regression `test_render_report_html_preserves_narrative_paragraph_breaks`.

## Verification evidence

```text
node frontend/scripts/check-report-ux.mjs
→ Report UX structure check passed

frontend: npx tsc --noEmit --pretty false
→ passed

frontend: npx prettier --check src/components/report/report-narrative-page.tsx src/components/report/narrative-section.tsx src/lib/report/view-model.ts scripts/check-report-ux.mjs
→ passed

backend: python -m pytest tests/unit/test_reports/test_pdf.py -q
→ 6 passed

backend: ruff check/format + mypy for app/modules/reports/pdf.py and tests/unit/test_reports/test_pdf.py
→ passed
```

## Verification

```bash
cd frontend
node scripts/check-report-ux.mjs
npx tsc --noEmit --pretty false
npx prettier --check src/components/report src/lib/report scripts/check-report-ux.mjs
```

```bash
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_reports/test_pdf.py -q'
```
