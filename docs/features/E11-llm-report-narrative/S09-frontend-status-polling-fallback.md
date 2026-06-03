# Story E11.S09: Frontend status polling, timeout, retry and fallback

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Frontend не должен показывать бесконечную «Генерация...». Он обязан различать deterministic_ready/generating_narrative/ready/narrative_failed, показывать понятный timeout state, давать retry и deterministic fallback.

## Что сделать

1. Обновить frontend report API types/client под narrative response shape.
2. Добавить polling для `GET /api/v1/reports/{id}` при `generating_narrative`.
3. После 90 секунд показывать сообщение «Текстовый отчёт ещё собирается», кнопку «Обновить» и fallback «Показать технический отчёт».
4. При `narrative_failed` показать warning, deterministic fallback и кнопку «Повторить генерацию».
5. Подключить regenerate endpoint к retry button.
6. Не ломать cookie auth path: protected fetch не должен early-return из-за отсутствия JS token.
7. Добавить deterministic frontend regression test/script assertions на statuses.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `frontend/src/lib/api/report.ts` | Types/client methods |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Status handling |
| `frontend/src/components/report/report-generation-progress.tsx` | New/updated progress UI |
| `frontend/src/components/report/deterministic-report-fallback.tsx` | Fallback UI |
| `frontend/scripts/check-report-ux.mjs` | Regression checks |

## Критерии приёмки

- [ ] `generating_narrative` показывает progress state без chart/radar/raw scores в первом экране.
- [ ] После timeout UI не висит молча, а предлагает refresh/fallback.
- [ ] `narrative_failed` показывает deterministic fallback и retry.
- [ ] Retry вызывает regenerate endpoint и возвращает UI в generation state.
- [ ] Protected fetch работает через HttpOnly cookies без обязательного JS token.
- [ ] `npm test` проверяет отсутствие endless spinner-only state.
