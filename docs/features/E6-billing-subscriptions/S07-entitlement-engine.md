# Story E6.S07: Entitlement engine и backend policy checks

Feature: [Billing & Subscriptions](FEATURE.md)
Статус: ⬜ Не начато

## Контекст

В коде уже есть базовая сущность `Entitlement` и primitive `grant_paid_product(...)`, но этого ещё недостаточно для реального разделения Free и Plus.

Нужен policy-слой, который умеет ответить:

- есть ли у пользователя доступ к `self` full;
- можно ли открыть `career`;
- должен ли report endpoint вернуть `preview`, `full` или `locked`;
- какие locked sections показывать вместе с CTA.

Именно эта story превращает entitlement storage в реальный access engine.

## Что сделать

1. Ввести единый backend policy-check для product access.
2. Научить policy-check различать `preview`, `full` и `locked`.
3. Применить policy-check в report/product endpoints.
4. Исключить ситуацию, когда полный контент отдаётся бесплатно и лишь скрывается на frontend.
5. Подготовить response metadata для paywall UX:
   - `access_mode`
   - `upgrade_required`
   - `locked_sections`
   - `billing_cta`

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/authorization/models.py` | Entitlement storage |
| `backend/app/modules/authorization/service.py` | Policy checks и grant resolution |
| `backend/app/modules/reports/service.py` | Применение access policy к report data |
| `backend/app/modules/reports/router.py` | Возврат preview/full contract |
| `backend/app/modules/reports/schemas.py` | Pydantic response fields для access metadata |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Рендер locked/full состояний |
| `docs/features/E6-billing-subscriptions/API.md` | Access contract |

## Критерии приёмки

- [ ] Есть backend service/function, которая определяет access mode пользователя по продукту
- [ ] Self-report умеет возвращаться как `preview` и как `full`
- [ ] Career без платного доступа возвращает `locked`-mode, а не случайный full payload
- [ ] API возвращает metadata для upgrade UX (`upgrade_required`, `locked_sections`, `billing_cta`)
- [ ] Direct navigation на report/product pages не обходит access restrictions
- [ ] Full paid sections не утекли в free API response
- [ ] Тесты покрывают policy-check и gated responses
- [ ] Тесты написаны и проходят
- [ ] ruff, mypy, eslint — 0 ошибок
- [ ] Документация обновлена

## Примечания

Это одна из ключевых MVP stories. Без неё даже корректная оплата не даёт гарантии, что продукт действительно разделён на Free и Plus на уровне данных, а не только на уровне интерфейсных обещаний.
