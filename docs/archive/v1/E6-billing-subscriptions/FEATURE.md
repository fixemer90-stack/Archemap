# Feature E6: Billing & Subscriptions

## Цель

Перевести Astrotype из режима «все отчёты доступны одинаково» в понятную продуктовую модель Free vs Plus.

На текущем фронтенде уже есть визуальная заглушка `/billing`, которая обещает единую подписку Plus с набором услуг. Для реализации нужен не просто checkout, а сквозной контракт:

- что именно получает Free-пользователь;
- что именно открывает Plus;
- где проходит граница между teaser/preview и полным отчётом;
- как entitlement появляется после оплаты;
- как backend и frontend синхронно принимают решение, что показывать пользователю.

MVP этой feature — не «все возможные PSP и mobile billing», а рабочее разделение бесплатного и платного флоу вокруг одной коммерческой модели Astrotype Plus.

## Scope MVP

В первой реализации E6 покрывает:

- единый коммерческий план `plus_monthly`;
- оплату через YooKassa;
- backend-owned каталог и цены;
- entitlement/access state для пользователя;
- разделение preview/full в отчётах и продуктах;
- billing/account UI для текущего access state;
- upgrade/retry/return-from-payment flow.

Вне MVP и остаётся будущим этапом:

- несколько PSP одновременно как обязательная часть первой поставки;
- App Store / Google Play;
- сложные bundle-планы и многоуровневая тарифная сетка;
- отдельные подписки на каждый vertical.

## Зависимости

`E5`, `E9`, `E10`, `E11`

- `E5` — reports API и генерация отчётов
- `E9` / frontend report pages — точки входа и экраны
- `E10` — UX отчётов, где нужен preview/full split
- `E11` — narrative-first Self report, который должен уважать платный доступ и fallback-пути

## Документы feature

- Workflow: [WORKFLOW.md](Archemap/docs/features/v1/E6-billing-subscriptions/WORKFLOW.md)
- API/state machine: [API.md](Archemap/docs/features/v1/E6-billing-subscriptions/API.md)
- SRS: [`docs/SRS/SRS-E6-billing-subscriptions.md`](SRS-E6-billing-subscriptions.md)

## Критерии приёмки

- [ ] У системы есть единый server-owned план `plus_monthly` с фактической ценой и составом доступа, совпадающим с billing page
- [ ] Free flow формализован: регистрация, профиль, free-preview, CTA на апгрейд
- [ ] Plus flow формализован: checkout, возврат, webhook, entitlement activation, повторная проверка доступа
- [ ] Backend не доверяет фронтенду цену, валюту и состав услуг; клиент отправляет только `product_id/plan_id`
- [ ] Report/product APIs умеют различать `preview` и `full` без утечки платного контента в free-ответы
- [ ] Frontend умеет рендерить три ключевых состояния: free, checkout/pending, plus-active
- [ ] Direct navigation на `/report/...` и `/products/...` не обходит платные ограничения
- [ ] Ошибка или задержка оплаты не ломает бесплатный доступ и не создаёт двусмысленное состояние интерфейса

## Текущие разрывы, которые нужно закрыть

1. Frontend уже продаёт «999 ₽ / месяц» и единый Plus, но backend catalog пока описывает разовые продукты `self_full` и `career_full`.
2. `/billing` пока только визуальный экран без checkout и без чтения текущего access state.
3. Entitlement в backend уже существует как primitive, но нет полного access contract для preview/full flow.
4. Story `S03` реализовала базовый YooKassa payment path, но её документация устарела относительно реального контракта `product_id` и текущей webhook-проверки.
5. Нет отдельного explainer-документа, который бы описывал реальный user journey от free-preview до unlock.

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [Каталог планов и access matrix: единый Plus-план, server-owned цена, состав услуг, согласование с billing UI](S01-plan-catalog.md) | ⬜ Не начато |
| S02 | [Lifecycle доступа: free → checkout_pending → plus_active → plus_inactive, webhook-driven переходы и правила возврата в UI](S02-subscription-lifecycle.md) | ⬜ Не начато |
| S03 | [YooKassa adapter baseline: create payment, reconciliation webhook, entitlement activation primitive](S03-yookassa-adapter.md) | ✅ Готово |
| S04 | [Checkout/session integration: billing entrypoint, return_url, payment status refresh, account summary API](S04-cloudpayments-adapter.md) | ⬜ Не начато |
| S05 | [Paid access orchestration: синхронизация payment/subscription/account state и ошибки оплаты](S05-stripe-adapter.md) | ⬜ Не начато |
| S06 | [Report/backend gating: preview/full contract, locked sections, upgrade_required metadata](S06-webhook-handling.md) | ⬜ Не начато |
| S07 | [Entitlement engine: backend policy checks для verticals, reports и CTA-state](S07-entitlement-engine.md) | ⬜ Не начато |
| S08 | [Frontend billing and upsell flow: /billing, post-payment refresh, report paywall, retry/return states](S08-in-app-billing.md) | ⬜ Не начато |

## Порядок реализации

1. S01 — зафиксировать коммерческую модель и access matrix
2. S02 — определить state machine доступа
3. S03 — опереться на существующий YooKassa baseline
4. S04–S05 — подключить checkout/account state
5. S06–S07 — включить backend gating
6. S08 — довести frontend flow до end-to-end user journey

## Реализация

Пока в коде реально существуют только базовые строительные блоки:

- `frontend/src/app/(dashboard)/billing/page.tsx` — визуальная страница Free/Plus без backend-интеграции
- `backend/app/modules/payments/*` — payment API и YooKassa provider
- `backend/app/modules/catalog/service.py` — server-owned product catalog, но ещё не в целевом Plus-виде
- `backend/app/modules/authorization/models.py` и `service.py` — primitive entitlement storage/grant

Именно поэтому следующая задача — не «сразу подключить кнопку оплаты», а сначала закрепить документационный контракт free/paid flow и только потом реализовывать его слоями.
