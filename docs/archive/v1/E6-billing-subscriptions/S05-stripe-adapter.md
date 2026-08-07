# Story E6.S05: Paid access orchestration

Feature: [Billing & Subscriptions](Archemap/docs/features/v1/E6-billing-subscriptions/FEATURE.md)
Статус: ⬜ Не начато

## Контекст

Даже после появления checkout entrypoint система всё ещё может быть логически дырявой: payment живёт отдельно, entitlement отдельно, UI-state отдельно.

Эта story закрывает именно orchestration-слой между ними.

Нужен единый механизм, который умеет собрать из разных источников одно коммерческое состояние пользователя:

- есть ли активный paid access;
- какой payment сейчас последний значимый;
- нужно ли показать pending, failure или active;
- какие grants реально применимы к продуктам и отчётам прямо сейчас.

## Что сделать

1. Определить backend aggregation rule для `access_status` на основе:
   - `payments`
   - `entitlements`
   - при необходимости `subscriptions`
2. Зафиксировать приоритеты состояний:
   - `plus_active`
   - `checkout_pending`
   - `payment_failed`
   - `plus_inactive`
   - `free`
3. Согласовать, какая payment attempt считается актуальной для UI.
4. Подготовить reusable service-layer, который используют:
   - `/billing/access`
   - report/product gating
   - post-payment refresh
5. Явно описать и реализовать degraded paths:
   - payment создан, webhook ещё не пришёл;
   - webhook пришёл, entitlement не выдан;
   - payment failed/cancelled;
   - исторические успешные платежи есть, но active access уже нет.

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/billing/service.py` | Сборка access state из payment/entitlement данных |
| `backend/app/modules/payments/service.py` | Актуальные payment statuses для orchestration |
| `backend/app/modules/authorization/service.py` | Источник и проверка entitlement state |
| `backend/app/modules/subscriptions/service.py` | Будущий recurring-friendly слой, если нужен для lifecycle |
| `backend/app/modules/billing/schemas.py` | Access state response contract |
| `docs/features/E6-billing-subscriptions/API.md` | State machine и semantics |
| `docs/SRS/SRS-E6-billing-subscriptions.md` | Формальные FR/NFR по access state |

## Критерии приёмки

- [ ] Есть единый backend service, который вычисляет `access_status` пользователя
- [ ] `payments`, `entitlements` и другие коммерческие источники не читаются фронтом врозь для восстановления истины
- [ ] Для `checkout_pending` и `payment_failed` описано и реализовано явное поведение
- [ ] Исторический успешный payment не даёт ложный `plus_active`, если активного access уже нет
- [ ] Один и тот же orchestration-слой используется billing UI и gated product/report flows
- [ ] Тесты покрывают приоритеты и конфликтующие состояния
- [ ] Тесты написаны и проходят
- [ ] ruff, mypy, eslint — 0 ошибок
- [ ] Документация обновлена

## Примечания

Эта story нужна, чтобы система не сводилась к примитивной логике «есть запись об оплате — значит открой Plus». Коммерческий state должен быть вычисляемым, повторно используемым и одинаковым для всех точек входа.