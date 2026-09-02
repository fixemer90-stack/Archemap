# SRS-E7: Account tier role foundation

## 1. Introduction

### Purpose

Define the requirements for Astrotype account-level Free/Plus status and its relationship to YooKassa payment confirmation, billing access state and product entitlements.

### Scope

This SRS covers:

- user account tier data model;
- tier upgrade after backend-confirmed payment;
- tier visibility in account/billing APIs;
- frontend status display;
- authorization boundary between tier and entitlements;
- production deploy, migration and paid-user backfill requirements.

### References

| Document                          | Path                                                           |
| --------------------------------- | -------------------------------------------------------------- |
| Architecture                      | `docs/architecture/account-tier-role-foundation.md`            |
| Feature                           | `docs/features/E7-account-tier-role-foundation/FEATURE.md`     |
| Billing feature                   | `docs/features/E6-billing-subscriptions/FEATURE.md`            |
| Payment confirmation architecture | `docs/architecture/current-payment-confirmation-flow.md`       |
| Production payment smoke          | `docs/implementation/payment-confirmation-production-smoke.md` |

## 2. Overall description

Astrotype stores commercial account status separately from paid product access grants.

```text
account_tier = account/commercial status
entitlement = product access proof
payment = provider-confirmed transaction state
```

The first account tiers are:

```text
free
plus
```

The tier must not become an admin permission or a frontend-only paywall. Paid product access must use backend entitlement checks.

## 3. Functional requirements

### FR-E7.1 User tier model

The system shall persist `users.account_tier` for each user.

Acceptance criteria:

- [x] New users default to `free`.
- [x] Existing users are preserved by migration.
- [x] First allowed values are `free` and `plus`.
- [x] Tier is not derived from `is_superuser`.
- [x] Production database has the deployed column after migration.

### FR-E7.2 Tier service boundary

The system shall update account tier through a named service boundary.

Acceptance criteria:

- [x] Code has an account-tier service method for upgrade to Plus.
- [x] Upgrade is idempotent.
- [x] Payment service does not scatter direct tier mutations across unrelated paths.

### FR-E7.3 Payment-to-tier upgrade

The system shall upgrade account tier only after canonical YooKassa reconciliation confirms successful paid payment.

Acceptance criteria:

- [x] `status == succeeded` and `paid == true` upgrades the account to `plus`.
- [x] Failed/cancelled/pending/unpaid events do not upgrade tier.
- [x] Metadata/amount/currency mismatch does not upgrade tier.
- [x] Replayed successful webhook keeps safe final state.

### FR-E7.4 API visibility

The system shall expose account tier through backend-owned account/access APIs.

Acceptance criteria:

- [x] Current-user response exposes account tier in the current codebase.
- [x] Billing access response exposes account tier in the current codebase.
- [x] API response does not imply payment success from browser return URL.
- [x] Production deployed endpoint returns auth-gated access state instead of 404.

### FR-E7.5 Frontend status behavior

The frontend shall show Free/Plus and billing access state from backend APIs.

Acceptance criteria:

- [x] Billing return UX refreshes backend state after checkout return.
- [x] Frontend does not mark the user paid from query params alone.
- [x] Frontend can render Free/Plus status copy.
- [x] Frontend does not unlock paid product payload by local tier state.

### FR-E7.6 Authorization boundary

The system shall use active entitlements for paid product/report access.

Acceptance criteria:

- [x] Paid report gate checks active matching entitlement.
- [x] Missing/inactive/expired/mismatched entitlement returns locked response.
- [x] Locked response contains no full paid report payload.
- [x] Tier alone is not sufficient proof of paid product access.

### FR-E7.7 Production migration and backfill

Production rollout shall safely deploy the tier column and backfill only confirmed paid users.

Acceptance criteria:

- [x] Production migration is applied.
- [x] Existing paid users are identified by succeeded payment plus active entitlement.
- [x] Existing free users remain `free`.
- [x] `fixemer90@gmail.com` and `balthier90@mail.ru` are verified after backfill.
- [ ] New payment smoke proves webhook -> payment -> entitlement -> tier.

## 4. Non-functional requirements

### Safety

- Migration must not delete or rewrite user/profile/payment/report artifacts.
- Backfill must be auditable and narrow.
- Frontend must not own paid-state truth.

### Security

- Tier must not be treated as admin/RBAC permission.
- Paid payload gates must run server-side.
- Payment card data must not be stored.

### Observability

- Payment and webhook state must remain inspectable through payment/webhook rows.
- Production smoke must record whether automatic YooKassa delivery works without manual webhook posting.

## 5. Data model

Primary field:

| Table   | Field          | Type                           | Default | Meaning                   |
| ------- | -------------- | ------------------------------ | ------- | ------------------------- |
| `users` | `account_tier` | varchar/string-compatible enum | `free`  | Account commercial status |

Related proof records:

| Table              | Field                                      | Meaning                          |
| ------------------ | ------------------------------------------ | -------------------------------- |
| `payments`         | `status`, `paid_at`, `provider_payment_id` | Payment confirmation state       |
| `entitlements`     | `product`, `status`, `source_payment_id`   | Product access grant             |
| `payment_webhooks` | `event`, `processed`, `error_message`      | Provider notification processing |

## 6. API specification

### Current user

The authenticated current-user response should include account tier.

```json
{
  "id": "...",
  "email": "user@example.com",
  "name": "...",
  "account_tier": "free"
}
```

### Billing access

The billing access response should include backend-owned access state.

```json
{
  "access_state": "plus_active",
  "account_tier": "plus",
  "entitlements": [
    {
      "product": "self",
      "status": "active"
    }
  ],
  "latest_payment": {
    "status": "succeeded"
  }
}
```

Allowed access states for the first implementation:

```text
free
checkout_pending
plus_active
payment_failed
plus_inactive
```

## 7. Verification criteria

Local code/docs verification:

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_payments.py tests/unit/test_auth_service.py tests/unit/test_dependencies.py -q
./.venv/bin/ruff check app/modules/users app/modules/auth app/modules/authorization app/modules/payments app/modules/billing tests/unit/test_payments.py
./.venv/bin/python -m mypy .

cd ../frontend
node scripts/check-billing-ux.mjs
npx eslint src/app/\(dashboard\)/billing/page.tsx src/lib/api/payments.ts scripts/check-billing-ux.mjs
npx tsc --noEmit --pretty false
```

Docs verification:

```bash
cd frontend
npx prettier --check ../docs/features/E7-account-tier-role-foundation/*.md ../docs/SRS/SRS-E7-account-tier-role-foundation.md ../docs/architecture/account-tier-role-foundation.md ../docs/features/README.md
cd ..
git diff --check -- docs/features/E7-account-tier-role-foundation docs/SRS/SRS-E7-account-tier-role-foundation.md docs/architecture/account-tier-role-foundation.md docs/features/README.md
```

## 8. Dependencies

- E6 billing/payment confirmation lifecycle.
- YooKassa provider reconciliation.
- Existing auth/current-user infrastructure.
- Existing entitlement model and paid report gates.
- Production deploy/migration process.

## 9. Rollout and risks

### Rollout

1. Deploy latest main. ✅ Done on 2026-09-02; `.deploy-sha = f17a23a3a2df05fedc4fe0057873277e95826f4f`.
2. Apply migration. ✅ Alembic reached `d3e4f5a6b7c8`.
3. Verify endpoint availability. ✅ `/api/v1/billing/access` returns auth error instead of 404 for unauthenticated requests.
4. Run paid-user audit/backfill. ✅ `fixemer90@gmail.com` and `balthier90@mail.ru` are `plus` from succeeded payment + active `self` entitlement.
5. Run new payment smoke. ⬜ Pending; requires a fresh YooKassa checkout and automatic webhook delivery proof.

### Risks

| Risk                                                | Mitigation                                                             |
| --------------------------------------------------- | ---------------------------------------------------------------------- |
| Production stays on old backend                     | S05 keeps production deploy/migration open                             |
| Historical paid users remain `free` after migration | audited backfill based on succeeded payment + active entitlement       |
| Tier is mistaken for authorization                  | S04 documents and tests entitlement-only gates                         |
| YooKassa webhook not delivered automatically        | production smoke/runbook verifies merchant-cabinet delivery separately |
