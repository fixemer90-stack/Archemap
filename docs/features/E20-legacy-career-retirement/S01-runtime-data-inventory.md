# S01: Инвентаризировать runtime consumers и production data

## Статус

⬜ Не начато

## Контекст

Удаление нельзя основывать на отсутствии ссылки в dashboard. Нужно доказать реальные consumers, объём сохранённых данных и отличие entitlement от report row.

## Что сделать

1. Зафиксировать call graph frontend route → API → service → storage/PDF.
2. Найти все write/read consumers `product="career"` в generic reports.
3. Выполнить production-safe aggregate census:
   - legacy Career rows и уникальные владельцы;
   - rows по статусам и версиям;
   - active grandfathered entitlements;
   - пользователи с entitlement без row и row без entitlement;
   - последние legacy read/PDF/write events, если telemetry доступна.
4. Проверить внешние API clients, bookmarks/deep links, admin/support operations и tests.
5. Сохранить только агрегаты; не копировать payload или персональные данные в документацию.

## Файлы

| Файл/область                                               | Действие                    |
| ---------------------------------------------------------- | --------------------------- |
| `backend/app/modules/reports/*`                            | Аудит call graph            |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Аудит legacy route          |
| `frontend/src/lib/api/report.ts`                           | Аудит client calls          |
| E20 evidence/runbook                                       | Записать агрегаты и решение |

## Критерии приёмки

- [ ] Все generic Career endpoints и clients перечислены с read/write классификацией.
- [ ] Подтверждено, какие generic reports paths нужны Self Report и не подлежат удалению.
- [ ] Production census выполнен read-only запросами и не раскрывает PII.
- [ ] Entitlements и report rows посчитаны раздельно.
- [ ] Зафиксированы неизвестные/неизмеряемые consumers и способ закрыть gap.
- [ ] Нет destructive SQL или data migration.
