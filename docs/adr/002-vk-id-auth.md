# ADR-002: VK ID as First Authentication Provider via Identity Brokerage

## Status

Accepted

## Context

Astrotype needs user authentication. The initial target market is Russian-speaking
users where VK (VKontakte) is a dominant platform. We must support additional
providers (Google, Telegram, etc.) over time without rewriting auth logic.

Options considered:

1. **Direct VK OAuth integration** — implement VK OAuth 2.0 flow from scratch
2. **Auth0 / Clerk / WorkOS** — third-party identity platforms
3. **Identity brokerage pattern** — build a thin abstraction that normalizes
   provider-specific flows into a common interface

## Decision

We implement an **identity brokerage** layer within the auth module:

- The auth module exposes a `Provider` protocol with methods: `get_authorization_url()`,
  `exchange_code()`, `get_user_info()`.
- VK ID is the first concrete provider implementation.
- New providers (Google, Telegram, email/password) are added by implementing the
  same protocol — no changes to the auth flow or API endpoints.
- User accounts are linked by `(provider, provider_user_id)` pair. A single
  Astrotype user may link multiple providers.
- JWTs are issued by our service (not delegated to VK) so we control token
  lifetime, claims, and revocation.

## Consequences

**Positive:**
- Clean separation between auth flow logic and provider specifics.
- Adding a new provider is a single module implementation (~200 lines).
- We own the session token, enabling fine-grained access control.
- VK ID compliance is isolated; swapping or removing it doesn't affect other
  providers.

**Negative:**
- We must implement and maintain each provider integration ourselves.
- Token refresh and provider-specific quirks live in our codebase.

**Neutral:**
- The brokerage is an internal pattern, not a reusable product — it's sized for
  our needs, not over-generalized.
