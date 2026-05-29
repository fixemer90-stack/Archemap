# ADR-001: Modular Monolith Architecture

## Status

Accepted

## Context

We need to choose an architectural style for the Archemap platform. The system
handles user accounts, subscriptions, billing, and payment orchestration. It is
initially a small-team project that may need to scale individual components
independently in the future.

Options considered:

1. **Microservices** — independent deployable services per domain
2. **Traditional monolith** — single deployable with flat internal structure
3. **Modular monolith** — single deployable with strict module boundaries and
   clear dependency rules

## Decision

We adopt a **modular monolith** with the following principles:

- Each domain (auth, users, subscriptions, billing, payments) is a self-contained
  module under `backend/app/modules/`.
- Modules communicate through well-defined service interfaces (Python protocols),
  never by importing internals of another module.
- Each module owns its own database models, repository layer, and API router.
- A shared kernel (`app/core/`) provides cross-cutting concerns: configuration,
  database engine, security, and event bus.
- Inter-module communication within the process uses a lightweight in-process
  event bus. If we later extract a module into a service, the event bus adapts to
  a message broker with no change to module code.

## Consequences

**Positive:**
- Simple deployment — single Docker image, single process to manage.
- Fast iteration — no network hop overhead, easy local debugging.
- Clear boundaries — module isolation prevents spaghetti dependencies and
  prepares for future extraction if needed.
- Shared database transaction guarantees where required.

**Negative:**
- All modules share the same failure domain — a crash takes down everything.
- Vertical scaling applies to the whole application.
- Requires discipline to maintain module boundaries (enforced via linting rules
  and import guards).

**Neutral:**
- The event bus abstraction means moving to microservices later is a deployment
  change, not a code rewrite.
