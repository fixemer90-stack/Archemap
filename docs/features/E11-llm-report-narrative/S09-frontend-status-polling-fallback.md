# Story E11.S09: Frontend status polling, timeout, retry and fallback

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Frontend не должен показывать бесконечную «Генерация...». Он обязан различать deterministic_ready/generating_narrative/ready/narrative_failed, показывать понятный timeout state, давать retry и deterministic fallback.

## Что сделано

1. Обновлены frontend report API types/client под narrative response shape: `status`, `narrative`, `error_message`, `GET /api/v1/reports/{id}` и regenerate endpoint.
2. Report page теперь выбирает latest report и polling-ит `GET /api/v1/reports/{id}` при `generating_narrative`.
3. Добавлен 90-секундный timeout state: «Текстовый отчёт ещё собирается», «Обновить» и «Показать технический отчёт».
4. При `narrative_failed`/`deterministic_ready` показывается deterministic fallback с warning и кнопкой «Повторить генерацию».
5. Retry вызывает `POST /api/v1/reports/{report_id}/narrative/regenerate`, сбрасывает timeout/fallback и возвращает UI в generation state.
6. Cookie auth path сохранён: protected fetch продолжает идти с optional token и не делает early-return при пустом JS token.
7. `frontend/scripts/check-report-ux.mjs` теперь проверяет narrative statuses, polling markers, timeout/fallback UI texts и API helpers.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `frontend/src/lib/api/report.ts` | Types/client methods |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Status handling |
| `frontend/src/components/report/report-generation-progress.tsx` | New progress/timeout UI |
| `frontend/src/components/report/deterministic-report-fallback.tsx` | Fallback UI |
| `frontend/scripts/check-report-ux.mjs` | Regression checks |

## Критерии приёмки

- [x] `generating_narrative` показывает progress state без chart/radar/raw scores в первом экране.
- [x] После timeout UI не висит молча, а предлагает refresh/fallback.
- [x] `narrative_failed` показывает deterministic fallback и retry.
- [x] Retry вызывает regenerate endpoint и возвращает UI в generation state.
- [x] Protected fetch работает через HttpOnly cookies без обязательного JS token.
- [x] `npm test` проверяет отсутствие endless spinner-only state.

## Проверка

```bash
cd frontend
npm test
npx tsc --noEmit --pretty false
npx prettier --check .
npx eslint .
```
