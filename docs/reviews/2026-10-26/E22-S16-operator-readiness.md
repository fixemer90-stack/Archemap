# E22 S16: operator readiness and live boundary evidence

## Scope and current verdict

Independent document audit `deleg_d9d6d989` reviewed clean `6114db2` and correctly rejected new-operator reproducibility. This follow-through fixes operational tooling and removes hidden documentation steps; it does not assert independent full runbook execution, approve missing budgets, advance the accepted marker or authorize production/canary. Application runtime remains `06b72c0`, alerting infrastructure `40f3fb1`.

## Original findings and disposition

- [x] R1 dual-auth public smoke: `scripts.child_rollout_smoke` now supports paired gateway environment-name flags, Basic Authorization plus per-actor access cookie, no ambient-cookie/auth contamination, no redirects or secrets in reports. Legacy Bearer mode is preserved. Initial transport test failed RED with missing kwargs; final real CLI passed all eight enabled scenarios over the protected public HTTPS endpoint.
- [x] R2 project/release/migration boundary: every runbook Compose operation uses explicit `-p astrotype-staging`, absolute project directory/env/config, clean approved checkout assertion, private rendered volume/bind identity guard and documented automatic Alembic startup. Tooling/docs-only updates do not request an unnecessary application restart.
- [x] R3 acquisition/manifests: the operator companion gives endpoint/body/returned-ID ledger, private initialization, both complete manifests, credential transport, existing approved provisioning locations and a dedicated locked owned-resource fixture. Its child was created under C's temporary synthetic access before expiry; the locked probe returns 402, rather than accidentally testing foreign 404. Synthetic internal test-payment rows are not external payments.
- [x] R4 safe triggers: signed expired-token browser contexts, public birth-date correction after review, immutable accepted-key replay, native disabled-sentinel terminal setup and stale-age update are specified with invariants/cleanup. Disabled sentinel evidence is not labeled a real-provider outage or token/cost test. Retained failed generation avoids improvising a paid timeout.
- [x] R5 application backup/state acquisition: checked-in stdlib-only `scripts.child_runtime_state` enforces staging Docker identity, read-only SQL, protected or all-public schema/row scopes, private non-overwriting outputs, and disposable-only DB names. The companion contains an explicit maintenance-window custom dump/unique restore/equality/source-recheck/cleanup SOP. Current retained historic application dump presence/size/SHA was read back and valid. The new helper itself ran real 21-table and full 66-table read-only comparisons. No new restore rehearsal is claimed for that read-only execution; historical restore proof remains separately dated.
- [ ] R6 approved numeric budget/release record: scope/approver/measurement requirements and STOP matrix are explicit, but thresholds/workload/sample/window approval and measurements are still absent. An author cannot invent those approvals. Real-provider qualification and production/canary remain separately unauthorized.
- [x] Scope wording: the checked rollback criterion now says new admission is blocked, artifacts preserved and accepted in-flight work is not interrupted.

The first five technical/documentation blockers have implementations/procedures, not a blanket acceptance verdict. A fresh independent reviewer must inspect them; actual new-operator execution and the budget decision still block the corresponding S16 criteria.

## Actual live boundaries, not API mocks

Three browser cases used genuinely signed expired native JWTs only after successful authenticated load: draft autosave, confirmation, and a complete reader's age-update action. Each produced real 401, sign-in recovery, disabled writes and preserved loaded data. All 21 protected table row hashes stayed equal across each denied-action window. No browser page exceptions were observed. These cases do not claim interruption of accepted jobs or every active-poll timing race.

A dedicated synthetic fixture first reached ready through the real broker/worker using native mock. After its completed questionnaire was visible in confirmation review, a public birth-date correction created a new source lineage. A fresh-key stale report admission returned the same private/no-store 404 as unavailable resources, preserving all 21 table hashes across rejection. Replaying the originally accepted key returned the same generation/report; the historical report and parent payload remained unchanged. Snapshot equality begins after the intentional source correction; that setup write is not hidden.

The new public smoke CLI executed all eight required enabled cases: exact/approximate/unknown/two-child 200, owned expired 402, foreign 404, retained terminal failure 200 and pinned PDF 200. Gateway Basic Auth and real application actor cookies were used without interception. During that CLI, all 21 protected table hashes stayed equal. C's expired fixture and internal test grant/payment setup are intentionally retained privately; no real customer grants or external payment/provider calls were used. A preliminary author-controlled owned-expiry probe restored A's grant in finally; its legitimate fixture timestamp changes are not represented as global zero-mutation proof.

Private evidence: `/opt/astrotype-staging/evidence/6114db2cdbd2e5f64fec858c8133fd2b054c181a/` contains `expiry-browser-result.json`, `stale-browser-result.json`, `stale-api-result.json`, scenario-specific `boundaries/*-proof.json`, `operator-cli-enabled-result.json`, `operator-cli-no-mutations.json`, `operator-full-proof.json`, and the private fixture ledger. Production/application container/image identities and both deployment markers were re-read unchanged; the previous application dump checksum was valid.

## Independent precommit review — remediation, 2026-10-27

Reviewer `deleg_2c5aa2b4` found no code security concerns, but rejected three SOP errors. Scoped remediation `deleg_96573a42` fixed all three without live operations:

- [x] Maintenance cleanup now runs inside a subshell before caller continuation. Eight deterministic Bash cases execute the actual extracted SOP block with stub commands and empty PATH, covering success, restore/compare/create failure, INT/TERM and cleanup failure while preserving original status and created-DB ownership.
- [x] Self polling now names `/api/v1/astrotype-v2/reports/generations/{generation_id}`; a source-router contract test proves the full prefix.
- [x] Expiry uses a fresh isolated synthetic context, removes both access/refresh cookie variants and Bearer/storage/in-memory fallbacks, then requires the actual denied request's 401 before invariants. Historical fresh-context execution is explicitly distinct from the normal-login refresh path.

The nonblocking report-output suggestion is implemented with its own real RED→GREEN: existing files/symlinks are rejected before transport, new output uses exclusive creation with mode 0600 and a new immediate parent mode 0700. Review cycle 2 `deleg_d44b975a` confirmed all three fixes and the code guards, but found one remaining call-site error: the SOP's initial pre-freeze snapshot still omitted `--all-public`. A new regression executes that exact extracted invocation against legacy-only inventory, failed RED, then passed after adding the flag. The full helper test alone had not covered the SOP call site.

After this last correction the parent independently reran 59 focused and all 1163 unit tests, full Ruff/format and strict mypy successfully. Final bounded review `deleg_0e61d620` approved the exact remaining delta with no security/logic findings and independently passed 19 SOP/runtime-state tests; the previous review had already verified the unchanged code and three earlier fixes. This closes the scoped implementation review, not independent full live operator acceptance. Exact-SHA publication/CI is checked after this review and is not asserted by the offline approval.

## Verification before publication

- Core/tooling/SOP regression slice: 59 passed after real RED failures (gateway API, runtime helper/full-public/pre-Child guards and actual SOP invocation, private output, maintenance lifecycle, route and expiry recipe).
- Full backend unit collection/execution: 1163 passed, five baseline warnings.
- Repo-wide Ruff lint and format: passed; 500 Python files formatted.
- Strict mypy: no issues in 480 source files.
- Real runtime helper: 21 protected tables and 66 full public tables/schema compared unchanged in separate read-only windows.
- Real public CLI: eight required scenarios passed; private output keeps `deployed_sha_verified:false`, `provider_execution:NOT_PROVEN_BY_READ_PROBE`, `staging_budgets:NOT_MEASURED` rather than fabricating acceptance.

Independent review, exact publication SHA/CI and final cleanliness are recorded after those gates actually complete, not predicted here.
