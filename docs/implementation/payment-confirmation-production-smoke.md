# Payment confirmation production smoke

Status: runbook ready; live YooKassa merchant-cabinet execution is environment-dependent.

Use this checklist before relying on live payments. Do not treat browser return to `/billing?checkout=return` as proof of payment.

## Prerequisites

- Production/staging backend is deployed behind HTTPS.
- `YOOKASSA_SHOP_ID` is configured in the backend runtime.
- `YOOKASSA_SECRET_KEY` is configured in the backend runtime.
- YooKassa merchant cabinet has webhook URL registered:
  - `https://<api-host>/api/v1/payments/webhooks/yookassa`
- Test user exists and can open `/billing`.
- Operator can read backend logs and database rows for `payments`, `payment_webhooks`, `entitlements`, and `users`.

## HTTPS reachability

```bash
curl -i https://<api-host>/api/v1/health
```

Expected: 2xx health response from the same host that receives YooKassa webhooks.

## Happy-path smoke

1. Log in as the test user.
2. Open `/billing`.
3. Click `Оформить Plus`.
4. Complete YooKassa test payment.
5. Return to `/billing?checkout=return`.
6. Confirm UI shows pending first if webhook is not yet processed, then `Plus активен` after backend confirmation.

Database checks:

```sql
select id, user_id, provider, provider_payment_id, amount, currency, status, paid_at
from payments
where user_id = '<test-user-id>'
order by created_at desc
limit 5;

select provider, event_type, payment_id, processed, processed_at, error_message
from payment_webhooks
where payment_id = '<provider-payment-id>'
order by created_at desc;

select user_id, product, status, source_payment_id, starts_at, expires_at
from entitlements
where user_id = '<test-user-id>'
order by created_at desc;

select id, account_tier
from users
where id = '<test-user-id>';
```

Expected:

- latest payment has `status='succeeded'` and non-null `paid_at`;
- webhook row is stored and processed;
- entitlement exists with `product='self'` and `status='active'`;
- user has `account_tier='plus'`;
- `GET /api/v1/billing/access` returns `access_state='plus_active'`.

## Cancel/failure smoke

1. Start another checkout as the same test user or a fresh free user.
2. Cancel or fail the YooKassa test payment.
3. Return to `/billing?checkout=return`.

Expected:

- no new active entitlement is created from the failed attempt;
- latest payment state is `cancelled`, `failed`, `pending`, or `processing`, never fake-success from the return URL;
- `/billing` shows `Оплата не завершена` or `Проверяем оплату` depending on backend state;
- gated report endpoints do not return full paid payload without active entitlement.

## Log events to inspect

- `payment_created`
- `payment_status_updated`
- `webhook_provider_reconciliation_failed`
- `webhook_payment_mismatch`
- `webhook_succeeded_without_paid_true`
- `account_tier_user_not_found`

## Rollback / incident rule

If webhook delivery or reconciliation fails, do not grant manual access from a frontend screenshot or return URL. Verify provider payment server-to-server and then repair database state with an explicit operator note referencing the YooKassa payment id.
