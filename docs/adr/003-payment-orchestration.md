# ADR-003: Payment Orchestration Layer

## Status

Accepted

## Context

Archemap processes subscription payments and must support multiple Payment
Service Providers (PSPs) — initially YooKassa (Yandex.Checkout), with plans to
add Stripe and others for international users.

Options considered:

1. **Direct PSP integration** — call YooKassa API directly from business logic
2. **Open-source orchestrator** (e.g., Hyperswitch) — self-hosted payment routing
3. **Custom orchestration layer** — thin internal abstraction over PSP APIs

## Decision

We build a **custom payment orchestration layer** as a dedicated module
(`app/modules/payments/`):

- A `PaymentProvider` protocol defines: `create_payment()`, `confirm_payment()`,
  `refund()`, `create_checkout_session()`, `list_payment_methods()`.
- YooKassa is the first provider. Stripe will be added when international
  support is needed.
- The orchestration layer handles:
  - Idempotency (keyed by `Idempotency-Key` header stored in Redis).
  - Webhook signature verification and event normalization.
  - Mapping PSP-specific statuses to our canonical status enum.
  - Retry logic for transient PSP failures.
- Webhook events are normalized and published to our internal event bus so
  subscription and billing modules react to them without knowing which PSP
  was used.

## Consequences

**Positive:**
- Adding a new PSP is an implementation detail — the subscription and billing
  modules are PSP-agnostic.
- Webhook handling is centralized — one verification and routing point.
- Idempotency is enforced at the orchestration boundary, preventing duplicate
  charges.
- Easy to test: mock the `PaymentProvider` protocol in tests.

**Negative:**
- Extra abstraction layer adds initial development time.
- PSP-specific features (e.g., YooKassa's smart payments) may not map cleanly
  to the common interface and need provider-specific API extensions.

**Neutral:**
- This is a module-level abstraction, not a standalone service. If we later
  extract it, the protocol boundary makes it straightforward.
