# Child Report: controlled rollout and rollback

## Status and authority

Local implementation/QA is not permission to deploy. Production/canary is NOT verified by this document. E22 remains open until S15 staging budgets and S16 live gates have real evidence and an operator approves the target/window. Never execute deployment, paid-provider calls, account changes or database maintenance from this runbook without authorization for that environment.

Use synthetic adult/child fixtures on staging. Do not put child names, DOBs, answers, prose, credentials or complete exports into tickets, CI artifacts or this repository. Private manifests contain opaque IDs; store them with mode `0600`, outside the checkout. Tokens belong in environment variables, not command arguments or JSON manifests. Export/download URLs are authenticated, never public shares.

## Preconditions

The [operator procedures](./child-operator-procedures.md) define the two shells, private-directory initialization, approved fixture/credential acquisition, complete manifests, safe expiry/stale/failure triggers, application backup/restore SOP and explicit acceptance gate matrix. Missing approval, numeric budgets or fixture provisioning is a STOP condition, not a hidden default.

1. Choose and record the exact 40-character reviewed commit SHA, environment, operator, approved window, previous SHA/image IDs and rollback decision owner. Require a clean checkout at that SHA and green exact-SHA CI; do not substitute a green older run.
2. Verify an application backup/restore under the deployment's existing private backup policy. The local `scripts.child_backup_restore` CLI deliberately refuses application/remote databases: its proof applies only to synthetic QA databases on loopback port 55434, role `e22test`, names `e22_qa_test`/`e22_qa_restore`. It requires populated child/generation/report history and refuses a nonempty restore target. Never weaken those guards to back up production.
3. Confirm schema head, PostgreSQL health, Redis/broker health, worker registration of `child.generate_report`, scheduler registration of `child.reconcile_generations`, and readiness through the real HTTPS frontend/proxy. Preserve existing volumes and account/billing data. Do not run destructive pytest fixtures on any application database.
4. Verify proxy trust: HTTPS must reach the backend as an authenticated HTTPS request through the trusted reverse proxy. Production JSON export rejects an HTTP request. Never bypass this by trusting arbitrary client `X-Forwarded-Proto` headers.
5. Define numeric staging acceptance budgets BEFORE enabling: create/poll p95, deterministic-publication p95, narrative p95, PDF p95, maximum provider attempts/tokens/cost per report, maximum queued/in-progress age, reconciliation latency and terminal-failure rate. Record sample size, load, currency, provider/model and observation window. Missing budgets or measurements block canary; local wall times and disabled-provider runs are not staging cost evidence.
6. Confirm a safe telemetry sink, dashboard/readback and alert recipient. Worker native OTEL instruments are `child.worker.operations`, `child.worker.duration` (seconds) and `child.provider.attempts`; labels are only bounded operation/outcome values. Inspect the collector/exporter for actual final series names. Prove scrape visibility and a delivered test alert; authored instrumentation is not proof that metrics/alerts are live.

## Flag and process controls

`CHILD_REPORT_ENABLED` defaults to `false` in development, staging and production Compose. It is explicitly passed to backend, worker, scheduler and refinement-monitor. Set it in the operator-owned environment file used with Compose; an env-file change requires recreating affected processes. It controls admission of writes, not deletion of persisted artifacts. Reads/status, existing questionnaire views, PDF and authenticated export remain available when off; new questionnaire creation is refused when no saved questionnaire exists. In-flight accepted work is allowed to finish/reconcile.

There is no `NEXT_PUBLIC_CHILD_REPORT_ENABLED` implementation. Do not invent a browser-only kill switch. The backend catalog/access decision is authoritative. A frontend code/build-time configuration change still requires a new build/image, not merely container environment changes.

Example staging commands, on the approved staging Docker host after all mutation prerequisites pass. `CHECKOUT` is the clean reviewed Git checkout; `RELEASE_DIR` is its separately checksum-verified release archive. Supply the approved values; do not derive a project from the checkout basename:

```sh
export TARGET_SHA='<approved full SHA>'
: "${CHECKOUT:?absolute reviewed Git checkout}"
export RELEASE_DIR="/opt/astrotype-staging/releases/$TARGET_SHA"
export CHILD_ALERT_SECRETS_DIR=/opt/astrotype-staging/secrets/child-alertmanager
export CHILD_ALERT_PROBE_DIR=/opt/astrotype-staging/alert-probes/child
test "$(git -C "$CHECKOUT" rev-parse HEAD)" = "$TARGET_SHA"
test -z "$(git -C "$CHECKOUT" status --porcelain)"
compose() {
  docker compose -p astrotype-staging --project-directory "$RELEASE_DIR" \
    --env-file "$RELEASE_DIR/.env.staging" -f "$RELEASE_DIR/docker-compose.staging.yml" "$@"
}
compose config --quiet
# Before build/up: privately compare rendered PostgreSQL/Redis/Prometheus volume
# names with live inspect mounts, require existing approved bind sources and
# correct private networks. See the identity guard in the operator procedures.
compose build backend worker scheduler refinement-monitor frontend
compose up -d --no-deps backend worker scheduler refinement-monitor frontend
compose ps
compose exec -T backend python -m alembic current
for service in backend worker scheduler refinement-monitor; do
  compose exec -T "$service" python -c 'from app.config import settings; print("child_enabled", settings.CHILD_REPORT_ENABLED)'
done
```

Use `.env.production`/`docker-compose.prod.yml` only in a separately approved production window after staging passes. Do not use the development Compose file on a public deployment. Record actual container image IDs and compare the running application source checksums with the approved commit; a requested SHA supplied to the smoke CLI is not deployed-SHA verification.

Staging backend startup runs `alembic upgrade head` automatically before Uvicorn. Therefore `up backend` is a migration boundary: the application backup/restore and flag-off admission gates must precede it. Do not treat startup as read-only, and do not rerun a lost rollout response blindly. These are application rollout examples, not instructions to restart the unchanged application for an operator-tooling/docs-only update.

## Fixture acquisition and full staging exercise

1. Create two authenticated synthetic adult accounts using normal registration/login. Adult A has a current persisted natal chart and canonical Plus or direct `child` access; adult B is used for foreign-owner denial. Also retain a Free account and an expired-access case. Do not promote direct Child access to unrelated products or change real customer entitlements.
2. Through the real product UI/API, create A's exact, approximate and unknown-time child records. Unknown must use `birth_time:null`; never guess a time. Save returned child IDs privately. Read every write back from the API.
3. For each child, GET `children/{id}/questionnaires/current`; record the returned session/age snapshot. Answer the server-returned questions using server-returned option codes, reload to prove autosave/resume, review and consent, then POST complete with one stable key. Complete must reject missing/invalid fields without partially sealing the draft.
4. POST `/reports` with only `child_profile_id` and `questionnaire_session_id`, plus a stable `Idempotency-Key`. Poll the returned `generation_id`, not the child ID. Verify real broker/worker execution and persisted events; require useful deterministic content before prose and the configured terminal state. Repeat the identical accepted request after a new snapshot/chart exists: it must return the original accepted generation. A new key with stale questionnaire age must be rejected.
5. Switch between two children and prove no cross-child answers, chart IDs, scores, generation IDs or report payload. Verify mismatched child/session, foreign owner, nonexistent, archived and deletion-pending resources. Free/expired denial must contain only the documented lock allowlist, never names, DOB, answers, prose, snapshots or artifact URLs. Foreign/missing use the same minimal owner query/status/body; inspect query plan/latency class under equivalent staging load, not a single wall-clock comparison.
6. Exercise controlled provider failure without exposing exception/provider text. Useful deterministic content stays readable. A deliberate retry after terminal failure needs a NEW client key; an ambiguous transport retry preserves its OLD key. Unknown external outcome must not be recalled automatically. Verify provider intent/attempt accounting from persisted rows and telemetry, not only HTTP status. Never simulate a timeout against a paid provider unless its cost/unknown-outcome experiment was explicitly approved.
7. Open the reader on desktop/tablet/mobile and use keyboard only through child selection, questionnaire review, reader disclosure and retry. Require no horizontal overflow, no serious/critical accessibility violations, no client errors and all 15 sections. Check late session expiry preserves already loaded read-only content while disabling writes/polling.
8. Update a stale age block. Poll until `age_update_ready` or `age_update_failed`; both are terminal. Core report/version stays immutable. Export PDF with the reader's exact `age_snapshot_id`; compare section order/body/actions, numerical age, confidence notes and metadata with the same presentation. Read/export must not silently create another snapshot.
9. Download authenticated JSON export, including an archived record; verify its complete owned Child graph, no sibling data and no worker/provider secrets. Delete only synthetic test fixtures via the documented archive/purge modes; verify account, billing, parent natal data and sibling child survive. Record the privacy-safe audit result, not the exported personal data.
10. Measure the predefined staging budgets and prove telemetry/alert delivery. Any safety, ownership, leakage, unknown-outcome, idempotency or data-loss failure blocks canary immediately; no statistical tolerance applies to these failures.

## Automated read probes

From `backend`, use a private JSON array manifest. The enabled inventory must be EXACTLY: `exact`, `approximate`, `unknown`, `two_child`, `locked`, `foreign`, `provider_failure`, `pdf`.

Each entry has `name`, `path`, `token_env`. Successful JSON probes also require `equals`: JSON-pointer-to-expected-value assertions. The CLI enforces a nonempty `/id` assertion for exact/approximate/unknown/two-child records, `/generation_id` for provider-failure generation probes, and `/report_id` for flag-off report reads; a status-only assertion is rejected. `two_child` additionally requires nonempty `forbidden_values` containing the sibling's private identifiers. `exact`/`approximate`/`unknown` target the respective GET child record; `provider_failure` targets its failed narrative generation; `locked` uses an existing owned resource with Free/expired credentials; `foreign` uses another active owner's token against A's resource. `pdf` must use `/api/v1/child/reports/{report_id}/pdf?age_snapshot_id={canonical UUID}`. No other query, credentials in URLs, foreign URLs or redirects are allowed.

Example entry shape (substitute real private opaque IDs, not literal placeholders):

```json
{
  "name": "unknown",
  "path": "/api/v1/child/children/<child-id>",
  "token_env": "CHILD_SMOKE_OWNER_TOKEN",
  "equals": {
    "/id": "<child-id>",
    "/birth_time_confidence": "unknown",
    "/birth_time": null
  }
}
```

```sh
.venv/bin/python -m scripts.child_rollout_smoke \
  --base-url https://staging.astrotype.ru \
  --manifest "$PRIVATE_DIR/child-enabled.json" \
  --sha "$TARGET_SHA" --phase enabled \
  --gateway-user-env CHILD_GATEWAY_USER \
  --gateway-password-env CHILD_GATEWAY_PASSWORD \
  --report "$PRIVATE_DIR/child-enabled-result.json"
```

The report deliberately says `deployed_sha_verified:false`, `provider_execution:NOT_PROVEN_BY_READ_PROBE`, `staging_budgets:NOT_MEASURED`. Close those gates using the independent steps above, never by editing the probe output. A read probe cannot prove real-provider execution, cost, queue recovery, browser UX, PDF content parity or notification delivery.

## Staging Child alert delivery

The staging Compose project includes a private, nonroot, read-only Alertmanager. It has no published port or edge-network membership; its state volume is staging-only. The default route drops unrelated alerts. Only `environment=staging, feature=child` routes to the existing Telegram receiver; message text uses fixed classifications/status, never raw annotations, labels, exceptions or Child identifiers.

Before starting this infrastructure, provision the existing bot token and configured home chat privately as `telegram_token` and `telegram_chat_id`. Do not copy the whole Hermes `.env`, put values in Compose/environment output, or commit them. Set `CHILD_ALERT_SECRETS_DIR` to the absolute private directory (for this staging: `/opt/astrotype-staging/secrets/child-alertmanager`). Its parent is root-only `0700`; the two mounted files are `0400`, owned by UID/GID `65534:65534`. A separate readable probe directory is selected by `CHILD_ALERT_PROBE_DIR` (here `/opt/astrotype-staging/alert-probes/child`). Both repository-relative default directories are gitignored. Missing secret files fail closed rather than becoming Docker-created directories. This uses outbound Telegram API calls only; do not change the existing gateway, bot webhook or polling.

Validate both actual binaries before deployment:

- `prom/prometheus:v2.53.1`: `promtool test rules prometheus-child-alerts.test.yaml` from the mounted `deploy` directory, without container networking. Cases include zero observations, all terminal failure classes, pending/firing/resolution, privacy label stripping, high duration and the first observed counter already equal to one. `increase()` alone misses that last case; the rule additionally bounds newly observed nonzero failure series to a five-minute window.
- `prom/alertmanager:v0.34.1`: `amtool check-config /work/alertmanager-child.staging.yaml`, with read-only secret-file mounts and networking disabled. CI runs the same parser with synthetic dummy files, never production or Telegram credentials.
- Render the complete real Compose configuration privately; assert unchanged PostgreSQL/Redis/Prometheus volume identities, private receiver mounts and no new ingress membership. Require green exact-SHA `Validate Child Alerting` before image/build acceptance.

For infrastructure-only changes, start only Alertmanager and recreate only staging Prometheus after snapshotting rollback configuration and existing mount/data identities. Do not recreate application, gateway, collector or production services unnecessarily. Preserve both existing non-Child rule files exactly. Read back Alertmanager readiness, Prometheus scrape state, active Alertmanager discovery and loaded Child rules through the private network; public metrics UI must retain Basic Auth on both bare and trailing-slash paths.

For a controlled delivery drill, create one operator-owned temporary rule in the mounted probe directory, not the repository. Use alert name `ChildAlertDeliveryProbe`, `expr: vector(1)`, `for: 1m` and fixed `environment=staging, feature=child, severity=info` labels. Send SIGHUP to staging Prometheus only. Record actual pending/activeAt, hold the literal for-duration, require firing plus a successful Telegram notification, then change the same rule's expression to `vector(0) > 0` and reload. Require inactive/resolved state and a separate resolved notification before removing the probe and reloading again; deleting a firing rule immediately can rely on a later TTL instead of proving normal resolution. Restore/remove the probe in `finally` after any failure. No application records, provider calls or fabricated Child data are needed for this drill.

Make the mounted probe directory readable by nonroot Prometheus (`0755`) and its synthetic rule file readable (`0644`); the enclosing host parent may remain private. Do not infer delivery from `alertmanager_notifications_total` alone: it counts notification attempts. Correlate the expected alert/receiver and completed `alertmanager_notification_latency_seconds_count` with `alertmanager_notification_requests_total`; require zero increases in both notification and request failure counters. Abort attribution if another real Child alert is active. The authenticated metrics prefix redirects `/career-metrics` → `/career-metrics/` (308), then Prometheus redirects to `/career-metrics/graph` (302); verify the final UI response is 200 without weakening Basic Auth.

Executed evidence: alerting source `40f3fb1b4aca2f39a48553689feaca893c2ceb2c`, CI `40235132422` (8 successful jobs). Native drill `2026-10-25T21:40:41Z`–`21:42:11Z` held the one-minute condition for 62.294404 seconds and completed exactly two Telegram notifications/requests with zero failures. Probe removal, private hardening, two inactive permanent Child rules, one active Alertmanager, preserved Prometheus volume/non-Child rule bytes and unchanged 17 protected container identities were read back. Application source remained `06b72c0`; no production rollout or accepted-marker advancement occurred. Detailed artifacts are private under `/opt/astrotype-staging/evidence/40f3fb1b4aca2f39a48553689feaca893c2ceb2c/`.

The permanent rules cover observed worker terminal failures (`for: 1m`) and worker-duration histogram p95 above 120 seconds (`for: 2m`). Those are operational staging thresholds, not an established paid-provider latency/token/currency budget, and no nonexistent stuck/cost gauge is invented. Alert delivery does not close the still-required full S15 budget or S16 production/canary gates.

## Rollback drill and canary

Before canary, set `CHILD_REPORT_ENABLED=false` in the selected environment file and recreate backend/worker/scheduler/refinement-monitor. Verify settings in API and worker. Do NOT stop PostgreSQL/Redis, drop tables, truncate events, delete artifacts, downgrade immutable lineage or clear durable provider intents. Preserve in-flight work and let fenced workers finish/reconcile; terminating an external call can create an unknown outcome.

The disabled manifest contains EXACTLY `flag_off_read` and `flag_off_write`. Read points at the previously published report with asserted report/child IDs. Write POSTs `/api/v1/child/reports` with a legitimate owned completed child/session pair so authentication/ownership/validation cannot mask the flag check. Expect 503, no new generation/events/segments, no enqueue/provider attempts, no billing/entitlement mutation. Reads, pinned PDF and export stay available. Compare persisted row counts and artifact hashes before/after; the HTTP probe alone does not establish no side effects.

```sh
.venv/bin/python -m scripts.child_rollout_smoke \
  --base-url https://staging.astrotype.ru \
  --manifest "$PRIVATE_DIR/child-disabled.json" \
  --sha "$TARGET_SHA" --phase disabled \
  --gateway-user-env CHILD_GATEWAY_USER \
  --gateway-password-env CHILD_GATEWAY_PASSWORD \
  --report "$PRIVATE_DIR/child-disabled-result.json"
```

Record successful rollback and re-enable only with the decision owner. Current flag is global, not a percentage/cohort switch: do not describe a global enable as canary. A restricted internal cohort needs separately approved ingress/account restrictions (without weakening canonical access checks); if no restriction is available, keep production off until an explicit global-release decision. Define observation window, sample size and stop conditions in the approved release record. Staging, rollout and canary remain incomplete until that record exists.

## Evidence record (required, not fabricated defaults)

- Exact approved/deployed SHA, previous SHA, image IDs, clean-source/runtime checksum proof, timestamps/timezone, environment, operator and approver.
- Private fixture registry: owner account IDs, child/session/generation/report/snapshot IDs, confidence path; no child PII or tokens.
- Per-scenario HTTP/worker/persisted/browser/PDF outcomes, idempotency and two-child isolation assertions, row-count/hash comparisons and provider-call accounting.
- Predefined budgets, measured distributions/sample size/load/cost, authoritative stale-job observations, collector scrape/rule evaluation and alert-delivery proof.
- Flag-off admission/read/side-effect proof, rollback result, approved canary restrictions/window and stop/go decision.
- Open gates and failures remain unchecked in S15/S16. Local synthetic proof and CI do not close deployed, paid-provider, staging-budget, production or canary gates.
