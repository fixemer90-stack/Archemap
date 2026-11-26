# E23: Business monitoring and privacy-safe acquisition analytics

**Цель (SMART):** завершить S01–S10 проверяемыми срезами: owner-only business dashboard, typed atomic events, quality/cost visibility и default-off external analytics с отдельной live приёмкой.

Status: 🟡 Release `819f654` is running in production with internal recording and outbound integrations disabled. The owner confirmed that the admin dashboard opens; authenticated API evidence and activation acceptance remain open. See [S10](./S10-verification-rollout.md#evidence).

## Canonical contracts

- [Business monitoring](../../architecture/business-monitoring-contract.md)
- [Event registry](../../architecture/analytics-event-registry.md)
- [Payment confirmation baseline](../../architecture/current-payment-confirmation-flow.md)

## Stories

| Story                                       | Scope                                                | Status                                       |
| ------------------------------------------- | ---------------------------------------------------- | -------------------------------------------- |
| [S01](./S01-kpi-privacy-contract.md)        | KPI, privacy и эксплуатационные gates (T01)          | ✅ Local complete                            |
| [S02](./S02-event-outbox.md)                | Typed business events и transactional outbox (T02)   | ✅ Local complete                            |
| [S03](./S03-authoritative-producers.md)     | Authoritative domain producers (T03)                 | 🟡 In progress                               |
| [S04](./S04-business-overview-api.md)       | Read-only business overview API (T04)                | 🟡 Implemented; review pending               |
| [S05](./S05-consent-attribution-metrica.md) | Consent, attribution и public-only Метрика (T05)     | 🟡 Собственный счётчик реализован; production-включение и приёмка открыты, SDK Яндекса отложен |
| [S06](./S06-business-dashboard.md)          | Защищённый business dashboard (T06)                  | 🟡 Local browser checks passed               |
| [S07](./S07-aggregation-alerts.md)          | Aggregation, digest и alerts (T07)                   | 🟡 Local runtime checks passed               |
| [S08](./S08-yandex-conversion-export.md)    | Gated initial LIVE conversion export (T08)           | 🟡 Local runtime checks passed               |
| [S09](./S09-cost-coverage-backfill.md)      | Cost coverage и controlled projection backfill (T09) | 🟡 In progress                               |
| [S10](./S10-verification-rollout.md)        | Integrated verification и rollout (T10)              | 🟡 Production code deployed; acceptance open |

## Feature acceptance

- [ ] Every Story closed with spec and code-quality review and fresh local verification.
- [ ] No changes to paid access, merchant credentials, saved reports or LLM retry policy for analytics convenience.
- [ ] External activation has explicit owner inputs and actual network/delivery/financial readback evidence.

## What remains before closure

1. **Verify access and data quality.** Capture the production overview API's `200` and `Cache-Control: no-store` from an admin session, and `403` from an ordinary session. Run the [overview performance and coverage checks](./S04-business-overview-api.md). Owner-confirmed rendering and anonymous `401` are already recorded; neither proves the remaining API checks.
2. **Accept internal recording independently.** Approve the data retention and deletion rules, name the rollout operator, and run the [recording go/no-go checklist](./S10-verification-rollout.md#internal-recording-gono-go). Start coverage only after capture is verified; report D7 from a complete seven-day window, not from historical guesses or an incomplete cohort.
3. **Close source and external gaps independently.** [S03](./S03-authoritative-producers.md) still needs authoritative renewal/refund evidence. [S05](./S05-consent-attribution-metrica.md) needs browser history/cache coverage and a separately approved isolated SDK origin. [S07](./S07-aggregation-alerts.md) needs live timer and Telegram receipt/recovery evidence; [S08](./S08-yandex-conversion-export.md) needs the approved counter and real export/readback. [S09](./S09-cost-coverage-backfill.md) has local cost/backfill tests, not approval to run a production backfill. Keep these gates open even if the internal dashboard is accepted.

## Delivery order

```mermaid
flowchart LR
  S01 --> S02 --> S03 --> S04 --> S06
  S01 --> S05
  S02 --> S07
  S03 --> S08
  S03 --> S09
  S05 --> S08
  S06 --> S10
  S07 --> S10
  S08 --> S10
  S09 --> S10
```

External gates remain OPEN until actually executed: counter owner/ID/policy, retention and legal sign-off, approved admin/Telegram/budget, staging actual-SDK network proof, LIVE PSP/renewal/refund acceptance. Their absence does not authorize inventing secrets or silently enabling exports.
