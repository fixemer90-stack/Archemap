# Account tier role foundation

Status: implemented baseline; gating remains future work
Last updated: 2026-09-01
Scope: account-level Free/Plus status after payment confirmation.

This document defines the first account-tier role layer for Astrotype.

The initial implementation must create and maintain the role/status value, but it must not restrict product behavior yet. Free and Plus users must keep the same functional access until later gating stories explicitly implement differences.

## Decision

Astrotype needs an account-level commercial role in addition to payment records and product entitlements.

The first roles are:

```text
free
plus
```

The role is a user/account status. It is not an admin permission and must not reuse `is_superuser`.

Initial behavior:

```text
new account -> account_tier = free
successful YooKassa payment -> account_tier = plus
failed/cancelled/mismatched payment -> account_tier remains unchanged
```

Important product rule:

```text
In the first implementation, free and plus differ only by displayed/account status.
No API endpoint, report section, calculation, profile action, or frontend route is restricted by account_tier yet.
```

Future stories may use `account_tier` to gate Plus features, but that must be implemented as separate explicit work.

## Why entitlements are not enough

Current payment confirmation already grants product entitlements. Entitlements answer:

```text
Which product access grant exists for this user?
```

Account tier answers:

```text
What is the commercial level/status of this account?
```

Both are useful:

| Layer                  | Example value | Meaning                                                    |
| ---------------------- | ------------- | ---------------------------------------------------------- |
| `users.account_tier`   | `plus`        | Account is commercially upgraded                           |
| `entitlements.product` | `self`        | This payment granted access to the Self product            |
| `payments.status`      | `succeeded`   | A payment attempt was confirmed by provider reconciliation |

For MVP, successful Plus checkout should update both:

```text
payment.succeeded + paid=true
-> payment.status = succeeded
-> payment.paid_at = now()
-> entitlement(product='self', status='active')
-> user.account_tier = plus
```

## Non-goals for the first implementation

The first account-tier implementation must not add behavior differences.

Do not implement yet:

- hiding report sections for Free;
- blocking API routes by `account_tier`;
- reducing report depth for Free;
- limiting profiles/questions/PDF/downloads;
- changing LLM generation behavior by tier;
- forcing paid users into different report schemas;
- admin/RBAC permission checks based on `plus`;
- subscription renewal/downgrade automation unless a separate story owns it.

This keeps the payment-to-role change safe, observable and reversible before product gating is added.

## Data model target

Add a user-level tier field.

Recommended minimal user columns:

| Column                           | Type                             | Default | Meaning                             |
| -------------------------------- | -------------------------------- | ------- | ----------------------------------- |
| `account_tier`                   | string / enum-compatible varchar | `free`  | Current commercial account status   |
| `account_tier_updated_at`        | timestamptz nullable             | null    | Last tier change timestamp          |
| `account_tier_source_payment_id` | UUID nullable FK -> payments.id  | null    | Payment that last upgraded the tier |

Allowed values for the first iteration:

```text
free
plus
```

Recommended invariant:

```text
account_tier = 'free' by default for every user
account_tier = 'plus' only after backend-confirmed payment success or an explicit admin/test fixture action
```

Optional later values such as `trial`, `admin`, `family`, `past_due`, `cancelled`, or `expired` are out of scope until billing/subscription lifecycle requires them.

## Service contract

Add a small service boundary instead of scattering direct user updates through payments code.

Recommended methods:

```python
class AccountTierService:
    async def get_tier(user_id: UUID) -> str: ...

    async def upgrade_to_plus(
        user_id: UUID,
        source_payment_id: UUID,
    ) -> User: ...
```

Initial `upgrade_to_plus` behavior:

- load the user;
- set `account_tier = 'plus'`;
- set `account_tier_updated_at = now()`;
- set `account_tier_source_payment_id = source_payment_id`;
- flush changes;
- remain idempotent if the user is already `plus`.

The service may live under `app.modules.authorization.service` or a dedicated account/billing service. The important rule is that payment handling calls a named account-tier method, not inline ad-hoc column mutation.

## Payment integration

Update the successful YooKassa webhook path.

Current success criteria remain unchanged:

```text
canonical_yookassa.status == 'succeeded'
canonical_yookassa.paid == true
```

After that condition passes, backend should:

1. set local payment status/timestamps;
2. grant product entitlement as today;
3. upgrade account tier to Plus.

Pseudo-flow:

```python
if new_status == "succeeded" and event.get("paid") is True:
    payment.paid_at = now()
    await EntitlementsService(db).grant_paid_product(...)
    await AccountTierService(db).upgrade_to_plus(
        user_id=payment.user_id,
        source_payment_id=payment.id,
    )
```

Do not upgrade tier when:

- provider reconciliation fails;
- payment is not found locally;
- amount/currency/metadata mismatch occurs;
- YooKassa status is `succeeded` but `paid` is not `true`;
- YooKassa status is `pending`, `waiting_for_capture`, or `canceled`.

## API and frontend contract

Expose the tier as account status only.

Minimum current-user response should include:

```json
{
  "id": "...",
  "email": "user@example.com",
  "name": "...",
  "account_tier": "free",
  "is_active": true,
  "is_verified": true
}
```

When upgraded:

```json
{
  "account_tier": "plus"
}
```

Initial frontend behavior:

- show the user's current status as Free or Plus where useful;
- after payment return, refresh current user/access status if available;
- do not unlock/hide/change functional surfaces purely because `account_tier` changed;
- do not implement frontend-only paywall logic.

The UI may display copy such as:

```text
Статус аккаунта: Plus
```

But it must not treat this as an authorization boundary until backend gates exist.

## Authorization rule for this phase

For the first implementation, this is the complete policy:

| User tier | Functional access                                             |
| --------- | ------------------------------------------------------------- |
| `free`    | Same as current product behavior                              |
| `plus`    | Same as current product behavior, plus visible account status |

There is intentionally no feature restriction in this phase.

Later gating must be added through backend policy checks, not by changing this baseline silently.

## Relationship to future access gating

Future stories can build on this foundation:

- `GET /api/v1/billing/access` returns `account_tier`, entitlements and payment state;
- report/product endpoints enforce Plus access for selected sections;
- frontend uses backend-provided access mode (`preview`, `full`, `locked`);
- subscription expiry/downgrade moves accounts back to `free` or another explicit state.

Those later behaviors require their own docs, migrations, services and tests.

## Acceptance criteria for implementation

The account-tier foundation is complete when:

- [x] `users` has an `account_tier` field with default `free`.
- [x] Existing users are backfilled or defaulted to `free` without losing auth/profile/payment data.
- [x] Successful YooKassa payment changes the user's tier to `plus`.
- [x] Failed/cancelled/mismatched/unpaid YooKassa events do not change the user's tier.
- [x] Replayed successful webhook is idempotent and keeps tier as `plus`.
- [x] `/auth/me` or equivalent current-user endpoint returns `account_tier`.
- [ ] Frontend can display Free/Plus status without using it as a paywall.
- [x] Tests prove that Free and Plus currently have no functional access difference caused by the new field.

## Required tests

Backend unit tests:

- user model/default tier is `free`;
- account-tier service upgrades to `plus`;
- account-tier service is idempotent for repeated successful payment;
- successful YooKassa webhook calls tier upgrade;
- failed/cancelled/mismatch/unpaid webhook does not call tier upgrade;
- current-user response includes `account_tier`.

Frontend tests or smoke checks:

- Free user displays Free status if rendered;
- Plus user displays Plus status if rendered;
- no route/page becomes inaccessible only because account tier is `free`.

## Migration safety

The migration must preserve existing platform data:

- users;
- auth tokens/session-related data;
- profiles;
- payments;
- payment_webhooks;
- entitlements;
- v2 report artifacts.

Do not rewrite historical entitlements into roles during the initial migration unless a separate backfill story defines the exact rule. The safe default is:

```text
all existing users -> account_tier = free
new successful payments after deployment -> account_tier = plus
```

If historical paid users must be upgraded, perform an explicit audited backfill based on succeeded payments plus active entitlements.

## Status marker

As of this document, account-tier role foundation is not implemented in code.

Current code has:

- `users.is_active`, `users.is_verified`, `users.is_superuser`;
- payment confirmation through YooKassa reconciliation;
- product entitlement grant after successful payment.

Current code does not have:

- `users.account_tier`;
- Free/Plus account-level role service;
- payment-to-account-tier update;
- `account_tier` in current-user API response.
