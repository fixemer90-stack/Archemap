# S07 — API, Frontend and PDF Integration

> Статус: ⬜ Не начато

## Контекст

Staged backend is not enough; the user needs a smooth report screen and PDF parity without seeing internal debug artifacts.

## Текущий кодовый статус

На момент синхронизации docs backend уже имеет baseline progress contracts в `backend/app/modules/reports/schemas.py`, но end-to-end integration ещё не подключена:

- frontend не использует `narrative_progress` / `stage_progress`;
- staged progress labels не рендерятся пользователю;
- web report не переключён на staged assembled content path;
- PDF parity для staged output не доказана;
- runtime smoke по staged flow отсутствует.

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

- [ ] User sees meaningful progress labels, not internal stage ids.
- [ ] Partial internal sections are not rendered as final content.
- [ ] Ready web report and PDF contain the same staged narrative blocks.
- [ ] Technical details remain below the narrative.
- [ ] Frontend structural check prevents top-level debug/stage JSON from leaking.
