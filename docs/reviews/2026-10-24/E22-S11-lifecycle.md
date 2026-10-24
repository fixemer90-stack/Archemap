# E22 S11 — independent lifecycle review, 2026-10-24

## Verdict

Approved. R1/R2 and final R3 atomic-concurrency recheck independently approved; no remaining security concerns or blocking logic errors reported. Backend implementation committed as `939fd40f47cd430422d4f34ec72e6787249d4cfb`; remote CI closeout tracked in S11. Production rollout is outside this Story.

## Scope

Current uncommitted S11 Child implementation: HTTP acceptance/access, PostgreSQL generation/dispatch/worker claims, deterministic publication, modular narrative, retries/reconciliation, immutable artifacts and additive migration. Missing S12 read/status endpoints were treated as planned work, not S11 defects.

## Findings

### R1 — disabled provider cannot persist recoverable failed sections

Status: Fixed and independently approved; disabled-to-enabled recovery regression passed.

- Review snapshot selected `DisabledChildSegmentProvider` but rejected its identity before any section row was saved, eventually exhausting retries with no failed-section retry target.
- Fix: allow the controlled disabled identity; persist explicit `child_narrative_disabled` failed sections with zero attempts; assembly accepts only the corresponding provider/attempt metadata; provider-call counter remains zero.
- Files: `backend/app/modules/child/narrative.py`, `service.py`, `assembly.py`; regression in `backend/tests/integration/test_child_generation_provider_retry.py`.
- RED: expected `narrative_failed`, observed `narrative_retry_waiting`; GREEN: `1 passed`.
- Real migrated HTTP → Redis → Celery → PostgreSQL smoke: health 200, create/replay 202 with same generation ID; report deterministic_ready, generation narrative_failed, one assembly, 15 failed/not_applicable sections, no ready prose.
- [x] Disabled provider produces durable safe failed sections without a retry loop.
- [x] Re-enabling a healthy provider completes the existing deterministic report without full regeneration.

### R2 — early-section exhaustion omits later sections from retry scope

Status: Fixed and independently approved.

- Full generation returns immediately when an early section exhausts automatic retries; later sections can remain absent.
- Manual retry pins only existing failed segment rows, so missing required sections cannot be recovered and successful retry still assembles a partial report.
- Required fix: persist an auditable complete recovery scope, without mutating terminal source sections or recomputing deterministic artifacts.
- [x] Reproduce first non-empty section exhaustion through all automatic attempts.
- [x] Healthy narrative retry completes every required section and reaches ready.
- [x] Existing completed segments and deterministic artifacts remain unchanged.

### R3 — ambiguous transport outcomes may issue duplicate external calls

Status: Fixed and independently approved after concurrent-race reproduction; shared source-report/section namespace, checkpoint commit boundary, durable post-crash fence and known-rejection retryability confirmed.

- Read timeout is collapsed into an ordinary retryable provider failure even though the remote response may have completed.
- Configured provider/SDK retry layers can repeat POSTs inside a single durable Child intent.
- Required fix: classify ambiguous outcomes as outcome_unknown, fence them against automatic/manual recall, and disable transparent retries for Child without altering other products' policy.
- [x] Intercepted configured production adapter proves exactly one POST per durable intent.
- [x] Ambiguous read/write/transport error persists outcome_unknown; sequential automatic/manual/sibling cases are fenced.
- [x] Concurrent siblings share an atomic durable source-report/section claim before external calls. RED reproduced B making 10 calls after stale prechecks; GREEN prevents B from issuing any call.
- [x] Six real PostgreSQL scenarios cover in-flight overlap, committed unknown after stale prechecks, completed sibling, crash/reconciliation/redelivery, retryable known rejection, and atomic contention observed via an ungranted advisory lock in `pg_locks`.
- `ChildRepository.claim_segment_intent()` takes a shared transaction-advisory lock keyed by source report + section, then checks sibling durable intents and inserts the caller intent through checkpoint commit. No DB lock spans network I/O; committed intents fence in-progress, unknown and completed calls.
- Sibling acceptance remains unchanged. Workers fail closed with bounded lifecycle backoff/exhaustion; they do not reuse or mutate another generation’s completed result. Known rejection remains retryable. No schema migration changes were needed.
- [x] Known rejection remains recoverable through durable lifecycle backoff.
- [x] Provider/SDK retry behavior for DeepSeek and OpenRouter is covered without real paid calls.

## Final local verification after atomic-fencing remediation

- Full backend unit suite: 1043 passed, 5 warnings (WeasyPrint/legacy AsyncMock).
- `TEST_DATABASE_URL=<disposable> pytest tests/integration/test_child*.py -q --tb=short`: 120 passed, including all prior Child Stories, S11 lifecycle/access/provider/migration, 24 review regressions and six concurrent-fencing scenarios.
- Backend Ruff, format and strict `mypy .`: pass; 450 checked source files; 451 Python files formatted.
- Documentation formatting and `git diff --check`: pass.
- Parent reran the exact suites after the final code changes; final independent recheck approved R3 with empty security/logic error lists.
- Parent repeated the real HTTP/Redis/Celery/PostgreSQL smoke after all fixes: health 200; create/replay 202; same generation ID; narrative_failed + persisted deterministic_ready; 15 safe sections; one assembly; no provider calls or fake prose.
- Remediation files: `backend/app/modules/child/service.py`, `narrative.py`; `backend/tests/integration/test_child_generation_review_regressions.py`, `backend/tests/unit/test_child/test_review_provider_retry_isolation.py`. Missing sections now have canonical input pins; Child provider settings are copied with zero internal retries, leaving other products unchanged.
