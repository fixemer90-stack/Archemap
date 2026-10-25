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

## Delivery gates

Independent review is complete. Commit/push, new exact-SHA CI, source-verified staging restart, explicit recovery of the recorded jobs, fresh exact/approximate/unknown API/browser/PDF smoke and staging marker acceptance remain separate gates. This document does not claim these have happened yet. The earlier staging success sentinel meant only readiness for independent smoke; its accepted marker was deliberately not advanced.

S15 real-provider cost/quality, delivered alerts and S16 production/canary remain open. A successful native-mock staging flow cannot close those gates.
