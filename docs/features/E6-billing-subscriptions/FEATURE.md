# Feature E6: Billing & Subscriptions

## Цель

Подписки, платежи через PSP (YooKassa, CloudPayments, Stripe), webhook-driven lifecycle, entitlement engine.

## Зависимости

`E5`

## Критерии приёмки

- [ ] Каталог планов: цена, интервал, trial, привязка к вертикалям
- [ ] Lifecycle: trial → active → past_due → cancelled → expired
- [ ] YooKassa: карты, SBP, автоплатежи
- [ ] CloudPayments: виджет, рекуррентные платежи
- [ ] Stripe: Checkout, Billing Portal (международный)
- [ ] Webhook inbox: идемпотентность, верификация подписи
- [ ] Entitlement engine: has_access(user, vertical) → bool

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [Каталог планов: CRUD, цена, интервал, trial, привязка к вертикалям, bundle-планы](S01-plan-catalog.md) | ⬜ Не начато |
| S02 | [Жизненный цикл: state machine (trial→active→past_due→cancelled→expired), webhook-driven transitions](S02-subscription-lifecycle.md) | ⬜ Не начато |
| S03 | [YooKassa: создание платежа, подтверждение, сохранение способа оплаты, автоплатежи, 54-ФЗ чеки](S03-yookassa-adapter.md) | ✅ Готово |
| S04 | [CloudPayments: виджет, рекуррентные планы, HMAC-валидация, X-Request-ID, онлайн-чеки](S04-cloudpayments-adapter.md) | ⬜ Не начато |
| S05 | [Stripe: Checkout session, Billing Portal, Smart Retries, invoice lifecycle](S05-stripe-adapter.md) | ⬜ Не начато |
| S06 | [Webhook inbox: верификация подписи, raw-event storage, дедупликация, быстрый 2xx, idempotent processing](S06-webhook-handling.md) | ⬜ Не начато |
| S07 | [Entitlement engine: проверка доступа к вертикалям, free-план = preview only, middleware](S07-entitlement-engine.md) | ⬜ Не начато |
| S08 | [In-app billing: мост для Google Play Billing и App Store, receipt verification](S08-in-app-billing.md) | ⬜ Не начато |
