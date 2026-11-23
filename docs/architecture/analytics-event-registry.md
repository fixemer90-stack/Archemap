# E23 Analytics event registry v1

**Цель (SMART):** до подключения producers S03 закрепить конечный whitelist событий, authoritative producer и privacy/dedup границы; каждое новое событие получает executable schema и negative tests.

[Contract](./business-monitoring-contract.md), [Feature](../features/E23-business-monitoring/FEATURE.md).

## Internal registry

| Event                       | Authority                                      | Semantic identity                            |
| --------------------------- | ---------------------------------------------- | -------------------------------------------- |
| registration_completed      | committed auth/OAuth account creation          | user creation UUID                           |
| account_verified            | actual committed verification transition       | user/verification transition UUID            |
| basic_report_ready          | persisted basic Self usable artifact           | artifact/version UUID                        |
| checkout_created            | durable backend billing intent                 | local intent/payment UUID                    |
| payment_confirmed           | canonical confirmed PSP/local transition       | local payment UUID bound to merchant/mode    |
| refund_confirmed            | canonical refund path, not suspend helper      | persisted refund UUID                        |
| subscription_period_started | committed initial paid period                  | source payment/period UUID                   |
| renewal_confirmed           | canonical paid renewal result                  | renewal payment/period UUID                  |
| renewal_canceled            | committed future-renewal cancellation          | persisted cancellation identity              |
| report_requested            | accepted new/reuse/resume generation operation | operation/generation UUID                    |
| report_ready                | durable complete/usable terminal result        | immutable result UUID                        |
| report_partial              | durable partial terminal result                | immutable partial/version UUID               |
| report_failed               | persisted failed operation, not raw exception  | operation/attempt UUID                       |
| report_opened               | ownership-checked first-party observed reader  | view/dedup identity; never inferred from GET |
| provider_usage_observed     | actual attempt accounting                      | attempt UUID with provenance/coverage        |

Typed common metadata: schema_version=1; canonical UUID entity identity and optional subject; UTC-aware occurrence and recorded timestamps; mode in unknown/test/live; product in self/career/child/plus or absent; bounded numeric/enum details only. No free-text key/payload or automatic ORM serialization. A random event_id per retry is not semantic dedup. Persist original occurrence time; replays cannot drift the financial/source fact.

Unknown/naive/nonfinite/coerced-bool counts/extra keys are invalid. Details use an explicit closed schema; any newly admitted parameter requires contract/schema/test review. Only `registration_completed` may carry `registration_method` (`email` or `oauth`); absence means unclassified, not `email`. Neither value carries addresses, provider identities or tokens. Full executable field definitions live in `analytics.schemas` and must remain narrower than privacy allowlists.

## Browser/public registry

Only landing_view, signup_cta_click and plus_interest_click are public marketing goals. Only allowlisted public routes/placements/campaign codes after opt-in. Private report_opened is first-party only and never includes prose/birth data. Browser cannot authorize money, account verification or report readiness.

## Delivery versioning

S02 initially supports internal_projection destination only. Yandex conversion export needs S08 and explicit gates, not reuse of an internal claim retry as external exactly-once proof. New event kinds/fields/destinations require registry + schema + tests updated together. Retention/anonymization must preserve unrelated billing/report history and never use aggregate cleanup as permission to delete business source rows.
