# E6 API contract: billing and payment confirmation

## Status

🟡 Частично реализовано

## Implemented endpoints

### POST /api/v1/payments

Creates a payment attempt for a server-owned product/catalog entry.

Client request must contain only the product identifier and return URL:

```json
{
  "product_id": "self_full",
  "return_url": "https://astrotype.ru/billing?checkout=return"
}
```

The client must not send:

- amount;
- currency;
- description;
- commercial metadata;
- entitlement/account-tier target.

Backend responsibilities:

1. Load product/catalog details server-side.
2. Create local `payments` row with `status='pending'`.
3. Create YooKassa payment with backend-owned amount/currency/metadata.
4. Store provider id and confirmation URL.
5. Return confirmation URL to frontend.

### POST /api/v1/payments/webhooks/yookassa

Receives YooKassa events.

Backend responsibilities:

1. Parse and store raw webhook body.
2. Extract provider payment id.
3. Fetch canonical payment object from YooKassa.
4. Validate provider object against local immutable payment facts.
5. Update local payment status.
6. Grant entitlement only when status is `succeeded` and `paid` is true.

## Reconciliation checks

| Check            | Rule                                                                      |
| ---------------- | ------------------------------------------------------------------------- |
| Provider id      | Provider object id equals local `payments.provider_payment_id`            |
| Amount           | Provider amount equals local amount                                       |
| Currency         | Provider currency equals local currency                                   |
| Local payment id | Provider metadata `payment_id` equals local payment id                    |
| User id          | Provider metadata `user_id` equals local user id                          |
| Product id       | Provider metadata `product_id` equals local payment metadata `product_id` |
| Product          | Provider metadata `product` equals local payment metadata `product`       |
| Paid success     | `status='succeeded'` requires `paid=true`                                 |

## Implemented access-state endpoint

### GET /api/v1/billing/access

Returns the current billing/access state for the authenticated user.

Suggested response:

```json
{
  "account_tier": "free",
  "access_state": "checkout_pending",
  "entitlements": [
    {
      "product": "self",
      "status": "active",
      "starts_at": "2026-08-31T12:00:00Z",
      "expires_at": null
    }
  ],
  "latest_payment": {
    "id": "uuid",
    "product_id": "self_full",
    "status": "pending",
    "created_at": "2026-08-31T12:00:00Z",
    "paid_at": null
  }
}
```

Allowed `access_state` values:

- `free`
- `checkout_pending`
- `plus_active`
- `payment_failed`
- `plus_inactive`

### Astrotype v2 report entitlement gates

Paid self-report payloads require active `self` entitlement:

- `GET /api/v1/astrotype-v2/reports/{report_id}` returns safe locked metadata instead of full paid payload when access is missing.
- `GET /api/v1/astrotype-v2/reports/{report_id}/pdf` returns HTTP 402 when access is missing.
- `GET /api/v1/astrotype-v2/reports/{report_id}/progress` returns HTTP 402 when access is missing.
- `GET /api/v1/astrotype-v2/reports/{report_id}/facts` returns HTTP 402 when access is missing.
- `GET /api/v1/astrotype-v2/reports/{report_id}/infographic` returns HTTP 402 when access is missing.
- `GET /api/v1/astrotype-v2/reports/{report_id}/segments` returns HTTP 402 when access is missing.
- `POST /api/v1/astrotype-v2/reports/{report_id}/regenerate` returns HTTP 402 when access is missing.

Locked response shape:

```json
{
  "access_state": "locked",
  "required_product": "self",
  "reason": "missing_entitlement",
  "upgrade": {
    "title": "Нужен Plus",
    "description": "Полный отчёт открывается после подтверждения оплаты.",
    "href": "/billing"
  }
}
```

### GET /api/v1/payments/{payment_id}

Optional helper if the frontend later needs payment-attempt-specific status. It must not expose provider secrets, raw webhook payloads, or internal reconciliation errors beyond safe user-facing categories.

## Frontend integration rules

- `/billing` creates payment through `POST /api/v1/payments`.
- After return from YooKassa, `/billing?checkout=return` fetches `GET /api/v1/billing/access`.
- Frontend displays backend status; it does not infer success from URL state.
- If status is pending, frontend can poll for a bounded time.
- If status is failed/cancelled, frontend offers retry.
- If status is active, frontend shows Plus/account access as active.

## Error and safety rules

- Invalid webhook JSON returns HTTP 400.
- Provider reconciliation failure must not activate access.
- Metadata mismatch must not activate access.
- `succeeded` without `paid=true` must not activate access.
- Duplicate webhook delivery must be idempotent.
- Secrets and full payment-card data must never be returned to frontend or committed to docs.
