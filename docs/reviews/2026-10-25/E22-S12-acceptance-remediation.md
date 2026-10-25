# E22 S12 acceptance review remediation — 2026-10-25

## Scope

Only independent P1 findings: full-report replay before mutable current lineage, and authoritative current-age validation for new acceptance. No commits. Existing provider-fence, narrative-scope, Decimal tolerance, router, presentation/PDF, frontend, and story-document edits are not part of this patch and were preserved.

Production changes:

- `backend/app/modules/child/service.py`: only `accept_full_generation`; resolve accepted public target before resolving current defaults. Existing generation ID, current persisted status and report ID are returned without redispatch.
- `backend/app/modules/child/repository.py`: replay helper validates active owner-scoped child and questionnaire IDs, and exact `(child_profile_id, questionnaire_session_id, source_report_id=None, operation_payload={})` within the `full_report` operation domain. Different valid public target with the same key returns conflict before supporting writes. An owner/operation/key advisory transaction lock is acquired before defaults and shared with `create_generation_idempotently`. Fresh acceptance takes the child-lineage lock after that idempotency lock; replay does not resolve current defaults.
- `resolve_current_generation_lineage` additionally uses `resolve_child_age` and `age_snapshot_is_current` to validate current persisted DOB, real UTC server clock converted to child timezone, current `AGE_RULES_VERSION`, and DOB-derived input hash. It does not create snapshots. Historical worker execution is unchanged.

New tests: `backend/tests/integration/test_child_api_acceptance_review.py`.

## Database safety

All integration runs explicitly used only:

```sh
TEST_DATABASE_URL=postgresql+asyncpg://e22test@127.0.0.1:55434/e22_review_acceptance_test
```

Created this dedicated disposable database with:

```sh
/usr/lib/postgresql/16/bin/createdb -h 127.0.0.1 -p 55434 -U e22test e22_review_acceptance_test
```

Tests use real HTTP/ASGI ownership/access handling and real PostgreSQL; dispatch is an in-process counting mock. No real LLM, Celery broker, or remote provider calls. The existing fixture creates/drops metadata only in the explicit disposable database; no migrations or application database writes were run.

## Actual RED → GREEN evidence

Commands below run from `/home/balthier/archemap/backend`, with the database variable above explicitly prefixed for every pytest invocation.

1. Added the replay HTTP regression first. After correcting a test-only chart response field assumption, ran:
   `.venv/bin/pytest tests/integration/test_child_api_acceptance_review.py -q`
   **RED:** 1 failed; accepted retry after public DOB correction/new chart and newer completed questionnaire returned **404**, expected **202**. No production fix had been made.
2. Added replay-first resolution plus shared idempotency lock; ran the same command.
   **GREEN:** 1 passed. Same key replays original generation/current status; fresh key with old questionnaire is 404; changed valid questionnaire with same key is 409; row counts and dispatch count remain unchanged.
3. Added authoritative-age regression covering public DOB correction from 3–6 to 6–9 without calling GET current afterward, plus stale local date, rules version, and input hash. Initial extra fixture variants hit the ORM append-only guard; changed only those test fixtures to SQL historical-artifact setup, leaving production guards enabled. Reran before changing production validation:
   `.venv/bin/pytest tests/integration/test_child_api_acceptance_review.py -q --tb=line`
   **RED:** 4 failed, 1 passed; every stale variant incorrectly returned **202**, expected **404**.
4. Added authoritative validation and reran targeted tests.
   **GREEN:** 5 passed. Replay coverage additionally advances repository clock one day and verifies current persisted `failed` status; its initial valid current-age completed request remains accepted. Rejections/replays/conflicts assert unchanged counts for generations, events, age snapshots, charts, questionnaires, reports, and provider segments and no extra dispatch.

## Verification and fixture follow-up

Related real-PostgreSQL run:

```sh
.venv/bin/pytest tests/integration/test_child_api_acceptance_review.py tests/integration/test_child_generation_lifecycle.py tests/integration/test_child_generation_access.py tests/integration/test_child_api.py -q --tb=short
```

**Actual result: 60 passed, 8 failed, 1 warning (68 collected).** All five new review regressions pass. The eight failures are existing acceptance expectations seeded with historical/noncanonical age snapshots; new authoritative validation correctly rejects them. Existing test files were deliberately not edited under the assigned ownership boundary. They need fixture upgrades using canonical current DOB/timezone/rules/hash, not relaxed production validation:

- `test_child_generation_lifecycle.py`: `test_accept_generation_returns_queued_id_without_running_pipeline_inline`, `test_http_create_returns_202_generation_without_inline_artifacts`, `test_http_create_allows_active_plus_access`, `test_accept_generation_replay_dispatches_once`, `test_generation_events_are_transactional_safe_and_append_only`.
- `test_child_generation_access.py`: `test_http_paid_gate_accepts_canonical_access_and_pins_server_lineage[plus]` and `[child]`.
- `test_child_api.py`: `test_regenerate_scopes_have_distinct_immutable_lineage[full_pair]`.

`_seed_lifecycle` uses 2026-10-23, `age-rules-v1`, and synthetic `a…` hash; `_seed_claimable_full_pipeline` likewise uses the historical `NOW` and synthetic `l…` hash. They are not valid current acceptance fixtures on the verified system date 2026-10-25. Historical worker-path tests continued passing. One warning is the existing WeasyPrint HarfBuzz-Subset deprecation.

Checks on the two touched production files and the new test:

```sh
.venv/bin/ruff check app/modules/child/service.py app/modules/child/repository.py tests/integration/test_child_api_acceptance_review.py
.venv/bin/ruff format --check --range 1210-1410 app/modules/child/repository.py
.venv/bin/ruff format --check app/modules/child/service.py tests/integration/test_child_api_acceptance_review.py
.venv/bin/mypy app/modules/child/service.py app/modules/child/repository.py tests/integration/test_child_api_acceptance_review.py
git diff --check
```

Final fresh verification: Ruff lint passed; acceptance-region repository formatting and full service/test formatting passed; strict mypy passed with no issues in all three source files; `git diff --check` passed; targeted PostgreSQL review tests passed **5/5 in 4.35s**. Repository formatting was deliberately limited to the acceptance region to preserve the parent's existing provider-fence/Decimal edits. Full-file format checking previously identified unrelated pre-existing formatting in that shared file.

Full related-suite output: `/home/balthier/.hermes/cache/scratch/e22-acceptance-pytest-final.log`.

## Parent fixture follow-through

The parent upgraded lifecycle acceptance snapshots to canonical current DOB/date/rules/hash. Historical worker fixtures now use canonical age resolution at their explicit pinned `NOW`, with an optional `snapshot_as_of` for fresh full-pair acceptance; historical worker semantics were not weakened. Stale-snapshot negative controls now create a genuinely newer canonical snapshot relative to the actual seed date. Extra-field rejection tests retain 422/no-write assertions while expecting redacted `unknown_field` locations.

Final full backend verification after these fixture corrections: **1094 unit tests passed; 173 integration tests passed**, Ruff lint/format and strict mypy passed. The same full commands passed again in a newly installed CI-shaped Python environment with zero known dependency vulnerabilities. Subsequent API work-class tracing/privacy/review regressions passed **21 tests**. Independent re-review and exact-SHA CI remain separate gates; no production rollout was executed.

## Full-pair regeneration correction fence follow-up

The remaining P1 was in `api_service.regenerate`: its API-only key lock did not fence mutable questionnaire/age/chart defaults against birth correction. Fresh `full_pair` now acquires the canonical owner/`full_report`/key transaction lock before the existing-row lookup, then the shared child-lineage transaction lock before any mutable default routing, holding it through acceptance commit. Existing replay rows use `populate_existing=True`, return before current-lineage resolution, and retain public cross-scope target conflicts. Lock order matches POST `/reports`; correction takes lineage without taking generation idempotency, so it does not introduce an inverse order.

Added `backend/tests/integration/test_child_full_pair_correction_fencing.py`. Its three real-PostgreSQL regressions use a fresh engine derived from the fixture bind and separate committed sessions. Server `pg_blocking_pids` plus ungranted advisory rows in `pg_locks` prove actual database waits; bounded lock timeouts guard lock-order failures. Coverage proves acceptance-first blocks a real validated public birth correction through commit, correction-first blocks acceptance then rejects the stale questionnaire without generation/artifact writes or dispatch, and the canonical generation-key lock is acquired before lineage. Accepted replay after DOB/chart correction returns the original target and fresh persisted status despite a deliberately stale identity-map row, without redispatch; changed scope retains its conflict.

Read the destructive fixture before running it. Created and exclusively used disposable `postgresql+asyncpg://e22test@127.0.0.1:55434/e22_full_pair_review_test`; did not use the parent's database. No remote providers, broker dispatch, migrations, or commits.

**Actual RED:** before production edits, the first barrier regression failed at `_blocked` with `TimeoutError` (1 failed in 7.03s): correction did not wait for acceptance at PostgreSQL. **GREEN:** the original two regressions passed in 3.65s after the minimal fix. Final expanded verification with the new three regressions, all API acceptance-review tests, and all `test_child_api.py` tests: **22 passed, 1 existing WeasyPrint warning in 37.30s**. Repeated focused regressions: **3 passed in 5.20s**. Scoped Ruff lint and format checks passed; strict mypy reported no issues in both touched Python files; `git diff --check` passed. Interpreter: `/home/balthier/.hermes/cache/scratch/e22-ci-audit-YPuDSo/bin/python`. Every pytest command explicitly set the disposable `TEST_DATABASE_URL` above.

## Final parent closeout

Independent read-only re-review `deleg_6cf19a52` approved R6 with no security/logic findings and executed 40 PostgreSQL tests. Its optional public scope-conflict assertions were persisted: exact 409/no-store response, all Child-table rows/columns unchanged, no extra dispatch. Parent reran 22 API/acceptance/concurrency tests and full Ruff/format/mypy successfully. Full current backend previously passed 1276 unit+integration tests and a fresh actual API→Redis→Celery→PostgreSQL/browser smoke passed with no paid provider calls. Production changes are committed as `f02b23b` and published within source SHA `39f43c3dec32bc32cffba4b0903d699eb9affff1`; GitHub CI `40177715171` completed all seven jobs successfully. Deployment/publication jobs were skipped; no staging/production rollout is claimed.
