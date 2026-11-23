# E23.S10: Integrated verification и rollout

**Цель (SMART):** закрыть перечисленные критерии S10 воспроизводимыми tests/review/evidence до смены статуса на complete.

Status: 🟡 Integration checks started; release gates open

[Feature](./FEATURE.md) · [Contract](../../architecture/business-monitoring-contract.md) · [Registry](../../architecture/analytics-event-registry.md)

## Scope

Implementation task T10. Do not infer live readiness from code/tests. External operations and authorizations are separate gates.

## Acceptance

- [ ] Full appropriate tests/lint/typecheck/build and two-stage review approved exact revision.
- [ ] Controlled migration rollout has fresh backup/off-host/restore proof and existing data/config preservation.
- [ ] External SDK privacy, real counter configuration, alert receipt and applicable conversion proof actually executed before live closure.

## Evidence

Production rollout has not been authorized or attempted. Complete the gates below in order and record the exact revision and evidence alongside each result. Never record secrets, account identifiers or report content here.

On the integrated working tree, Alembic reported one head (`e23s07t001`) and `alembic upgrade head` passed on a fresh socket-only PostgreSQL database. The S07 harness passed 30 tests with disposable PostgreSQL/Redis and mocked Telegram. The S08 harness passed 36 tests using disposable PostgreSQL and mocked HTTP. Both rejected destructive downgrade after delivery fences existed. This is local working-tree evidence, not release approval, CI, or a production backup/restore proof.

The targeted cross-story suite also passed 289 cases on disposable PostgreSQL, with LLM disabled/mock only: `tests/unit/test_business*.py`, `tests/unit/test_e23_overview_route.py`, `tests/unit/test_e23_s05_collector.py`, `tests/integration/test_e23_overview_postgresql.py`, and `tests/integration/test_business_event_outbox.py` (including the separate outbox migration database). This is not a full backend or end-to-end release run. S08 review requires serialized revocation/dispatch admission, a synchronously durable send fence, and matching counter provenance before that exporter can be considered eligible for enablement.

A later S08 harness run upgraded the integrated chain to `e23s08b001`, exercised empty downgrade/re-upgrade, and refused downgrade with retained counter provenance and used export fences. All 44 scoped S08 tests passed with mocked HTTP. Independent re-review and real counter acceptance remain open.

The pre-commit review blocked rollout on report-queue compatibility: queue age alone cannot establish worker abandonment. Run `cd backend && bash scripts/test_e23_release.sh` against the exact candidate tree in addition to generic CI. This runner creates private PostgreSQL and Redis sockets, uses a separate outbox-migration database, and forces offline/mock LLM settings. The first run reproduced the delayed Self delivery failure (185 passed, 1 failed). With the worker-claim correction applied, the same release runner passed 187 tests. Retain the separate S05/S07/S08/S09 and browser evidence on the final candidate because generic CI does not opt into all of those cases.

## Rollout gates

1. **Candidate revision.** Identify the exact commit, migration head and immutable images. Run backend unit/integration suites with disposable PostgreSQL/Redis, frontend checks/build and browser tests, and broker/worker acceptance. Record independent specification and code-quality reviews for that revision. Confirm CI for the published SHA; local checks do not establish CI status.
2. **Data protection.** Before touching the target database, take a scoped consistent backup, verify its off-host checksum and restore it into an isolated environment. Record migration head and aggregate counts for accounts, reports, payments, subscriptions and entitlements before migration and verify preservation after upgrade. Never try a destructive downgrade of populated analytics data. Use the previous app image with integrations disabled if the additive schema must remain.
3. **Staging, outbound off.** Verify that schema, API, worker and scheduler are from the same revision. Test anonymous/user/admin requests, `Cache-Control: no-store`, current/stale/unavailable values, and bounded aggregate readback. Enable internal recording only after migrations and set `BUSINESS_MONITORING_COVERAGE_SINCE` to the verified start of continuous capture; do not backdate it into gaps. Use mock provider fixtures, not real charges or paid report generation.
4. **Separate external sign-offs.** Require the owner to supply the approved counter and goal, policy/retention decision, staging test origin, approved Telegram destination, escalation owner and thresholds. Prove actual SDK network behavior before and after consent/revocation and across private navigation. Verify Telegram delivery and recovery to the approved recipient, and independently stop the producer to verify the dead-man detector. An API acknowledgment alone is not destination-side receipt.
5. **Financial proof.** Require confirmed merchant/mode binding and canonical PSP/ledger reconciliation for any real financial evidence. Do not generate transactions solely for this rollout. Verify transport acceptance and eventual conversion processing as separate observations. Unknown dispatch outcomes are quarantined, never blindly replayed. Until renewal/refund provenance is accepted, retain their unavailable/not-certified labels.
6. **Controlled release and rollback.** Only after owner approval, record an observation window and rollback operator. Turn off outbound integrations independently on failure, stop new recording if needed, and read back effective process flags and existing access/report availability. Disabling a frontend build-time flag requires redeploying its rebuilt assets, not only updating a running container's environment.
