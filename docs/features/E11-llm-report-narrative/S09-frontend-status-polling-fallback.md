# Story E11.S09: Frontend status polling, timeout, retry and unavailable state

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Frontend не должен показывать бесконечную «Генерация...». Для Self он обязан различать `deterministic_ready` / `generating_narrative` / `ready` / `narrative_failed`, показывать понятный timeout state, давать retry и не подменять полный narrative техническим fallback summary.

## Что сделано

1. Обновлены frontend report API types/client под narrative response shape: `status`, `narrative`, `error_message`, `GET /api/v1/reports/{id}` и regenerate endpoint.
2. Report page теперь выбирает latest report и polling-ит `GET /api/v1/reports/{id}` при `generating_narrative`.
3. Добавлен 90-секундный timeout state: «Текстовый отчёт ещё собирается», «Обновить» и «Повторить генерацию».
4. При `narrative_failed` или `ready` без `narrative` показывается отдельный unavailable state с warning и кнопкой «Повторить генерацию», а не deterministic fallback summary.
5. Статус `deterministic_ready` больше не открывает техническую fallback-версию для Self: frontend остаётся в progress/ожидании полного текста и не рендерит `DeterministicReportFallback`.
6. Retry вызывает `POST /api/v1/reports/{report_id}/narrative/regenerate`, сбрасывает timeout/unavailable state и возвращает UI в generation state.
7. Cookie auth path сохранён: protected fetch продолжает идти с optional token и не делает early-return при пустом JS token.
8. `frontend/scripts/check-report-ux.mjs` теперь проверяет narrative statuses, polling markers, отсутствие legacy fallback markers и новый unavailable/progress UI.

## Затрагиваемые файлы

| Файл                                                               | Действие                                                                      |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| `frontend/src/lib/api/report.ts`                                   | Types/client methods                                                          |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx`         | Status handling                                                               |
| `frontend/src/components/report/report-generation-progress.tsx`    | New progress/timeout UI                                                       |
| `frontend/src/components/report/deterministic-report-fallback.tsx` | Legacy fallback component remains in tree but is not used by Self report page |
| `frontend/scripts/check-report-ux.mjs`                             | Regression checks                                                             |

## Критерии приёмки

- [x] `generating_narrative` показывает progress state без chart/radar/raw scores в первом экране.
- [x] После timeout UI не висит молча, а предлагает refresh/retry без перехода в technical fallback.
- [x] `narrative_failed` или `ready` без narrative показывают unavailable state и retry.
- [x] Self report не рендерит `DeterministicReportFallback`, `showFallback` и кнопку «Показать технический отчёт».
- [x] Retry вызывает regenerate endpoint и возвращает UI в generation state.
- [x] Protected fetch работает через HttpOnly cookies без обязательного JS token.
- [x] `frontend/scripts/check-report-ux.mjs`, `npx tsc --noEmit --pretty false` и `npx eslint ...` подтверждают отсутствие legacy fallback UI.

## Проверка

```bash
cd frontend
node scripts/check-report-ux.mjs
npx tsc --noEmit --pretty false
npx eslint src/app/'(dashboard)'/report/'[profileId]'/page.tsx src/components/report/report-generation-progress.tsx scripts/check-report-ux.mjs
```
