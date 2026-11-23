# E23 Business monitoring: implementation contract

**Цель (SMART):** к завершению E23 показать владельцу read-only business overview с проверенными источниками, privacy-safe opt-in public analytics и доставляемыми alerts; закрывать каждую Story только после её executable acceptance. Срок внешнего запуска определяется после получения counter/consent/операторских данных, не подменяется датой кода.

Status: implementation in progress. [Feature](../features/E23-business-monitoring/FEATURE.md), [event registry](./analytics-event-registry.md).

## Decisions fixed for engineering

1. Marketing attribution: Yandex Metrica. Business/financial truth: committed backend state plus canonical PSP confirmation. Operational telemetry: existing OTel. No PostHog/session replay/warehouse/new microservice in MVP.
2. External tracking/export/delivery defaults OFF. No counter ID, legal approval, retention duration, Telegram recipient or budget has been supplied. These are explicit external gates, not placeholders to invent. Implement/test locally with mock PSP/LLM; never create a paid report/payment as analytics smoke.
3. Business API is server-superuser only. Never derive authorization from a client flag/email, automatically promote the owner, or expose aggregates to ordinary accounts. GET overview uses read-only queries, not reconciliation-writing billing/access services.
4. Financial mode unknown stays unknown. TEST, manual grants and unproven rows are not LIVE cash or MRR. Merchant/mode/renewal/refund readiness depends on E6/payment hardening; analytics must not silently repair billing.
5. All SQL business windows are [from,to), events UTC, presentation Europe/Moscow unless explicitly selected. Keep currency separate and amounts exact Decimal/minor units. Missing source/coverage/denominator means unavailable, not zero.

## KPI contract

- Registrations: committed unique account creations, with email/OAuth path classification; verification is a real first verified transition, not an email send.
- Service activation D7 is defined by the deterministic per-account observation contract below, not by the duration of the registration calendar bucket. Reader open is a separate observed UI event, never inferred from GET/prefetch.
- Checkout: distinct durable intent, not button clicks/retries. Pending and unknown outcomes are visible separately from failed.
- LIVE cash received: one canonical paid LIVE provider payment once; four entitlement grants never quadruple money. Confirmed refunds use refund identities, not suspend invocation counts. Cash after refunds is not accounting profit or post-fee revenue.
- Active paid Plus: effective paid period/access policy at as_of, not account_tier or a stale active status. MRR only recurring LIVE plans; cancel_scheduled remains in current-period MRR until expiry, but not next-cycle expected MRR. One-time month access is not MRR; unimplemented/unproved renewal is not_certified.
- Attribution/conversion: never divide all backend registrations by only consented Metrica visits as an exact rate. Unknown attribution is not organic. CAC/ROAS need real spend and comparable attribution windows.
- Report delivery: distinguish new/reused/resumed/retried generation, ready/partial/failure, and total acceptance-to-durable-result duration.
- Cost: validated observed provider usage versus estimate versus unknown. Include failed/retried calls. No rates/FX/usage means unknown with coverage, not free generation. Display USD and RUB separately without a dated FX contract.
- Retention cohorts require mature observation windows. Zero denominator is null/unavailable. No low-traffic rate alert from one event.

### Deterministic D7 activation contract

1. Assign an account to a registration cohort iff its authoritative committed account-created timestamp `t_signup` is in the selected Moscow calendar bucket converted to UTC `[cohort_from_utc, cohort_to_utc)`. OAuth and email account creation use the same clock semantics; login/account linking is not another registration.
2. The qualifying artifact is the first persisted, account-owned basic Self v2 report with the canonical usable deterministic foundation committed and renderable. A chart-only snapshot, requested/queued operation, legacy placeholder or failure does not qualify. LLM prose need not be complete: this metric means **received a usable basic calculation**, not **read the full narrative**. S03 must prove the producer is attached to this actual persistence transition.
3. For each account independently, `deadline = t_signup + timedelta(days=7)` on UTC-aware instants (seven elapsed 24-hour days, not seven Moscow date labels and not a day-seven bucket). It activates iff the first qualifying artifact time `t_ready` satisfies `t_signup <= t_ready < deadline`. An artifact after the registration bucket closes still qualifies when inside this per-account interval; one exactly at `deadline` does not.
4. An account is mature iff `as_of_utc >= deadline`. Count mature and immature accounts separately. Mature denominator is the number of distinct mature accounts in the selected registration cohort; numerator is the distinct activated accounts among that same mature set. Never count immature accounts as unsuccessful activations or count ready events outside the per-account window.
5. A readiness fact and its outbox commit with the Self foundation, but neither timestamp on the fact proves visibility. Use a durable precommit lower bound and a separate owner-bound postcommit upper bound. PostgreSQL retains the write-once provenance and observation so historical reads do not depend on the source report still existing. Ignore a candidate only when its durable lower bound is strictly after `as_of`, even if its observation is pending. Only count a first readiness whose bounds prove it falls in the strict interval. Historic facts without evidence, mismatched lineage and ambiguous bounds make the mature-cohort numerator and rate unavailable, not zero. A signup with no readiness fact is a nonactivation only when its full observation window is covered by verified uninterrupted capture. Do not backfill readiness times from report timestamps or a retry.
6. The primary cohort D7 rate is returned only when the selected cohort has no immature accounts, no unresolved first-readiness evidence and a positive mature denominator: numerator / mature denominator. Otherwise value is null with `unavailable` (unresolved evidence or incomplete coverage), `insufficient_history` (immature accounts present) or `no_data` (zero denominator). Preserve maturity counts when coverage permits, and do not show a partial-maturity subset rate as the final cohort result. The default comparison cohort must have an elapsed observation window; current-day registrations can legitimately have no D7 rate yet.
7. Golden cases must cover registration just before Moscow midnight with a next-day ready artifact, signup at cohort upper boundary, ready before signup, ready exactly at deadline, `as_of` exactly at deadline, unknown or missing proof, no fact under continuous capture, mixed maturity and empty cohorts. Calendar bucketing and UTC elapsed-time comparison must be tested independently.

## Persistence and transaction boundary

BusinessEvent is owned analytics storage with typed event name, stable semantic identity, aware occurred_at, recorded time, explicit mode, bounded product/outcome/numeric fields and optional private UUID subject/entity references. No arbitrary payload bags or strings. These references are pseudonymous personal data, not anonymized data.

emit_business_event persists the event and internal projection outbox atomically in the caller transaction, never commits the caller or does external I/O, and returns an immutable receipt. Rollback of the business mutation implies no event/outbox. A duplicate semantic identity returns the original only for matching facts freshly read from the database. A failed emit (including validation, semantic mismatch, or persistence failure) rolls back the entire current caller transaction, so catching the error and committing cannot persist the business change. Callers must use a transaction scoped to that unit of work. Concurrent transactions share database uniqueness, not process-local sets.

A queue claim is a positive bounded lease with a fresh token; completion/retry requires the current claim. A stale worker cannot finalize a reclaimed delivery. Replay of internal_projection is idempotent. External conversion delivery is a separate future operation: expired lease or lost acknowledgment never proves that external upload did not happen. Do not auto-retry unknown external effects merely because local claim expired.

Append-only source facts and mutable delivery state are separate. Schema/index definitions must match ORM; migration is additive from actual Alembic head. Downgrade cannot silently destroy populated event history. Backup/off-host checksum/restore proof precedes any production schema or backfill mutation. No existing user/profile/report/payment/entitlement table is dropped, reset or cleaned up.

## Privacy boundary

No external SDK runs on the application origin, including the landing page. A public pathname or full-document navigation does not isolate persistent auth and report storage from same-origin JavaScript. Any future deployment must use an independently reviewed isolated origin without access to app storage, credentials or private context, and pass approved live network sentinel tests before activation. It remains limited to the allowlisted landing flow after valid-version opt-in and approved counter/policy configuration. No shared-root tag, noscript pixel or pre-consent external queue. All replay/form/clickmap/link/auto-goals stay OFF.

No names/email/phone/hash, birth/child data, coordinates, answers, report/prompt text, auth/verification/reset tokens, raw entity IDs, arbitrary UTM/query/hash/referrer or exception text goes to Yandex. Route predicate/defer/manual hit alone is not network privacy proof. Validate clean current and original URL/referrer; deny when uncertain. Require full-document navigation to private forms, revoke/destruct and back/bfcache/race evidence for any future SDK, and effective private `Referrer-Policy: no-referrer` through ingress. The first-party landing sends a null ClientID until an isolated design is accepted. S05 pins the one server-approved counter at capture and owner binding; only an exact policy/counter match at both preflight and final owner-row-locked admission can enter S08. Neither legacy null provenance nor a browser assertion can select an export destination. The permanent export fence commits synchronously before admission; revocation and admission are serialized through the bounded one-shot attempt, and unknown outcomes never replay. Missing attribution never blocks product use, and account revocation remains reachable when collection is off.

Analytics, consent and attribution must not insert or require a Career upsell in Self reports, force a Career CTA as a condition of continuing, gate ordinary product use behind an upsell, or change existing product navigation/access. Measure only existing or separately approved voluntary paths; tracking refusal must not degrade report use. S05/S06 must preserve this invariant in UI/source regressions.

First-party collector binds to authenticated owner, accepts only UI subset, validates size/rate/Origin/CSRF/schema. Browser cannot submit payment_confirmed/report_ready. Identity and consent version are not arbitrary trusted body fields. External export is later opt-in initial-LIVE-only, one mechanism/goal, stable original event time, upload-status audit; no browser purchase duplicate.

## Unresolved operator/legal gates

| Gate                                                    | Current decision                                                  |
| ------------------------------------------------------- | ----------------------------------------------------------------- |
| Counter account, stage/prod numeric IDs, permissions    | Not supplied; external OFF                                        |
| Approved privacy/consent policy/version and publication | Not supplied; external OFF                                        |
| Retention durations/deletion/legal basis per data class | Owner/specialist decision; no destructive retention job           |
| Business administrator                                  | Existing server-superuser policy; no automatic role assignment    |
| Telegram bot/chat and permitted recipients              | Not supplied; outbound OFF; do not copy Hermes secrets            |
| Budget, incident thresholds and escalation owner        | Proposed defaults only; no automatic paid retry or service cutoff |
| LIVE merchant/renewal/refund readiness                  | Separate payment acceptance remains open                          |

## Gates and closeout

DATA_SAFE: strict schema, atomicity, isolation, migration/rollback guard, RBAC and privacy negatives proved. PAID_TRUTH: actual merchant/mode/payment/refund provenance and same-source readback; no synthetic promotion. ATTRIBUTION_READY: approved policy/counter, actual SDK network proof, consent/ClientID coverage and accepted upload behavior.

Internal summary target freshness 5 minutes; stale warning after 10 minutes is a proposed configuration to validate, not observed runtime. Daily digest proposed 10:00 Europe/Moscow. Alert data is central/durable, deduplicated and tested for delivery/recovery; independent dead-man must detect stopped producer. Scheduling a TODO is not acceptance.

Each Story records changed paths, RED/GREEN, lint/typecheck, source revision/fingerprints, independent spec review then code-quality review, runtime proof where required and open external gates. Parent feature remains incomplete until all Story criteria close. Code merge does not prove live SDK/Telegram/payment acceptance.
