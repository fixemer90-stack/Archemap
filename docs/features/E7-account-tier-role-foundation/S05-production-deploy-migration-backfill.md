# S05: Production deploy, migration and paid-user backfill

## Status

⬜ Не начато

## Context

The code is implemented in `main`, but production observed on 2026-09-02 still did not have `users.account_tier` or `GET /api/v1/billing/access`. Production needs a deploy, database migration and a narrow paid-user audit/backfill.

## Source architecture

- `../../architecture/account-tier-role-foundation.md`
- Parent feature: `./FEATURE.md`
- Payment smoke runbook: `../../implementation/payment-confirmation-production-smoke.md`

## Files/targets affected

- production backend container/image
- production frontend container/image
- production PostgreSQL migration state
- `users.account_tier`
- `payments`
- `entitlements`
- `payment_webhooks`

## What to do

1. Deploy the latest `main` that contains E6/E7 account-tier code.
2. Run Alembic migrations against production database.
3. Verify `users.account_tier` exists and defaults to `free`.
4. Verify `GET /api/v1/billing/access` exists on production.
5. Audit existing paid users from active entitlements and succeeded payments.
6. Backfill `users.account_tier='plus'` only for users with:
   - local `payments.status='succeeded'`;
   - non-null `payments.paid_at`;
   - active `entitlements.product='self'` sourced from that payment.
7. Verify `fixemer90@gmail.com` and `balthier90@mail.ru` both have active `self` entitlement and expected account tier.
8. Run one new payment smoke after deploy to prove webhook -> payment -> entitlement -> tier.

## Acceptance criteria

- [ ] Production is running a build that includes `GET /api/v1/billing/access`.
- [ ] Production migration adds `users.account_tier` without data loss.
- [ ] All existing users have non-null `account_tier`.
- [ ] Existing paid users are backfilled to `plus` only from succeeded payment + active entitlement evidence.
- [ ] Existing free users remain `free`.
- [ ] `fixemer90@gmail.com` and `balthier90@mail.ru` are verified after backfill.
- [ ] New YooKassa payment upgrades both entitlement and tier through normal webhook processing.
- [ ] Rollback plan is recorded before production mutation.

## Verification

```sql
select column_name, column_default, is_nullable
from information_schema.columns
where table_name = 'users' and column_name = 'account_tier';

select email, account_tier
from users
where email in ('fixemer90@gmail.com', 'balthier90@mail.ru');

select u.email, p.status, p.paid_at, e.product, e.status
from users u
join payments p on p.user_id = u.id
left join entitlements e on e.source_payment_id = p.id
where u.email in ('fixemer90@gmail.com', 'balthier90@mail.ru')
order by u.email, p.created_at desc;
```

HTTP smoke:

```bash
curl -i https://astrotype.ru/api/v1/billing/access
```

Authenticated users should receive backend-owned access state; unauthenticated users should receive auth error, not 404.
