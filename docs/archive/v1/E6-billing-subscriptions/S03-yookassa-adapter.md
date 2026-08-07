# Story E6.S03: YooKassa adapter baseline

Feature: [Billing & Subscriptions](Archemap/docs/features/v1/E6-billing-subscriptions/FEATURE.md)
Статус: ✅ Готово

## Контекст

YooKassa — primary PSP для российского платежного flow в текущем Astrotype MVP. Эта story закрыла базовый payment layer, на который теперь должен опираться Free vs Plus access flow.

Важно: story закрывает именно baseline create/list/get/webhook path, а не весь конечный продуктовый сценарий Plus-подписки.

## Что сделано

- реализован `YooKassaProvider` для create/get/cancel/capture;
- добавлены модели `Payment` и `PaymentWebhook`;
- добавлены payment endpoints: create/list/detail/webhook;
- payment creation переведён на server-owned `product_id` вместо client-owned `amount/currency`;
- webhook-путь использует provider reconciliation и может активировать entitlement при `payment.succeeded`.

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/payments/providers/yookassa.py` | YooKassa provider |
| `backend/app/modules/payments/models.py` | Payment, PaymentWebhook |
| `backend/app/modules/payments/schemas.py` | CreatePaymentRequest, responses |
| `backend/app/modules/payments/service.py` | Create payment, webhook reconciliation, entitlement grant |
| `backend/app/modules/payments/router.py` | API endpoints |
| `backend/app/modules/catalog/service.py` | Server-owned product catalog lookup |
| `backend/app/modules/authorization/service.py` | `grant_paid_product(...)` |
| `backend/alembic/versions/a7b8c9d0e1f2_add_payments_tables.py` | Payments migration |
| `backend/alembic/versions/b2c3d4e5f6g7_add_entitlements_table.py` | Entitlements migration |

## Актуальный API baseline

```http
POST /api/v1/payments
  body: { product_id, return_url }
  -> PaymentResponse с confirmation_url

GET /api/v1/payments
  -> PaymentListResponse

GET /api/v1/payments/{id}
  -> PaymentResponse

POST /api/v1/payments/webhooks/yookassa
  -> WebhookEventResponse
```

## Текущий pipeline

```text
POST /payments
  -> lookup product in backend catalog
  -> create local Payment(status=pending)
  -> call YooKassa create payment
  -> save provider_payment_id + confirmation_url
  -> return PaymentResponse

YooKassa webhook
  -> store raw webhook
  -> fetch canonical payment object from YooKassa
  -> reconcile id/amount/currency/metadata
  -> update local Payment status
  -> on succeeded + paid=true grant Entitlement
```

## Критерии приёмки

- [x] YooKassa provider для create/get/cancel/capture существует
- [x] Payment и PaymentWebhook модели существуют
- [x] Payment API endpoints существуют
- [x] Create payment использует server-owned `product_id`
- [x] Webhook reconciliation обновляет payment status
- [x] Успешный webhook может активировать entitlement
- [x] Alembic migration для payment layer существует

## Что story ещё не закрывает

- единый продуктовый контракт `plus_monthly`;
- billing/account access-state endpoint;
- preview/full gating для report APIs;
- frontend post-payment refresh flow;
- полноценный recurring subscription lifecycle.

## Примечания

Ранее документация этой story отставала от кода: описывала client-owned `amount/currency` и signature-verification flow, тогда как текущая реализация уже работает через `product_id` и provider reconciliation. Этот документ приведён в соответствие с текущим baseline.
