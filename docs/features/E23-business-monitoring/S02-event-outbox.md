# E23.S02: Typed business events и transactional outbox

**Цель (SMART):** закрыть перечисленные критерии S02 воспроизводимыми tests/review/evidence до смены статуса на complete.

Status: ✅ Complete (local verification; not deployed)

[Feature](./FEATURE.md) · [Contract](../../architecture/business-monitoring-contract.md) · [Registry](../../architecture/analytics-event-registry.md)

## Scope

Implementation task T02. Do not infer live readiness from code/tests. External operations and authorizations are separate gates.

## Acceptance

- [x] Strict privacy-safe typed schema rejects extra/PII/free-text/nonfinite/naive values.
- [x] Business change, event and internal outbox are atomic with rollback and semantic-key replay/mismatch tests.
- [x] Real PostgreSQL concurrent claim/commit, lease fencing and stale-worker recovery proved.
- [x] Additive ORM/migration index parity, upgrade/downgrade guard/re-upgrade proved on disposable DB.

## Evidence

- Event-schema unit suite: 28 passed. Disposable PostgreSQL: all 12 integration cases passed, including rollback, concurrent replay/claim, lease fencing, and the guarded downgrade/re-upgrade cycle on a separate migration database. The combined S01/S02 run was 63 passed. Ruff and mypy passed for the checked paths.
- The original shared fixture rebuilt unrelated application tables for every case. The suite now creates only its two ORM tables; the migration test still executes real Alembic against its own disposable database.
- After review: semantic conflicts roll back the caller's current transaction; the emitter returns a frozen receipt; the migration blocks updates, deletes and truncation of facts. Event keys use the canonical entity UUID. Only payment confirmations carry a supplemental merchant binding; a changed binding does not create a second key.
- Reverification after the second review: `pytest -q --tb=short tests/integration/test_business_event_outbox.py tests/unit/test_business_{cohorts,event_schema,monitoring_config,cost_coverage}.py` — 194 passed, including 14 PostgreSQL cases. Regressions cover rollback on enqueue failure, corrupted in-memory JSON, merchant-binding mismatch and invalid recording timestamps.
- Cancellation regression: before the fix, catching `CancelledError` at the outbox insert and committing left the caller table behind. After the fix, the same real PostgreSQL test proved that the caller change, fact and outbox row are all absent. The combined rerun passed 195 cases, including 15 on PostgreSQL; Ruff and mypy passed.
- The integration module requires `E23_DISPOSABLE_TEST_DATABASES=1`, a disposable `e23_tests` database via `TEST_DATABASE_URL`, and a disposable `e23_migration` database via `BUSINESS_EVENT_MIGRATION_DATABASE_URL` with no user relations and only `public` in the effective search path. Final independent review accepted the cancellation regression in `5d429da`. No production migration or producer activation was performed.
