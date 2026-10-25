# E22 staging native-mock remediation — 2026-10-25

## Scope and observed runtime

The reviewed source `01e41a9d548e2510d2aa54295f76524e4b91881f` was built in the isolated staging project/release directory, not production. Staging migrated from `f1a2b3c4d5e6` to `a8b9c0d1e2f3`, with Child enabled and `LLM_ENABLED=true`, `LLM_PROVIDER=mock`. Production container/image identities and marker were unchanged.

The existing staging backend was already exited before rollout (exit 1, October 13); the new backend is healthy. A private application dump was restored into a uniquely named disposable staging database: 49 tables, 39 nonempty, matching schema/rows/checksums and unchanged source. All 48 preexisting non-revision tables remained unchanged across the additive Child migration before synthetic fixtures were added.

Acceptance stopped on actual persisted failures, not on an HTTP/health failure:

- Child generation `1ae31437-b121-4308-b6f4-2d9fb5c58eb4` / report `1a9c29f1-ff9d-4bdf-8a52-e49af8307aae` reached `narrative_failed`. Persisted applicable sections had `child_narrative_disabled`, `provider=disabled`, `attempts=0`; not-applicable sections remained explicit. The deterministic report was preserved.
- Synthetic parent Self generation `3150196d-dc63-47cd-9a0e-3e49aca26401` / report `60e4852a-39fb-46ea-9efa-14fc0ffad0dc` also reached `narrative_failed`, with six section rows left `running`. Its deterministic natal chart/report existed; that is not ready narrative.

These synthetic opaque IDs are retained as recovery targets. No failed rows or deterministic artifacts were deleted to make the next attempt look green.

## Root causes and corrections

### Child provider selection

`configured_child_provider` treated every `LLM_PROVIDER=mock` as disabled, irrespective of `LLM_ENABLED`. The staging configuration could therefore never execute its existing bounded `MockChildSegmentProvider`.

Correction: disabled settings still select the zero-work sentinel; explicitly enabled native mock selects the bounded Child mock only in development/staging. Production and unknown environments remain fail-closed. Live-provider selection and private retry isolation are unchanged.

Actual RED: two configured-provider tests returned the disabled sentinel instead of the expected bounded native mock. GREEN covers development/staging enabled selection, all three environments disabled, and production enabled mock denial. The HTTP→real PostgreSQL→actual worker regression now covers exact/approximate/unknown birth inputs in both enabled and disabled modes: six passed, ready only in enabled native-mock mode, with provider-call accounting and 15-section reader validation.

### Self v2 provider input contract

The generic `MockLLMProvider.generate_structured` unconditionally read legacy `NarrativeInput.deep_natal_synthesis`. The real v2 adapter supplies `SectionRenderInputV2`; all six real section boundary regressions failed with `AttributeError` before any compatible response could be returned.

Correction: dispatch typed v2 inputs before accessing legacy fields. Native v2 mock responses retain the exact section identity/title, owned theme IDs and supplied evidence IDs, render only owned-theme detail, carry explicit demo/no-real-LLM wording, and continue through the existing unchanged validators. Legacy Self input handling is unchanged. The configured factory disallows this new v2 demo path in production; an additional RED proved production previously returned a demo result, then GREEN restores fail-closed behavior. No network calls, fabricated astrological evidence or validator bypasses were added.

## Verification

- Twelve initial configured Child/native Self boundary regressions passed after correct RED failures. A seventh Self production-denial regression was subsequently added with its own RED→GREEN.
- Real PostgreSQL configured-worker matrix: six passed.
- Complete current backend unit+integration command with explicit disposable `e22_presentation_test`: **1292 passed**, six baseline warnings, in 337.80 seconds.
- Ruff lint passed; 496 Python files format-clean; strict mypy passed across 476 source files; `git diff --check` passed.
- Production provider/container changes: none. Paid provider calls: none.
- The temporary 2 GiB build swap was safely disabled and removed; private `swap-cleanup.json` readback confirms removal.

## Independent review and final local follow-through

Read-only reviewers `deleg_f681e3c6` and `deleg_aa3c559b` approved the scoped fixes with no security or logic findings. The final review included all three production files, environment-gated Self factory behavior, legacy compatibility, and production refusal. Review suggestions were persisted as explicit demo/notes, incompatible-schema, reference-only body sentinel, and development/staging parameterized tests. After these test-only additions, all **1121 unit tests** plus full Ruff/format/mypy passed. The earlier full 1292 unit+integration pass covers the unchanged production patch; remote CI will execute the expanded final suites again.

## Exact-SHA staged follow-through

Commit `1fcc4792373866c5c99104fdd92e7b9a3344559a` was published; CI run `40203572310` completed with all seven jobs successful. A fresh private backup was restored and compared: 66 tables, 55 nonempty, identical schema/rows and unchanged source. The isolated backend consumers were rebuilt/restarted without production mutation. The frontend git tree was unchanged and its verified image was reused. Independent runtime verification matched all 270 tracked application/worker Python sources in each of backend, worker, scheduler and refinement-monitor; checked effective staging/mock/Child flags, 18 Child operations, task registration and scheduler configuration.

Actual Child-only HTTPS→broker→worker→browser smoke passed exact/approximate/unknown paths, 15-section reader, full PDF body/confidence/age parity, owner-only export, idempotency, private foreign denial, free/expired denial, age update and a browser-generated report. The browser used no API mocks: no mobile overflow, no WCAG violations, keyboard review focus, ten autosave groups and no console errors. The original degraded Child was explicitly retried with `failed_sections` and its report ID preserved. Initial recovery terminal wait was 71.067 seconds; subsequent two cases were under one second. These are observed mock timings, not real-provider budgets or a population percentile.

Parent Self recovery through its public force-regeneration endpoint reached `narrative_failed` again (generation `b9a826fb-d298-4416-bfe5-aa9f7b5e94cc`). Read-only replay of all six persisted section requests isolated a second boundary: cached themes without optional depth fields yielded a demo body below the unchanged 450/300-word validation floors. Six new regressions reproduced the exact validation failure. The corrective mock-only delta adds bounded explicit-demo explanatory paragraphs; no cached chart/facts are changed and no validation rule is weakened. Local GREEN: **1127 unit tests**, Ruff/format/mypy. Independent read-only review `deleg_cc748596` approved this delta with no blockers and independently ran all 21 Self boundary tests, including all six thin-cache regressions and production refusal. This later delta still needs publication, exact-SHA CI and redeploy; it is not part of the running `1fcc479` image.

## Delivery gates

The running `1fcc479` build and its Child-only smoke are verified. Overall staging acceptance remains blocked on the later cached-theme correction, actual ready Self recovery, and the remaining rollback/telemetry/budget gates. The older accepted marker was deliberately not advanced. Runtime/source readiness and the successful Child flow are not a claim that all S15/S16 gates are complete.

S15 real-provider cost/quality, delivered alerts and S16 production/canary remain open. A successful native-mock staging flow cannot close those gates.
