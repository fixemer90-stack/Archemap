# E23.S08: Gated initial LIVE conversion export

**Цель (SMART):** закрыть перечисленные критерии S08 воспроизводимыми tests/review/evidence до смены статуса на complete.

Status: Locally verified; external acceptance and independent review pending

[Feature](./FEATURE.md) · [Contract](../../architecture/business-monitoring-contract.md) · [Registry](../../architecture/analytics-event-registry.md)

## Scope

Implementation task T08. Do not infer live readiness from code/tests. External operations and authorizations are separate gates.

## Acceptance

- [x] Only consented, attributed canonical initial LIVE purchases eligible; others skip with reason (local PostgreSQL + mocks).
- [x] One export mechanism/goal, durable upload state, unknown outcomes fail closed and no blind duplicate retry (local PostgreSQL + mocks).
- [ ] Tokens private; actual counter/settings/API processing/readback remain external acceptance gates.

## Operating boundary

- Export is off by default. The trusted `export_initial_purchase(event_id)` entry point takes one committed event ID. No route, scheduled scan, payment callback, backfill, or browser purchase goal invokes it. `refresh_upload_status(event_id)` only reads an upload with a known receipt; it does not submit again.
- Enabling requires `YANDEX_METRICA_EXPORT_ENABLED`, a dedicated server-only `YANDEX_METRICA_EXPORT_OAUTH_TOKEN`, and explicit `YANDEX_METRICA_EXPORT_COUNTER_ID`, `YANDEX_METRICA_EXPORT_TARGET`, `YANDEX_METRICA_EXPORT_POLICY_VERSION`, and timezone-aware `YANDEX_METRICA_EXPORT_NOT_BEFORE`. The S05 approved and stored policy/counter must match the export version and destination; legacy null or a different counter fails closed. Verify isolated SDK provenance and no parallel purchase goal before any external activation. Apply `e23s08b001` before starting the updated capture/export code and keep old senders disabled during rollout. Login OAuth credentials are not used.
- The only insert winner can dispatch. `SET LOCAL synchronous_commit = on` is applied in the permanent fence transaction; the `outcome_unknown` row commits before final admission and before any HTTP. This is PostgreSQL commit durability on the primary, not an asynchronous replica/failover guarantee. The row contains bounded state/receipt fields, not ClientID, credentials, or provider response bodies. A received upload ID is not evidence of conversion linkage.
- Final admission rechecks the purchase, then takes an exclusive row lock on the exact eligible S05 owner snapshot. If revocation takes the row first and commits, the waiting sender sees the tombstone and never sends. If final admission takes the row first and consent is still usable at the rechecked clock, revocation waits through the one-shot request until response, cancellation, or deadline releases the transaction. The 10-second total deadline includes final DB recheck/lock wait and the whole HTTP attempt; it is not reset between stages. Receipt persistence is a separate transaction after releasing the consent lock. This is ordering at the local dispatch boundary, not cancellation of bytes already in flight or a distributed atomic guarantee after loss of the database session or process.
- A known denial before HTTP becomes `skipped`; timeout, cancellation, a crash after fence commit, or missing receipt leaves `outcome_unknown`, even when no bytes were actually sent. No lease, silent retry, or later re-admission is allowed. Do not delete fences to recover delivery.

## Evidence

From the repository root, with `TMPDIR` pointing at a private scratch directory:

```bash
bash backend/scripts/test_yandex_conversion_export.sh -x -q \
  tests/unit/test_business_monitoring_config.py tests/unit/test_e23_s05_collector.py
```

Re-review also found that consent revocation could inherit asynchronous commits even though dispatch fences did not. Revocation now requires `SET LOCAL synchronous_commit = on` before changing attribution. The PostgreSQL lock-order test starts the revocation transaction with synchronous commit off and verifies that revocation turns it on; the S08 harness rerun passed 44 tests. This verifies the commit setting, not crash recovery or replica failover.

The earlier 66-test run also included S05 and configuration checks. The disposable socket-only PostgreSQL harness covers migration `e23s07t001 → e23s08b001 → e23s07t001 → e23s08b001`, retained legacy null provenance, and downgrade refusal with bound attribution or used fences. A database trigger requires `synchronous_commit=on` at fence INSERT despite the cluster default being off. Independent sessions observe both PostgreSQL lock orders before the mock HTTP call, and the mock checks the fence is already visible while HTTP is in flight. Tests cover pre-HTTP and in-HTTP deadline, cancellation, no replay, counter mismatch and legacy null, and receipt persistence/readback. No external provider, deployed counter, or real payment was exercised.
