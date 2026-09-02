# S05: Production deploy, migration and paid-user backfill

## Status

🟡 Production deploy/migration/backfill verified; new payment smoke pending

## Context

The code is implemented in `main`. Production was behind on 2026-09-02, then the latest source was deployed to `/opt/astrotype`, the backend restarted, Alembic reached `d3e4f5a6b7c8`, and the narrow paid-user backfill was applied for confirmed paid users.

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

## Rollback plan recorded before production mutation

Recorded: 2026-09-02T19:00:32Z.

Before deploy/migration/backfill, create a production PostgreSQL dump on the server and preserve the previous `/opt/astrotype` source tree by relying on the existing Docker images/containers until the new build is healthy.

Rollback path:

1. stop the newly built services if health checks fail;
2. restore the previous source tree or previous image set from Docker cache;
3. run `docker compose -f docker-compose.prod.yml up -d backend worker frontend`;
4. if the migration/backfill corrupted tier data, restore the PostgreSQL dump captured immediately before deploy;
5. verify `https://astrotype.ru/api/v1/health` before re-opening payment smoke.

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

- [x] Production is running a build that includes `GET /api/v1/billing/access`.
- [x] Production migration adds `users.account_tier` without data loss.
- [x] All existing users have non-null `account_tier`.
- [x] Existing paid users are backfilled to `plus` only from succeeded payment + active entitlement evidence.
- [x] Existing free users remain `free`.
- [x] `fixemer90@gmail.com` and `balthier90@mail.ru` are verified after backfill.
- [ ] New YooKassa payment upgrades both entitlement and tier through normal webhook processing.
- [x] Rollback plan is recorded before production mutation.

## Production verification evidence

Recorded on 2026-09-02 after deploy/backfill:

- pre-mutation dump: `/opt/astrotype/backups/pre-e7-tier-20260902T193726Z.sql` (`9,790,184` bytes);
- `.deploy-sha`: `f17a23a3a2df05fedc4fe0057873277e95826f4f`;
- backend local health: `{"status":"ok","database":"ok","redis":"ok"}`;
- backend container: healthy after restart;
- worker/frontend containers: restarted successfully;
- Alembic version: `d3e4f5a6b7c8`;
- `users.account_tier`: exists, default `'free'`, non-null;
- user counts after backfill: `14` total, `0` null tiers, `12` free, `2` plus;
- `balthier90@mail.ru`: `account_tier=plus`, provider payment `322a72ec-000f-5001-9000-194494557f3e`, payment `succeeded`, active `self` entitlement;
- `fixemer90@gmail.com`: `account_tier=plus`, provider payment `322a6fd6-000f-5000-b000-14a40d255910`, payment `succeeded`, active `self` entitlement;
- unauthenticated public `GET https://astrotype.ru/api/v1/billing/access`: `401 Not authenticated`, proving the deployed endpoint is present and auth-gated rather than missing/404.

Fresh automatic YooKassa delivery smoke is still pending because it requires a new checkout/payment cycle.

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
