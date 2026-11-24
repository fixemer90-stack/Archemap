# E23.S04: Read-only business overview API

**Цель (SMART):** закрыть перечисленные критерии S04 воспроизводимыми tests/review/evidence до смены статуса на complete.

Status: 🟡 Deployed with recording off; 90-day seeded SQL budget not met

[Feature](./FEATURE.md) · [Contract](../../architecture/business-monitoring-contract.md) · [Registry](../../architecture/analytics-event-registry.md)

## Scope

Implementation task T04. Do not infer live readiness from code/tests. External operations and authorizations are separate gates.

## Acceptance

- [x] Superuser-only GET overview; normal/anonymous users denied.
- [x] Pure read queries do not call PSP/LLM/reconcile or mutate ledger.
- [x] LIVE/test/unknown, exact money, cohorts, zero denominator, effective periods and data freshness correctly distinguished.
- [x] Executed D7 golden fixtures cover late-Moscow-day signup/next-day activation, cohort/window/deadline/as_of boundaries, immature/empty cohorts and same-cohort numerator/denominator exactly as the canonical contract.

## Evidence

- `GET /api/v1/admin/business/overview` returns `Cache-Control: no-store`. Business queries run in a separate PostgreSQL `REPEATABLE READ READ ONLY` transaction with a five-second statement timeout. The PostgreSQL test rejects a ledger write with SQLSTATE `25006` and verifies anonymous, ordinary and superuser access through the mounted route.
- Date filters are optional `from_date`/`to_date` (exclusive), at most 90 calendar days in `Europe/Moscow` or `UTC`. The default D7 cohort excludes the last seven calendar days. The server uses its UTC observation instant; callers cannot ask the current subscription ledger to reconstruct past entitlements.
- Recording and an operator-supplied `BUSINESS_MONITORING_COVERAGE_SINCE` are both required for metrics. Uncovered cohorts have a null rate. The latest recorded event is a freshness hint, not independent pipeline health; on low traffic the view can be marked stale without an outage. Refund and recurring revenue are not certified until their sources exist.
- Cash is unavailable if the selected window is incomplete, any paid receipt has unproven mode, or any proven LIVE amount is unusable. A covered window with no LIVE receipts returns an empty currency list. Cash uses exact decimal addition of valid cents recovered from the current PSP-validated ledger amount, not a retained independent PSP amount snapshot. Checkout outcomes are bounded local snapshots (`pending`, `failed`, `confirmed`, `unknown`). Partial paid Plus returns null for the total and a separately named `proven_active` lower bound; proof requires the current payment's own entitlement.
- Independent review found duplicate-identity, mixed-cohort and financial coverage gaps. RED on disposable PostgreSQL reproduced a duplicate signup in the overview. The correction filters canonical identities, classifies each payment once, and adds PostgreSQL cases for duplicate payment proof, conflicting ownership, invalid amounts, an unrelated grant, observed zero, and mixed maturity. The [seeded benchmark](#seeded-postgresql-benchmark) exercises the 90-day limit and found timeouts; the limit alone does not bound query cost.
- The second review reproduced orphan confirmation facts, duplicate PSP receipts across local payment rows, and an overflow at the earliest ISO date. The correction counts unmatched facts and ambiguous PSP references as unknown and withholds cash; unrepresentable dates return 422. The mounted PostgreSQL test exercises aggregates with monitoring enabled as well as the default-off route.
- Disposable PostgreSQL plus adjacent unit checks: `pytest -q tests/integration/test_e23_overview_postgresql.py tests/unit/test_e23_overview_route.py tests/unit/test_business_cohorts.py tests/unit/test_business_monitoring_config.py` — 41 passed. No PSP or LLM was invoked. Immutable amount evidence is still needed for financial certification.

## Self D7 timing coverage

D7 uses the independent bounds from the [Self producer](./S03-authoritative-producers.md#self-d7-publication-time), not `basic_report_ready.occurred_at`. The metric counts a first readiness only when its bounds prove it was at or after signup and strictly before the 168-hour deadline. A proven pre-signup first readiness or a fully proven late first readiness is a known nonactivation. A bound crossing either edge, an older event without proof, missing readiness evidence, or mismatched lineage is unavailable. A known on-time report does not erase an older unqualified candidate.

If any mature signup has unresolved readiness evidence, return `unavailable` with null activated count and rate; preserve the maturity counts. Under verified continuous coverage, a mature signup with no readiness fact is a known nonactivation; a present but unqualified fact is not. Old rows are not backfilled. A recovery observation at or after the deadline does not certify an earlier commit when the bounds straddle the cutoff. Local verification does not certify production cohort coverage.

- Follow-up verified the covered no-readiness case RED → GREEN: 70 PostgreSQL producer/overview/outbox integration tests passed. The complete backend unit run finished with 1,860 passed and five warnings (WeasyPrint and test mocks). [S10 rollout evidence](./S10-verification-rollout.md) records that the November 23, 2026 flags-off deployment of `819f654bab35131bb32f7a8dcbd60f1327d0ce68` read back production head `e23d7b001`. The isolated restore rehearsal preserved nine checked table counts without historical readiness backfill; the rollout preserved 18 checked counts. This is recorded rollout evidence, not a fresh production check, activation, or signed-in acceptance.
- Independent-review follow-up: readiness with a durable lower bound strictly after `as_of` does not change an earlier known zero, whether observation is pending or completed. A missing bound, a straddling bound, or a lower bound exactly at `as_of` with a later observation still leaves the candidate unresolved. The historical overview uses finalized, database-protected proof even after the source report is deleted.

## Seeded PostgreSQL benchmark

The original timeouts below are baseline evidence. The optimized queries passed the unchanged 1,000-account/day benchmark on two fresh clusters (5 and 12 repetitions per window). The maximum observed wall time for the complete 90-day overview was 1.50 s with the same 5 s statement timeout; both windows matched completed baseline outputs, including intentionally unavailable cash and D7 values. This unblocks the synthetic performance gate, not production data coverage or concurrent traffic acceptance.

- D7 now aggregates canonical signup counts and mature readiness outcomes independently. This avoids the generic nested-loop rejoin that reproduced `57014` without changing which candidates are unproven or activated.
- Payment counts pair in-window confirmations and ledger rows by canonical identity once, preserving a single unknown for mismatches and a separate unknown for true orphans. A same-snapshot 90-day plan measured 137 ms versus 215 ms before the rewrite; the earlier payment timeout did not recur during the A/B run, so its precise runtime cause remains unproven. Tests cover paid-window boundaries and merchant account ambiguity.
- The default release runner passed 205 tests after the query changes. No new schema migration is needed.

Run from `backend/` as a non-root user with the backend venv and local PostgreSQL server tools installed (`pg_config --bindir` must locate `initdb`, `pg_ctl`, `createdb`, and `psql`). Use a short, private `TMPDIR` on local storage.

```sh
.venv/bin/python -m scripts.benchmark_e23_overview > "$TMPDIR/e23-s04-1000.json"
```

The [runner](../../../backend/scripts/benchmark_e23_overview.py) creates and removes its own Unix-socket-only cluster, ignores inherited PostgreSQL connection variables, and applies `alembic upgrade head`. It seeds 180 calendar days at 1,000 synthetic accounts/day: **180,000 users, 903,501 business events, 144,100 D7 proof rows, 69,900 payments, 42,900 subscriptions, and 42,900 entitlements**. No copied customer data, production connection, Redis, or provider calls. The seed includes on-time, late, pre-signup, absent, and pending D7 evidence; it covers LIVE, TEST, unproven, orphan, and duplicate receipts, plus pending, failed, and local-only checkouts. The seed writes D7 bounds and the observation in separate transactions to exercise the migrated write-once constraint; it does not run the producers.

PostgreSQL 16.15 at `e23d7b001`, fixed observation time `2026-10-01T21:00:00Z`. The two explicit Moscow windows end at September 25, 2026 (exclusive); they start on September 18 and June 27 respectively so both exercise mature cohorts. The runner calls `build_overview` in the route's `REPEATABLE READ READ ONLY` session, verifies `statement_timeout = 5s` and write rejection `25006`, and explains the six production SQL statements with their typed binds. It reports up to five samples per window/statement, buffer counters and scan paths, and returns nonzero on a timeout or budget breach while retaining JSON evidence. If a build aborts early, independently probed statements the build did not reach are marked as using derived, rather than captured, binds.

First 1,000/day run (milliseconds, median / maximum):

| Measurement                           |            7 days |                            90 days |
| ------------------------------------- | ----------------: | ---------------------------------: |
| Full overview build, client wall time | 204.625 / 253.819 |                1052.061 / 1096.917 |
| `EXPLAIN ANALYZE`: watermark          |   44.553 / 44.839 |                    44.567 / 49.300 |
| D7                                    |   49.649 / 49.917 |                  296.547 / 322.023 |
| Active Plus                           |   69.567 / 70.120 |                    69.447 / 74.304 |
| Event counts                          |   16.943 / 17.192 |                  127.834 / 133.948 |
| Checkout outcomes                     |     9.416 / 9.769 |                  181.093 / 183.976 |
| Payment counts                        |   13.968 / 14.058 | Timed out (`57014`); estimate only |

- **7-day result:** 4,200 of 7,000 mature signups activated (60%); 350 LIVE and 350 TEST receipts, no unknown receipts, and exact cash of 3,498.25 RUB and 3,498.25 USD. Both completed windows reported a partial current Plus snapshot with 1,500 proven active users.
- **90-day result on completed builds:** 90,000 mature signups, but the pending proof made activation unavailable. Receipts were 4,500 LIVE, 4,500 TEST, and 16,600 unknown; cash was null. The separate payment `EXPLAIN ANALYZE` exceeded the server timeout on both fresh 1,000/day clusters. Its estimated plan used a sequential payment scan with correlated proof lookups; no runtime plan was obtained for that statement.
- **Repeatability and limits:** On a second fresh cluster with identical 1,000/day seed, the 7-day build passed again (216.322 / 958.757 ms), but the 90-day build itself stopped at D7 (`57014`, 5047.482 ms elapsed). A 200/day run also stopped at D7 on the 90-day build although the separately explained D7 statement completed. A fast `EXPLAIN` or even five fast builds on one cluster is therefore not sufficient evidence of a stable budget. These are single-client, sampled, post-seed `VACUUM (ANALYZE)` runs, not production traffic, cold-start percentiles, concurrent load, authenticated HTTP latency, or real capture coverage. Query/plan remediation and re-benchmarking remain open before claiming the 90-day performance gate passed.
