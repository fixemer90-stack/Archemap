# E23.S09: Cost coverage и controlled projection backfill

**Цель (SMART):** закрыть перечисленные критерии S09 воспроизводимыми tests/review/evidence до смены статуса на complete.

Status: 🟡 In progress

[Feature](./FEATURE.md) · [Contract](../../architecture/business-monitoring-contract.md) · [Registry](../../architecture/analytics-event-registry.md)

## Scope

Implementation task T09. Do not infer live readiness from code/tests. External operations and authorizations are separate gates.

- DeepSeek and OpenRouter produce request-local evidence only after the existing HTTP dispatch guard. Each retry has a separate identity. HTTP rejection and structured-response rejection are failed attempts; an admitted call with no response is an unknown outcome, not a zero-cost failure. A succeeded attempt means the response passed the adapter, not that the report was delivered.
- With `BUSINESS_MONITORING_ENABLED`, the adapters write typed, append-only `business_transport_usage` facts in a separate best-effort transaction. They do not write a tariff, backfill, queue event, customer/report identifier, upstream response ID, prompt or prose. Only the configured model's opaque digest is stored, not the returned model label. Missing or invalid token usage is absent. OpenRouter cache writes cannot be priced by the two-bucket cache model and do not produce a cache split.
- `read_transport_costs` groups exact Decimal estimates by currency; there is no FX or invoice conversion. Optional trusted rate evidence must match the provider/model scope and pins version, time, currency, cache policy and prices. No rate is inferred from current settings, provider labels, payloads, Career's legacy telemetry estimates, or historical Child segments. A delivery denominator is caller-owned and must be comparable to the cost scope.
- Historical Child diagnostics are aggregate evidence from retained terminal segment rows. They cannot recover HTTP-attempt IDs, individual outcomes, earlier replaced diagnostics, or exact dispatch times. Their separate projection is keyed by source segment ID and windowed by segment creation time. Failed section rows remain visible, missing/malformed aggregates remain unknown, and mock/disabled rows are excluded. Never add historical projection counts to overlapping live evidence.
- New Child diagnostics aggregate each received response once, including valid usage from rejected HTTP responses. A received response without valid usage increments `responses_without_usage` without inventing tokens; an admitted call with no response increments only `http_attempts`. Older rows can undercount rejected-response usage: the backfill projects what was retained without relabeling outcomes, guessing tokens, or changing source rows. `unknown_usage_attempts` remains attempts minus responses with known usage.
- If valid individual responses sum past signed 64-bit range, the new Child diagnostics keep the attempt and response counters and mark `aggregate_tokens_overflow: 1` instead of writing partial totals. The projection retains those counters with null token and cache totals. Report publication and individual transport facts are unchanged.

## Local acceptance (review and rollout gates remain open)

- [x] Observed/estimated/unknown usage, failed attempts, rate provenance and FX correctly separated.
- [x] No prompt/output/raw inputs enter analytics storage/export.
- [x] Dry-run/apply only owned analytics projection with idempotency; original financial/report data unchanged.

## Operator procedure (not a rollout authorization)

After explicit approval, verified backup/off-host checksum/restore evidence, and migration readback, set `BUSINESS_USAGE_BACKFILL_DATABASE_URL` to an explicitly selected PostgreSQL URL. Use a role with `SELECT` on only the required Child source columns and `SELECT`/`INSERT` on `business_child_usage_projection`; no authoritative table writes. From `backend/` preview:

```sh
python -m app.modules.analytics.usage_backfill \
  --expect-database "$CONFIRMED_DATABASE_NAME" \
  --start 2026-10-01T00:00:00Z --end 2026-10-02T00:00:00Z
```

The default is a read-only transaction. Only aggregate counts and a digest are printed; no per-segment or per-attempt records are exported. Confirm the exact database, canonical `public` search path, `[start,end)` window (at most 31 days), planned insert count, and row bound (at most 5,000). Apply with the **same** arguments plus `--apply-digest "$APPROVED_PLAN_DIGEST"`. Changed projected facts or bounds invalidate the digest. Duplicate apply writes nothing; conflicts fail closed. The command never writes Child, report, payment, subscription, entitlement, business event or outbox rows. The two new tables refuse ordinary update/delete/truncate; migration downgrade refuses to drop populated evidence.

Do not treat the sampled transport store as a complete ledger: disabled collection, cancellation/crash, and analytics DB failures can leave gaps. No real provider, tariff, invoice, production migration/backfill, retention job, or export destination was configured in this slice. Dashboard wiring and operational capture coverage are separate from the internal reader and CLI.

## Evidence

The pure cost helper rejects counts outside the nonnegative signed 64-bit range and rates with more than 38 coefficient digits or a stored exponent outside −38…38. These are validation limits, not rounding rules. Valid inputs preserve exact subtotals across scales; unavailable usage or rates remain unavailable, and currencies are not combined.

- RED: `pytest tests/unit/test_business_cost_coverage.py -q -k 'counts_fail_before or rate_envelope or both_numeric'` — eight missing-validation failures; the valid boundary case passed.
- GREEN: `pytest -q tests/unit/test_business_provider_evidence.py tests/unit/test_business_cost_coverage.py tests/unit/test_llm tests/unit/test_child/test_content_v3.py tests/unit/test_business_event_schema.py tests/unit/test_business_cohorts.py tests/unit/test_business_monitoring_config.py` — 247 passed. Ruff lint/format and mypy passed for the 10 S09 Python files.
- PostgreSQL 16, migrated disposable `e23_s09_tests`: `pytest -q tests/integration/test_business_usage_evidence.py` — 2 passed. Exercised real Child persistence with mocked HTTP, failed and unknown transport facts, exact rates, privacy sentinels, SQL-enforced read-only preview, stale-plan refusal, and concurrent apply/replay. Fresh reads confirmed identical source, report, account, financial, entitlement, event and outbox rows across the backfill.
- Additive revision `7ad3c4e591b2`: empty upgrade/downgrade/re-upgrade passed; populated downgrade was refused and readback preserved the revision and stored usage. Final E23 head assembly and independent specification/code review remain open.
- Rejected-response follow-up: RED reproduced a mocked DeepSeek 503 (3 tokens) then 200 (9 tokens) persisting only 9 in Child diagnostics. GREEN on disposable PostgreSQL 16 at `7ad3c4e591b2` (`pytest -q tests/integration/test_business_usage_evidence.py`, 2 passed) read back 12 tokens across both responses in the ready segment and its projection. A legacy fixture retained 9 tokens and one unknown-usage attempt, with its failed section outcome unchanged. The unit regression slice (264 passed) also covered mocked OpenRouter errors with valid, invalid and non-JSON usage, plus admitted calls with no response. No real provider or deployed database was used.
- Overflow follow-up: RED left generation in `narrative_retry_waiting` after a mocked 503 at the signed 64-bit maximum followed by a 200 with 9 tokens. GREEN on disposable PostgreSQL 16 (`tests/integration/test_business_usage_evidence.py`, 3 passed) read back a ready publication, both exact attempt records, and null aggregate token/cache totals with both responses still counted. The 383-test regression slice covered Child lifecycle, narrative, transport and analytics contracts; the revised S09 migration passed empty downgrade/re-upgrade and still refused a populated downgrade.
