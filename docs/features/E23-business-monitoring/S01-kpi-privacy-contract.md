# E23.S01: KPI, privacy и эксплуатационные gates

**Цель (SMART):** закрыть перечисленные критерии S01 воспроизводимыми tests/review/evidence до смены статуса на complete.

Status: ✅ Complete (contract and local verification)

[Feature](./FEATURE.md) · [Contract](../../architecture/business-monitoring-contract.md) · [Registry](../../architecture/analytics-event-registry.md)

## Scope

Implementation task T01. Do not infer live readiness from code/tests. External operations and authorizations are separate gates.

## Acceptance

- [x] KPI definitions and UTC/business-calendar/coverage semantics recorded.
- [x] D7 registration assignment, usable basic artifact, per-account UTC interval, boundary inclusion, maturity, same-cohort numerator/denominator and null/insufficient-history behavior are deterministic and independently specified.
- [x] Finite event registry, financial truth and privacy boundaries specified.
- [x] External counter/legal/retention/role/recipient decisions explicitly unresolved and default OFF; no fabricated approvals.

## Evidence

- The architecture contract fixes KPI definitions, sources, UTC and Moscow calendar boundaries, and coverage. The separate event registry defines the allowed events and data boundaries; browser events are not evidence of payment.
- Local verification: `pytest -q tests/unit/test_business_cohorts.py tests/unit/test_business_event_schema.py tests/unit/test_business_monitoring_config.py` — 51 passed. The D7 tests cover Moscow midnight, personal UTC deadlines, maturity and unknown rates; the config test verifies disabled integrations by default.
- Independent review found that the helper considered any in-window artifact instead of the first qualifying artifact. The two-artifact regression reproduced a false activation; the fix selects the earliest artifact independent of input order. Re-review raised no remaining S01 finding. Local foundation commit: `5d429da`. S03 still owns proof of the actual committed producer transition.
