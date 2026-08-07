# Story E10.S01: Report data contract и placeholders removal

**Feature:** [Report UX Redesign — понятный self-report](Archemap/docs/features/v1/E10-report-ux-redesign/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Новый UX нельзя строить на placeholder-данных. Сначала нужно зафиксировать, какие данные report page получает из API, какие поля уже есть, какие нужно адаптировать на frontend, и убрать placeholder-путь из `/report/[profileId]`.

## Что сделать

1. Проверить текущий API/клиентский contract для self-report.
2. Убедиться, что `/report/[profileId]` получает реальные данные профиля, chart snapshot, archetype и socionics outputs.
3. Ввести frontend adapter/view-model для report UX, чтобы новые компоненты не зависели напрямую от сырого API shape.
4. Описать fallback-и для отсутствующих полей: неизвестное время рождения, нет ASC/домов, нет aspects, нет evidence.
5. Убрать placeholder-данные из report page.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Подключить real API data вместо placeholder |
| `frontend/src/lib/api/*` | Проверить/обновить report API client |
| `frontend/src/lib/report/*` | Создать adapter/view-model для UI |
| `contracts/openapi.yaml` | Обновить только если фактический contract отличается |

## Критерии приёмки

- [x] `/report/[profileId]` использует реальные API-данные: `GET /api/v1/profiles/{profileId}` + `POST /api/v1/profiles/{profileId}/chart` через `fetchReportApiData`.
- [x] Placeholder/mock data удалены из runtime path: `placeholderData` убран из page, regression script это проверяет.
- [x] Есть typed frontend adapter/view-model для report UX: `frontend/src/lib/report/view-model.ts`.
- [x] Unknown/partial data не ломает страницу и имеет явные fallback-и: adapter нормализует отсутствующие planets/houses/aspects/socionics/function_strengths.
- [x] Если contract изменился, обновлён `contracts/openapi.yaml`: contract не менялся, используются существующие endpoints.
- [x] `npx eslint .`, `npx prettier --check .`, `npx tsc --noEmit --pretty false` и `npm test` проходят без ошибок.
