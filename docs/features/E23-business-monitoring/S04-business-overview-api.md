# E23.S04: Read-only business overview API

**Цель (SMART):** закрыть перечисленные критерии S04 воспроизводимыми tests/review/evidence до смены статуса на complete.

Status: 🟡 Implemented; independent review and integrated release evidence pending

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
- Independent review found duplicate-identity, mixed-cohort and financial coverage gaps. RED on disposable PostgreSQL reproduced a duplicate signup in the overview. The correction filters canonical identities, classifies each payment once, and adds PostgreSQL cases for duplicate payment proof, conflicting ownership, invalid amounts, an unrelated grant, observed zero, and mixed maturity. The remaining operational requirement is to inspect SQL plans on representative history before rollout; the 90-day input limit alone is not a plan or load proof.
- The second review reproduced orphan confirmation facts, duplicate PSP receipts across local payment rows, and an overflow at the earliest ISO date. The correction counts unmatched facts and ambiguous PSP references as unknown and withholds cash; unrepresentable dates return 422. The mounted PostgreSQL test exercises aggregates with monitoring enabled as well as the default-off route.
- Disposable PostgreSQL plus adjacent unit checks: `pytest -q tests/integration/test_e23_overview_postgresql.py tests/unit/test_e23_overview_route.py tests/unit/test_business_cohorts.py tests/unit/test_business_monitoring_config.py --tb=short` — 29 passed. Exact-path Ruff lint/format passed; the latest mypy run timed out. No PSP or LLM was invoked. The corrected revision still needs independent sign-off and immutable amount evidence for financial certification.
