# E7 account tier role foundation — discrepancy audit

## Purpose

This register records cross-Story discrepancies found while re-auditing E7 on 2026-09-26. Story acceptance criteria remain the source of truth; this file explains why a Story is closed or partial and what exact proof is required to close the remaining gaps.

## Verified baseline

Local repository:

- audited commit: `2c8804f` on `main`, synchronized with `origin/main` before documentation edits;
- worktree was clean at audit start;
- E7 implementation commits are ancestors of the current production deploy marker;
- targeted backend verification: 44 payment/auth/dependency tests passed;
- targeted Ruff and mypy checks passed;
- frontend billing structure check, ESLint and TypeScript checks passed.

Current production readback on 2026-09-26:

- `.deploy-sha`: `0a498a090d5c258480be363231f2611f869077ff`;
- backend healthy; worker running; public health reports database and Redis healthy;
- Alembic current/head: `a6b7c8d9e0f1`;
- `users.account_tier`: `varchar(20)`, default `free`, non-null;
- users: 15 total, 10 `free`, 5 `plus`, 0 null, 0 values outside `free`/`plus`;
- no current user/product has more than one entitlement row;
- the historical pre-E7 dump path recorded in S05 is no longer present on the server.

Production payment evidence is read-only. Database rows prove resulting payment/entitlement/tier state, but do not by themselves prove that YooKassa delivered a webhook automatically.

## Summary status

| Story | Audit status | Reason                                                                                                                                                                     |
| ----- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S01   | 🟡 Partial   | Column/migration are deployed, but `free`/`plus` is not enforced by a database constraint or typed application boundary.                                                   |
| S02   | 🟡 Partial   | Payment integration is implemented; exact replay/idempotence regression tests required by the architecture are missing.                                                    |
| S03   | ✅ Verified  | Current-user/billing APIs and frontend status consumers exist; production route is deployed and auth-gated.                                                                |
| S04   | 🟡 Partial   | Entitlement gates exist, but the reader assumes at most one matching active row although the schema permits several payments for the same product.                         |
| S05   | 🟡 Partial   | Deploy/migration/backfill are verified; automatic YooKassa webhook delivery is still unproven and current rows show fallback reconciliation for later successful payments. |

## Implementation and test-contract gaps

| Story | Discrepancy                                                                                                                                                                                                    | Impact                                                                                                                                                                                                                                                                               | Closure proof                                                                                                                                                               |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S01   | `account_tier` is a plain `varchar(20)` in both ORM and migration. Production has no check constraint mentioning `account_tier`; `UserResponse.account_tier` is also a plain string.                           | A direct database/admin/import write can persist a value outside `free`/`plus`, contradicting the documented allowed-value invariant. Current production data is clean, but the invariant is not enforced.                                                                           | Add a safe migration constraint or enum-compatible validation, add model/schema tests for accepted and rejected values, deploy it, and read back the production constraint. |
| S02   | Existing tests cover successful upgrade, mismatch, unpaid success and provider failure, but do not execute the same successful webhook twice or directly test repeated `AccountTierService.upgrade_to_plus()`. | Idempotence is supported by code inspection, but the required regression contract can regress without a failing test.                                                                                                                                                                | Add a replay test proving one effective entitlement/tier outcome and a direct repeated-upgrade service test; run them in CI.                                                |
| S04   | `EntitlementsService.has_active_product_access()` uses `scalar_one_or_none()` for a query whose schema is unique only by `source_payment_id + product`, not by `user_id + product`.                            | A user who legitimately buys the same product more than once can have several matching rows and receive `MultipleResultsFound`/HTTP 500 instead of a stable access decision. Production currently has a maximum of one row per user/product, so this is a latent implementation gap. | Change the query to an existence/ordered/limited access check that handles multiple rows and add tests covering multiple active rows plus mixed expired/active rows.        |

## Live and rollout evidence gaps

### S05 automatic webhook delivery

The final S05 criterion remains open.

Current production rows after the original 2026-09-02 rollout show:

- the 2026-09-03 succeeded payment for the documented test account has a processed `payment.succeeded` webhook, but session evidence records that this webhook was manually replayed after the provider payment had already succeeded;
- succeeded payments on 2026-09-07 and 2026-09-16 produced active `self` entitlements and Plus state without corresponding `payment_webhooks` rows;
- those later chains therefore prove provider reconciliation fallback, not normal automatic YooKassa notification delivery.

Impact: checkout can eventually activate access when a client requests billing/report state, but E7 still has no proof that the configured merchant notification path performs `YooKassa -> automatic webhook -> canonical reconciliation -> payment -> entitlement -> tier` without manual replay or read-triggered fallback.

Closure proof:

1. Register/verify the production webhook URL and required payment events in the active YooKassa shop.
2. Create a fresh checkout after that verification.
3. Complete payment without manually posting/replaying a notification and without relying on billing/report fallback first.
4. Record provider payment id and timestamps, a new processed `payment.succeeded` webhook row, local succeeded payment with `paid_at`, active entitlement sourced from that payment, Plus tier for the same user, and authenticated billing state `plus_active`.
5. Confirm logs have no provider reconciliation or payload mismatch error for that payment.

### Historical rollback artifact

S05 records that `/opt/astrotype/backups/pre-e7-tier-20260902T193726Z.sql` existed immediately after rollout. The 2026-09-26 readback reports that this path is now missing. This does not undo the historical pre-mutation procedure, but the document must not present the file as a currently retained rollback artifact.

Closure proof: either restore the retained dump from the backup system and document its current location/checksum, or explicitly accept the retention loss and point S05 to the current backup/restore policy.

## Documentation drift corrected

- S01 no longer says the production migration is pending.
- S03 no longer says production deploy is pending.
- Parent and child statuses now reflect S01, S02, S04 and S05 gaps instead of showing all implementation Stories as fully closed.
- Historical 2026-09-02 counts/deploy evidence are labeled as historical, separate from the 2026-09-26 current readback.
- The parent Feature links this consolidated register.

## Closure order

1. Make the entitlement access query safe for multiple rows and add S04 regression tests.
2. Enforce the S01 `free`/`plus` value invariant with migration and tests.
3. Add S02 replay/direct-service regression tests.
4. Repair/verify YooKassa automatic notification delivery and run one fresh S05 checkout smoke.
5. Resolve the historical backup retention note.
6. Re-run targeted backend/frontend tests, production readback, exact-path Markdown checks and exact-SHA CI before closing E7.

## Closure rule

Code inspection or static source-marker scripts can support implementation claims, but they do not substitute for the exact missing regression tests. Payment, entitlement and tier rows do not prove automatic provider delivery when a webhook was manually replayed or no webhook row exists. E7 becomes complete only when every Story criterion is checked with the required code, test and production evidence.
