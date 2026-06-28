# S07 — API, Frontend and PDF Integration

> Статус: 🟡 В процессе

## Контекст

Staged backend is not enough; the user needs a smooth report screen and PDF parity without seeing internal debug artifacts.

## Текущий кодовый статус

На момент текущей синхронизации уже закрыты два реальных integration slice:

- report API теперь отдаёт top-level `narrative_progress` и `narrative_stage_artifacts`;
- frontend progress screen читает staged progress даже когда `narrative` body ещё не готов;
- user-facing progress labels и completed-stage chips рендерятся без утечки raw stage JSON;
- PDF уже получил user-facing staged summary block для ready narrative;
- `frontend/scripts/check-report-ux.mjs` покрывает staged markers для web/progress/PDF parity contract.

Ещё не закрыто end-to-end:

- staged runtime smoke `generate -> progress -> ready -> pdf` не доказан на живом full flow;
- нет отдельного live proof, что worker lifecycle стабильно держит stage-level progress до final ready;
- нет явной пользовательской smoke-проверки, что web ready content и PDF остаются согласованными после реальной генерации, а не только по unit/integration tests.

## Что сделать

1. Extend report API response with `narrative_progress` / staged progress metadata.
2. Update frontend polling copy and progress steps.
3. Render staged narrative output through existing narrative-first UI.
4. Add UI blocks for aspect patterns and chart dynamics if they become visible sections.
5. Update PDF template to include the same assembled staged content.
6. Extend `frontend/scripts/check-report-ux.mjs` with staged markers and anti-technical-first assertions.

## Затрагиваемые файлы

| Файл                                                            | Действие                                 |
| --------------------------------------------------------------- | ---------------------------------------- |
| `backend/app/modules/reports/schemas.py`                        | Baseline progress fields уже добавлены   |
| `backend/app/modules/reports/router.py`                         | Include progress metadata                |
| `frontend/src/lib/api/report.ts`                                | Type updates                             |
| `frontend/src/lib/report/view-model.ts`                         | Normalize staged narrative               |
| `frontend/src/components/report/report-generation-progress.tsx` | Stage-aware copy                         |
| `frontend/src/components/report/report-narrative-page.tsx`      | Render staged sections                   |
| `backend/app/modules/reports/templates/report.html`             | PDF parity                               |
| `frontend/scripts/check-report-ux.mjs`                          | Regression checks                        |

## Acceptance criteria

- [x] User sees meaningful progress labels, not internal stage ids.
- [x] Partial internal sections are not rendered as final content.
- [x] Ready web report and PDF contain the same staged narrative blocks at contract level.
- [x] Technical details remain below the narrative.
- [x] Frontend structural check prevents top-level debug/stage JSON from leaking.
- [ ] Live runtime smoke proves `generate -> progress -> ready -> pdf` for the staged path.

## Реализовано

1. `feat(report): add staged summary pdf parity` (`fd7dc6c`)
   - `backend/app/modules/reports/pdf.py`
   - `backend/app/modules/reports/templates/report.html`
   - `backend/tests/unit/test_reports/test_pdf.py`
   - `frontend/scripts/check-report-ux.mjs`
2. `feat(report): expose staged narrative progress in api` (`252d7dc`)
   - `backend/app/modules/reports/schemas.py`
   - `backend/tests/unit/test_reports/test_reports.py`
   - `frontend/src/lib/api/report.ts`
   - `frontend/src/lib/report/view-model.ts`
   - `frontend/src/components/report/report-generation-progress.tsx`
   - `frontend/src/app/(dashboard)/report/[profileId]/page.tsx`
   - `frontend/scripts/check-report-ux.mjs`

## Свежая verification evidence

- `pytest tests/unit/test_reports/test_reports.py tests/unit/test_reports/test_pdf.py tests/unit/test_report_narratives/test_api.py -q` → `44 passed`
- `ruff check app/modules/reports/schemas.py tests/unit/test_reports/test_reports.py tests/unit/test_reports/test_pdf.py` → `All checks passed!`
- `mypy app/modules/reports/schemas.py tests/unit/test_reports/test_reports.py tests/unit/test_reports/test_pdf.py` → `Success: no issues found in 3 source files`
- `node frontend/scripts/check-report-ux.mjs` → `Report UX structure check passed`
- `npx tsc --noEmit --pretty false` → exit `0`
- `npm run build` → production build green
