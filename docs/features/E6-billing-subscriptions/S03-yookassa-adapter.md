# Story E6.S03: YooKassa Adapter

**Feature:** [Billing & Subscriptions](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

YooKassa — PSP для российских платежей. Поддержка карт, SBP, YooMoney.

## Что сделать

- YooKassa provider class (create, get, capture, cancel)
- Payment model (SQLAlchemy)
- Payment webhook handler
- API endpoints (create, list, get, webhook)

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/payments/providers/yookassa.py` | YooKassa provider |
| `backend/app/modules/payments/models.py` | Payment, PaymentWebhook |
| `backend/app/modules/payments/schemas.py` | Pydantic schemas |
| `backend/app/modules/payments/service.py` | PaymentsService |
| `backend/app/modules/payments/router.py` | API endpoints |
| `backend/alembic/versions/a7b8c9d0e1f2_add_payments_tables.py` | Migration |

## API

```
POST /api/v1/payments
  body: { amount, currency, description, return_url, metadata }
  → PaymentResponse с confirmation_url

GET /api/v1/payments
  → PaymentListResponse (pagination)

GET /api/v1/payments/{id}
  → PaymentResponse

POST /api/v1/payments/webhooks/yookassa
  → WebhookEventResponse
```

## Pipeline

```
POST /payments
  → Create Payment record (status=pending)
  → Call YooKassa API (create payment)
  → Update Payment (provider_payment_id, confirmation_url)
  → Return PaymentResponse с confirmation_url

YooKassa webhook
  → Verify signature
  → Parse event
  → Find Payment by provider_payment_id
  → Update status (succeeded/failed/cancelled)
  → Trigger downstream (subscription activation)
```

## Критерии приёмки

- [x] YooKassaProvider: create, get, capture, cancel, verify_webhook
- [x] Payment model: user_id, provider, amount, status, timestamps
- [x] PaymentWebhook model: raw payload storage
- [x] PaymentsService: create, get, list, handle_webhook
- [x] API endpoints: POST, GET list, GET detail, POST webhook
- [x] Alembic migration
- [x] ruff check: 0 ошибок

## Примечания

- YooKassa API: https://yookassa.ru/developers/api
- Webhook signature verification через HMAC-SHA256
- Idempotency через Idempotence-Key header
- Статусы: pending → processing → succeeded/failed/cancelled
