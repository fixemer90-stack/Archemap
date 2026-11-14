# S01: Инвентаризировать runtime consumers и production data

## Статус

🟡 Source inventory и проверенный read-only census tool готовы; production census и внешние consumers заблокированы до восстановления инфраструктуры.

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

- [x] Все generic Career endpoints и repository clients перечислены с read/write классификацией; внешние клиенты явно неизвестны.
- [x] Подтверждено, какие generic reports paths нужны Self Report и не подлежат удалению.
- [ ] Production census выполнен read-only запросами и не раскрывает PII. **Блокер: сервер утрачен; данных для census нет.**
- [ ] Entitlements и report rows посчитаны раздельно на production/restored-data snapshot. Synthetic SQL/CLI проверены, но не подменяют этот результат.
- [x] Зафиксированы неизвестные/неизмеряемые consumers и способ закрыть gap.
- [x] Census tool не содержит destructive SQL или data migration; тестовая DDL ограничена собственными disposable fixtures.

## Source evidence и локальная проверка

[INVENTORY.md](./INVENTORY.md) содержит call graph всех mounted generic routes, direct/queued narrative writers, PDF/versions paths, обнаруженный `/rules/interpret` generation bypass и frontend chart-POST side effect. Внешние clients и фактические старые broker messages не объявлены отсутствующими.

Census implementation: `backend/scripts/legacy_career_census.py`. Первый RED: 8 failed из-за отсутствующего инструмента; первый GREEN: 8 unit + 2 real PostgreSQL integration = 10 passed. После независимого spec finding добавлены шесть falsy-root metadata regressions, сопоставленные с реальным canonical access: RED 4 failed / 2 passed; после первого исправления SQL census suite **16 passed** (8 unit + 8 integration). Второй numeric-underflow finding воспроизведён raw JSON insertion и чтением через реальный DB decoder: RED **12 failed / 6 passed**; после исправления SQL rounding boundary полный census suite **34 passed** (8 unit + 26 integration). Independent SPEC re-review `deleg_fe8fe02d`: PASS по текущему source candidate, без независимого DB/unit execution; code/security `deleg_4751131c` — PASS для census scope, fingerprints проверены; live evidence остаётся открытым. Реальный PostgreSQL отклонил mutating probe с SQLSTATE `25006`; synthetic CLI — exit 0. Ruff/format/scoped mypy — PASS, owned PostgreSQL container удалён с readback. Это не production census и не migration/removal approval.
