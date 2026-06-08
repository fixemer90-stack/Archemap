# Story E6.S02: Lifecycle доступа и state machine Free/Plus

Feature: [Billing & Subscriptions](FEATURE.md)
Статус: ⬜ Не начато

## Контекст

Даже при существующем payment API система всё ещё не знает, как формально жить между состояниями:

- пользователь только бесплатный;
- пользователь уже ушёл в checkout;
- оплата ещё подтверждается;
- доступ активирован;
- оплата не удалась или доступ больше не активен.

Без этой story frontend будет гадать по косвенным признакам, а backend не сможет стабильно управлять preview/full flow.

## Что сделать

1. Зафиксировать список access states для MVP:
   - `free`
   - `checkout_pending`
   - `plus_active`
   - `payment_failed`
   - `plus_inactive`
2. Описать переходы между ними на backend-событиях.
3. Определить, как `payments`, `entitlements` и будущие `subscriptions` складываются в один access state для UI.
4. Подготовить account/billing summary endpoint, который отдаёт это состояние явно.
5. Определить поведение после return from PSP, когда webhook ещё не успел обработаться.

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/payments/service.py` | Payment status и post-webhook orchestration |
| `backend/app/modules/authorization/service.py` | Источник факта активного entitlement |
| `backend/app/modules/subscriptions/*` | Если потребуется явная subscription model для recurring state |
| `backend/app/modules/billing/*` | Summary/access-state endpoint |
| `docs/features/E6-billing-subscriptions/WORKFLOW.md` | Пользовательский сценарий |
| `docs/features/E6-billing-subscriptions/API.md` | State machine contract |
| `docs/SRS/SRS-E6-billing-subscriptions.md` | Формальный lifecycle |

## Критерии приёмки

- [ ] Определён единый набор access states для backend и frontend
- [ ] Для каждого состояния описан источник истины и allowed UI behavior
- [ ] Return from PSP без подтверждённого entitlement не считается `plus_active`
- [ ] Ошибка оплаты возвращает пользователя в Free-compatible flow, а не в подвешенное состояние
- [ ] Есть endpoint или service contract для чтения current access state
- [ ] Тесты покрывают основные переходы состояния
- [ ] Тесты написаны и проходят
- [ ] ruff, mypy, eslint — 0 ошибок
- [ ] Документация обновлена

## Примечания

На первом этапе допускается, что recurring billing и полноценная subscription model ещё не завершены. Но даже в таком случае пользователю и frontend нужен единый state machine contract.
