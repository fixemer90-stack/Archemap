# E23.S07: Aggregation, digest и alerts

**Цель (SMART):** закрыть перечисленные критерии S07 воспроизводимыми tests/review/evidence до смены статуса на complete.

Status: 🟡 Local implementation; external acceptance pending

[Feature](./FEATURE.md) · [Contract](../../architecture/business-monitoring-contract.md) · [Registry](../../architecture/analytics-event-registry.md)

## Scope

Implementation task T07. The Celery worker consumes `internal_projection` in bounded transactions with the day counts, outbox completion, and successful-projector heartbeat committed together. Beat runs both analytics tasks every minute on the existing `celery` queue when `BUSINESS_MONITORING_ENABLED=true`. Apply the migration before enabling writers or Beat. Operator messages are durable local records, not evidence of Telegram delivery.

The digest snapshots the latest due completed Moscow calendar day at 10:00 `Europe/Moscow`, using `[from,to)` UTC bounds. It defers if the heartbeat is missing or stale or if that day has a pending, leased, or exhausted projection row. It deduplicates by business date and only counts observed events, by bounded event type, mode, and optional product. It does not report cash, infer an absent denominator, or resend for later-arriving facts. Late facts update the central projection; historical catch-up of missed digests is not automatic beyond the latest due day.

The backlog rule opens on pending work aged 10 minutes or exhausted attempts. The provider rule covers persisted non-mock Career provider-classified failures, not PSP health or all model traffic. It opens on at least three distinct affected generations and at least as many failures as successes in 30 minutes. Recovery requires at least three distinct newer successful generations and more successes than failures. Silence, validation errors, or multiple sections from one generation do not prove recovery or independently trigger an incident. Active incidents send at most one local reminder per hour while the rule remains breached, and a single resolved message when positive evidence clears the condition.

## Independent watchdog

`deploy/systemd/archemap-business-watchdog.{service,timer}` runs the DB-only observer every minute without requiring Celery, the API, Redis, or the Telegram sender. Install a matching, immutable backend release and Python environment at `/opt/archemap-business/backend` (or override both `WorkingDirectory` and `ExecStart`), with read/execute access for the dynamic user. Install the units under `/etc/systemd/system`; use a private, systemd-readable `/etc/archemap/business-watchdog.env` containing an explicit `DATABASE_URL` and `BUSINESS_MONITORING_ENABLED=true`. Provision private DB reachability from that runner (for a container-only DB, a private DB endpoint or an explicitly shared socket outside private `/tmp` is required; do not publish a public port for this timer). No Telegram credentials belong on the watchdog. After migration and operator approval, only the host operator runs `systemctl daemon-reload` and `systemctl enable --now archemap-business-watchdog.timer`.

Collect the journal/exit codes and detect missed invocations via an **independent** monitor; the timer alone will not page on host loss. The observer reports `healthy` (0), `stale` (1; no successful projector commit in 10 minutes or never run), `unavailable` (2; cannot evaluate/commit, including DB failure), `busy` (3; another watchdog transaction holds the lock), or `disabled` (4). A PostgreSQL outage cannot be journaled to PostgreSQL; use the runner output and an external monitor. With a separate Telegram timer, a durable stale or resolved notice can be sent even with Beat and Redis down, provided the DB and Telegram remain reachable.

## Telegram delivery (default off)

Do not install or enable the optional `deploy/systemd/archemap-business-telegram.{service,timer}` without approved recipients and a staged rollout. Provision the same backend release, and set `DATABASE_URL`, `BUSINESS_MONITORING_ENABLED=true`, `BUSINESS_ALERTS_ENABLED=true`, and the approved activation instant `BUSINESS_TELEGRAM_ACTIVE_SINCE` (ISO 8601 with offset, e.g. `2026-06-01T07:00:00Z`) **only** in `/etc/archemap/business-telegram.env`. Supply the token and one numeric chat ID (no handles or recipient lists) as root-owned mode `0600` files `/etc/archemap/business-telegram.token` and `/etc/archemap/business-telegram.chat-id`; systemd passes them as credentials, not argv or environment. Do not reuse any other service's bot secret. Apply `e23s07t001` first, use one sender per environment, and only then enable its timer through the same explicit operator workflow. Turning either flag off stops further sends. Stop the timer and its service for an immediate rollback; if resuming after a pause, use a new activation instant to exclude notices from the pause. Do not delete delivery fences.

One tick selects at most one notice newer than activation and at most 24 hours old. The text contains only registered incident codes or a Moscow-date digest of aggregate event counts by mode, across products. Delivery state retains only the local message key, status, and timestamps. The Telegram call uses a fixed HTTPS endpoint, no proxy or redirects, a five-second total timeout and a capped response body. An HTTP success alone is insufficient: a valid positive message ID for the configured chat is required. `acknowledged` means the Bot API acknowledged it, not that an operator read it.

A PostgreSQL checkpoint is committed before HTTP and transitions to `acknowledged` only after a valid receipt. Crashes, cancellations, commit ambiguity, HTTP failure (including rate limits), and malformed receipts can leave a permanent `indeterminate` fence; invalid local content is recorded as `invalid_message` with no HTTP call. A crash after checkpointing but before HTTP may leave a notice unsent. This is the deliberate loss-versus-duplicate tradeoff: do not redispatch, because this API has no idempotent send key. Reconcile indeterminate notices manually with the approved destination; never clear a fence to resend. Collect the sender journal as well: `idle`/`acknowledged` (0), `indeterminate`/`invalid_message` (1), `unavailable`/`misconfigured` (2), `disabled` (4). Receipt/incident recovery acceptance with an approved Telegram recipient remains separate.

## Acceptance

- [x] Concrete tasks registered and exercised through real test broker/worker, not scheduled TODOs.
- [x] Durable central incident/aggregation state, dedup/cooldown/resolved and independent dead-man proved.
- [x] Daily business timezone and synthetic provider outages tested; Telegram request/response, durable suppression on failure, and independent timer tested locally.
- [ ] Deploy and monitor the independent timer; approve the destination and accept real Telegram delivery/recovery separately.

## Evidence

- Follow-up disposable PostgreSQL/Redis run: 30 tests passed, including seven runtime integration cases. The used S07 downgrade was rejected and the four delivery fence rows remained. This is not real Telegram delivery or production timer acceptance.

Original projection and watchdog evidence from `backend/`, before the Telegram follow-up:

- RED: `BUSINESS_MONITORING_ENABLED=false .venv/bin/python -m pytest tests/unit/test_business_operations.py -q` failed on the missing operations module before implementation. GREEN: that suite plus `tests/unit/test_business_event*.py` and `tests/unit/test_celery_async_interruption.py` passed (55 tests).
- `bash scripts/test_business_operations.sh -q`: 7 passed. Isolated PostgreSQL/Redis Unix sockets; real Beat sends both task names at accelerated test intervals and a separate solo Celery process commits/readbacks through PostgreSQL. Covered concurrent projection, rollback, leased/exhausted backlog, positive provider recovery from persisted synthetic outage signals, Moscow boundary and digest replay. With Beat and worker stopped and the observer's broker address unreachable, a separate CLI process reported stale; a restarted worker resumed heartbeat without another count and the CLI recorded one resolution.
- Harness upgraded `e23s07b001`, downgraded an unused instance to its predecessor, then reapplied it. After use, downgrade was rejected and readback showed `e23s07b001` plus 10 retained operator messages. Parent integration must linearize parallel revisions and rerun the combined migration chain.
- Scoped `ruff check`, `ruff format --check`, and `mypy --follow-imports=silent`: 10 Python paths passed. Compose rendered flag `false` and `true` for backend, worker, and scheduler with a disposable environment file.
- Base `d70623c`; SHA-256 of the `sha256sum` manifest over S07's three analytics modules, task, migration, harness, and two test files (in that order): `57cee3c4155abb5f11a4b949e00cff34220dea76262b45c49d58e023c7997433`.

Telegram and timer follow-up:

- RED: `BUSINESS_ALERTS_ENABLED=false .venv/bin/python -m pytest tests/unit/test_business_telegram.py -q` could not import the not-yet-implemented transport. GREEN: that file plus `tests/unit/test_business_operations.py`, `tests/unit/test_business_event*.py`, and `tests/unit/test_celery_async_interruption.py`: **75 passed**.
- `bash scripts/test_business_operations.sh -q`: **30 passed**. `e23s07t001` upgraded after `e23s08a001`, downgraded cleanly while unused, and re-upgraded. Fresh PostgreSQL reads inside mock HTTP proved the pre-send fence was already committed; concurrent/replayed senders made no duplicate calls after success, lost response, or cancellation. Used downgrade refused; current revision/readback was `e23s07t001` with four fences retained.
- `systemd-analyze verify` passed on the two service/timer pairs with the local interpreter path substituted. A temporary user-mode copy of the watchdog timer (sandbox directives adapted for the test user manager) fired on a minute boundary and journaled `business_projection_watchdog=unavailable`, exit 2, with deliberately unreachable DB/Redis sockets. Combined with the disposable Beat/worker shutdown/recovery test above, this proves the timer trigger and independent observer locally. No persistent units were installed or enabled.
- Ruff check/format and `mypy --follow-imports=silent` passed on nine changed Python files. Follow-up code/unit manifest SHA-256 at base `d70623c`: `c7da2294cb13596be173b2bea0cac26a810f75ad5a9f74d6a82ce260dbe2380f`.

Open gates: independent specification/code-quality review on the integrated diff, deployed timer/independent monitoring, approved recipient, and real external Telegram delivery/recovery acceptance. The provider signal is scoped to Career and was exercised with persisted synthetic outcomes; no actual upstream outage or real external requests were induced.
