# Staging maintenance controller

## Scope and provenance

Published operator sources are `backend/scripts/child_staging_maintenance.py` and its bundled diagnostic `backend/scripts/child_staging_probe.py`. Copy **both unchanged from the independently reviewed `OPERATOR_SHA`** into the operator checkout on the approved Docker host. These are stdlib operator tools; the diagnostic uses the backend container's already-installed application dependencies. No application rebuild is needed to provision them. Keep `APPLICATION_SHA=4f104c8c6e6d297f99b382684ed8e62ebee7da03` separate from the operator-tool commit. The reviewed application CI is `41209406856`, completed/success, all eight jobs; tooling still needs its own independent review/exact-SHA CI.

This is a staging-only controller, not a generic Compose wrapper or production runbook. No application flags, account/grant/payment data, database rows, provider calls, production ingress or accepted markers are changed. The only external writes are CAS replacement of the **existing staging gateway's** loaded Caddy JSON, controller-owned gateway/scheduler restart policies, and graceful stop/start of the exact staging scheduler. It never stops a worker. Additional application recreation is a separately approved operation guarded by a fresh drain.

The supported native JSON shape was read from the existing staging gateway admin API on October 31, 2026: one `:8080` server, outer security/noindex headers and encoding, then a subroute whose first unconditional handler is Basic Auth, followed by API, metrics and frontend routes. The frozen configuration inserts an unconditional 503 **after authentication**, without removing any original route/header/account. Authenticated GET/HEAD/POST/PUT/PATCH/DELETE, metrics and frontend reads are all maintenance responses; this is deliberately **all-HTTP maintenance**, not read-only availability. Unauthenticated traffic still encounters Basic Auth. Restoring reinstalls the entire original JSON, not a reconstructed Caddyfile. Unsupported shapes fail before mutation. Native read-only validation of both original and frozen JSON passed on the existing Caddy binary; this is not a live maintenance HTTP/drain acceptance run.

The CAS contract is the official Caddy admin API's `GET /config/` Etag and `POST /config/` with `If-Match`. Transport is `docker exec -i <full verified staging gateway ID> sh -c 'nc -w 15 127.0.0.1 2019'`; configuration travels on stdin, never credential-bearing command arguments. There is no production Caddy request or public admin listener.

## Inventory, authority and private record

Run all following commands only in the separately approved staging window, as the single recorded Docker-host operator. Do not run them in this implementation/review lane. Use the already-approved strict-host-key/key-only transport; these commands run **on the Docker host**, not through a new unverified SSH mechanism.

Provision `/opt/astrotype-staging/maintenance` as an operator-owned 0700 directory, without symlinks in any path component. Every ancestor, up to `/`, must be owned by root or the operator and not group/world-writable; shared writable directories (including sticky `/tmp`) are rejected. Use a trusted operator-owned scratch/evidence tree instead. Reads walk directories with pinned no-follow descriptors and validate the actual opened file as regular, operator-owned, exactly 0600 and single-link before parsing it. Existing owner/mode must be inspected, never blindly changed. `PRIVATE_DIR` is another new operator-owned 0700 evidence directory. Every record/checkpoint/result is exclusively created 0600, with no symlinks or hardlinks; no credential/config contents should be printed. Only the signed mutable `state.json` is atomically replaced. Keep the key, original/frozen config, approved records, history and backups private and retained. One canonical host lock plus durable owner claim excludes concurrent runs even when the CLI exits between actions.

```bash
set -euo pipefail
umask 077
: "${CHECKOUT:?reviewed OPERATOR_SHA checkout on the Docker host}"
: "${OPERATOR_SHA:?independently reviewed full tooling SHA}"
: "${PRIVATE_DIR:?new private 0700 evidence directory}"
: "${MAINTENANCE_OPERATOR:?exact named operator}"
: "${MAINTENANCE_RECORD:?new absolute private approved-run JSON path}"
MAINTENANCE="$CHECKOUT/backend/scripts/child_staging_maintenance.py"
test "$(git -C "$CHECKOUT" rev-parse HEAD)" = "$OPERATOR_SHA"
test -f "$MAINTENANCE"
test -f "$CHECKOUT/backend/scripts/child_staging_probe.py"
python3 "$MAINTENANCE" inventory --output "$PRIVATE_DIR/inventory.json"
```

`inventory.json` contains the complete live Docker inventory, including non-staging protected containers: full IDs, exact names/project/service labels, image, running/start-time state, restart policy, network names/IPs/aliases, published bindings, and command/mount hashes. It omits environment values and raw command/mount payloads. An owned scheduler stop/start may release/reassign its IP and advance its start time; its exact ID/image, network names/aliases and other topology remain pinned unless a new scheduler is explicitly adopted. Non-staging/protected start times are not exempt. Record protected production markers/health separately in the existing release record; the controller proves its observed container-boundary inventory, **not production database-row or marker equality**.

Discover actual Celery replies and consumed queues privately using the already verified staging backend's full ID from this inventory. Never guess a wildcard node or derive a node name from a service name. Correlate each returned node's hostname with its exact worker/refinement-monitor/additional-consumer Docker `Config.Hostname`; the native adapter enforces that mapping. For example, after recording `STAGING_BACKEND_ID`:

```bash
: "${STAGING_BACKEND_ID:?exact full staging backend ID from the reviewed inventory}"
(set -o noclobber; docker exec "$STAGING_BACKEND_ID" celery -A workers.celery_app.app inspect ping --timeout 10 --json > "$PRIVATE_DIR/nodes.json")
(set -o noclobber; docker exec "$STAGING_BACKEND_ID" celery -A workers.celery_app.app inspect active_queues --timeout 10 --json > "$PRIVATE_DIR/queues.json")
```

This discovery is a control inspection, not an application-task dispatch. Missing replies are not permission to omit a consumer. Both standard consumers and every additional registered consumer must be recorded. Unknown task registry/schema/queue topology requires reviewed tool extension, never relaxing a guard during execution.

Have the named approver approve a JSON record with **all** these explicit fields before `freeze`:

- `version: 1`, `approved: true`, `environment: "staging"`, `project: "astrotype-staging"`;
- unique `run_id` matching `[a-z0-9][a-z0-9-]{0,63}`; nonempty `operator`, `approver`, `authority`; `operator` must equal `MAINTENANCE_OPERATOR`;
- exact full `application_sha` and `operator_sha`, plus `expires_at` as an approved Unix-time deadline (not an invented/default window);
- `controller_sha256` and `probe_sha256`, actual byte hashes of the two reviewed installed sources; the executable rejects different source bytes;
- `inventory`: the **entire** parsed `inventory.json` list, not only staging writers;
- `nodes`: object keyed by every exact returned node name, each with `service` and nonempty exact `queues` array; include `worker`, `refinement-monitor` and all additional consumers;
- `additional_stage_services`: exact extra consumer service names, or `[]`. Standard passive services are `prometheus`, `alertmanager`, `otel-collector`; unknown services are not silently passive;
- `producer_paths`: object with **exactly** `public_gateway`, `private_api`, `shared_edge_api`, `host_api`, `direct_broker`, `operator_scripts`. Each value describes the actual endpoint/network/listener, exclusion mechanism, owner and window. Review actual published bindings, shared-edge peers and non-Docker host/operator producers; a list of six vague labels is not a producer inventory;
- `assertions`: exactly the following keys, each explicitly `true`: `exclusive_operator_window`, `direct_producers_excluded`, `all_network_paths_reviewed`, `no_gateway_recreate_or_restart`, `no_scheduler_recreate`, `native_mock_no_payments`, `all_task_families_reviewed`, `protected_state_recorded`.

`native_mock_no_payments` describes the operation's authority: this controller must not make payment/LLM calls. It does **not** assert that inherited payment keys are already absent. The separately reviewed no-payment/private-network remediation must still be verified before qualification samples. `no_scheduler_recreate` means no unowned scheduler recreation; a replacement is permitted only by the separately approved exact-ID ownership transfer below.

These are operational inventory/exclusion assertions under a cooperative, exclusive operator window. Gateway maintenance alone does not firewall private/edge/host API or broker access. The controller cannot prove that a malicious root/operator cannot publish work or alter the host; it does not claim to. Do not set an assertion true merely because public ingress is blocked. If these direct paths cannot actually be excluded, do not freeze or recreate writers.

Do not source dotenv files. An approver may prepare a private fields JSON; this exact builder merges the observed inventory and source hashes, validates it, and exclusively writes `MAINTENANCE_RECORD` (it never defaults approval/operator/window/nodes/assertions):

```bash
python3 - "$MAINTENANCE" "$PRIVATE_DIR/inventory.json" "$PRIVATE_DIR/approved-fields.json" "$MAINTENANCE_RECORD" <<'PY'
import hashlib
import importlib.util
import pathlib
import sys
spec = importlib.util.spec_from_file_location("stage_controller", sys.argv[1])
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
record = module.read_private(pathlib.Path(sys.argv[3]))
record["inventory"] = module.read_private(pathlib.Path(sys.argv[2]))
record["controller_sha256"] = hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest()
record["probe_sha256"] = hashlib.sha256(module.PROBE_PATH.read_bytes()).hexdigest()
module.validate_record(record)
module.exclusive(pathlib.Path(sys.argv[4]), record)
PY
```

Hashing installed files does not replace reviewing their source/`OPERATOR_SHA`. The approver must bind those actual hashes to the reviewed artifact before execution. Do not edit a signed run's record, config, key or source afterward; a mismatching hash is STOP, not permission to regenerate evidence in place.

## Exact controller lifecycle

The following is the executable lifecycle invocation contract. Run each line as a standalone foreground command, not hidden inside an `if`, `!`, `&&` or `||` wrapper. A nonzero result stops progression. Preflight performs live identity/native-config/complete-node/task-family diagnostics without external state mutation; it never declares a drain. Freeze writes durable intent before each external action and reads back the exact target afterward.

```bash
python3 "$MAINTENANCE" preflight --record "$MAINTENANCE_RECORD" --operator "$MAINTENANCE_OPERATOR"
python3 "$MAINTENANCE" freeze --record "$MAINTENANCE_RECORD" --operator "$MAINTENANCE_OPERATOR"
python3 "$MAINTENANCE" status --record "$MAINTENANCE_RECORD" --operator "$MAINTENANCE_OPERATOR"
python3 "$MAINTENANCE" drain --record "$MAINTENANCE_RECORD" --operator "$MAINTENANCE_OPERATOR"
```

Freeze preserves all accepted worker work and reconciliation. It disables gateway **and scheduler** automatic restart, loads the authenticated all-HTTP maintenance response via Caddy CAS, then stops the scheduler with infinite grace (`docker stop -t -1`), never stopping backend/workers/data services. Kernel/API connections and accepted work can still be present after `freeze`; let them finish. The return value `FROZEN` is not `DRAIN_CONFIRMED`.

Every `drain` performs two full, live passes, with freeze and protected-inventory readbacks before/between/after them:

- broadcast node discovery equals the recorded set; every exact destination replies to ping, registered, active queues, active, reserved and scheduled; all recorded queues match and every occupancy list is empty;
- task registry matches the published 13-task inventory, including Child, Career, Self, profile dispatch/monitor, legacy PDF/narrative, notifications, renewal and reconciliation families;
- the effective PostgreSQL and Redis broker DNS resolves to the exact inventoried staging data-service IPs before Celery control messages or database reads;
- all Redis list keys (including priority-suffixed and forgotten queues) are empty, and all hash/zset entries, including unacked representations, are zero. Unknown nonempty hash/zset/list keys conservatively block drain; no purge/ack/revoke is performed;
- one repeatable-read/read-only transaction checks all nine generation/event/narrative/refinement tables plus `payments` and `payment_webhooks`; unknown lifecycle tables, unknown/nonterminal statuses, unsettled dispatch, pending payments/unprocessed webhooks or unknown/ambiguous diagnostics block drain. Legacy PDF/notifications/placeholder renewal/reconciliation tasks have no separate durable task-intent table; their broker/node settlement remains mandatory. Historical unknown diagnostics are deliberately conservative STOP even if another row appears terminal; obtain an incident decision rather than deleting them;
- no active/idle-in-transaction peer database session and no accepted/in-progress IPv4/IPv6 API socket on the supported `:8000` listener. Idle keep-alives can conservatively delay this check; let them close, never interrupt a live request to get zero.

Only a successful live double pass emits an HMAC-signed `DRAIN_CONFIRMED` decision, bound to the operator/run/config. Approval is rechecked after the final live readback; expiry leaves the checkpoint `FROZEN` without a decision. Validity is at most 30 seconds and never extends beyond either the original approval or any adopted identity-transfer approval deadline. Save the private signed checkpoint as evidence; HMAC proves local checkpoint integrity, not an independent approver's public-key signature. `status` is **not** fresh drain proof and never republishes `DRAIN_CONFIRMED`. Repeat `drain` immediately before every writer stop/recreation, even if a previous check passed. Never use a static environment variable, old decision or elapsed quiet interval as a replacement. The [full application backup SOP](./child-operator-procedures.md#application-backuprestore-sop) includes the mandatory exact private invocation immediately before its infinite-grace writer stop.

## Source recreation without reopening ingress

Keep the **same running gateway ID/config** throughout application refresh; never include gateway/data/passive services in application `up`, never run `compose down`, never restart/reload Caddy from its original source. Frozen original/maintenance JSON stays private in `/opt/astrotype-staging/maintenance/<run_id>/`. Gateway auto-restart is disabled before freeze, so a crash/daemon restart fails closed instead of loading the unmodified source without maintenance. If the gateway dies, retain the checkpoint and STOP for explicit recovery; this tool intentionally does not recreate/transfer a gateway. Do not restart it from the original Caddyfile to regain admin access. An incident-specific reviewed frozen-config bind/overlay and exact gateway ownership transfer would be needed; none is silently authorized by this CLI.

Build while workers remain alive; take/restore-prove the backup first. Immediately double-drain before stopping the exact recorded application writer IDs with infinite grace. Once they are already stopped, use only the approved complete staging Compose chain to recreate backend, worker, refinement-monitor and frontend. Keep scheduler stopped; when updating its image/settings, use Compose `create --no-deps scheduler`, **not** `up scheduler`. Use the controller-created private `/opt/astrotype-staging/maintenance/<run_id>/scheduler.compose.json` as the final pinned overlay (`MAINTENANCE_SCHEDULER_OVERLAY`); it contains only `services.scheduler.restart: "no"`, so a new stopped scheduler cannot auto-start on daemon restart. Render the complete actual Compose chain with this overlay before any recreation. Do not remove this overlay until controller restore and readiness/owner approval.

Any changed IDs/images/settings/network addresses require an explicit new approved identity-transfer record (same run/operator/tool/application target, fresh complete live inventory and actual new node/queue identities). The transfer may change only staging backend/frontend/worker/refinement-monitor, and optionally the scheduler below. Protected/non-staging containers, gateway, PostgreSQL/Redis and passive services cannot be blessed by adoption. The controller does not mutate or silently accept these changes. Verify new app settings/provider/no-payment/network/readiness independently while ingress is still frozen.

A **new** scheduler must be observed stopped, restart policy `no`, with explicit `scheduler_transfer` containing `old_id`, `new_id`, `approved_resume_owned_state: true`. This transfers the original controller-owned resume obligation; it does not authorize starting some unrelated previously stopped service. The original scheduler's running/stopped state and restart policy are retained for recovery. If it was originally stopped, the replacement stays stopped too. Keep the original immutable `MAINTENANCE_RECORD`; do not replace it with the transfer record.

```bash
: "${MAINTENANCE_TRANSFER_RECORD:?new separately approved exact live identity-transfer JSON}"
python3 "$MAINTENANCE" adopt --record "$MAINTENANCE_RECORD" --operator "$MAINTENANCE_OPERATOR" --replacement "$MAINTENANCE_TRANSFER_RECORD"
python3 "$MAINTENANCE" drain --record "$MAINTENANCE_RECORD" --operator "$MAINTENANCE_OPERATOR"
```

Adoption requires the retained signed pre-recreation drain, complete new empty live evidence, unchanged gateway maintenance, stopped scheduler and approved exact replacement inventory. It records the approved transfer in the signed checkpoint and clears the old decision. It performs no Docker mutation. Re-drain after adoption; before another recreation, repeat immediately again. Never use adoption to manufacture a missing pre-stop drain or to hide unknown outcomes.

## Exact restore and failure recovery

First verify every originally running consumer's readiness, effective flags/provider/payment exclusions, correct data/network identities, and durable reconciliation, then obtain the maintenance owner's go decision. Resume producers only when that decision permits new work. This is distinct from opening application writes for qualification; no automatic paid call is admitted by this controller.

```bash
python3 "$MAINTENANCE" restore --record "$MAINTENANCE_RECORD" --operator "$MAINTENANCE_OPERATOR"
python3 "$MAINTENANCE" status --record "$MAINTENANCE_RECORD" --operator "$MAINTENANCE_OPERATOR"
```

Restore uses only checkpoint-owned config/policies/scheduler state, reads back each change and complete protected inventory, and releases the durable owner claim only after `RESTORED`. It never starts workers/backend/data services or an unowned previously stopped scheduler. It reinstalls the **exact saved original Caddy JSON**, including authentication, noindex/security headers, metrics redirect/subroute and original read paths. Repeat restore is idempotent; a completed run cannot freeze again. Run public authenticated/unauthenticated health/read/write-boundary checks and protected production container/marker/health readbacks independently after restore. Do not infer those HTTP/marker results from a config comparison.

On any exception, failed drain, signal or lost transport: keep workers/data alive and retain private checkpoint/owner claim. Do not automatically recreate, repeat a POST/stop/start, purge, revoke or clear the journal. Re-enter `status`, read the exact target and retained `intent`, then use the **same** approved run's `restore` when safe. A settled intended target can be reconciled from readback without replay, including a response lost after success. If the target has not settled, the retained intent blocks retry/restore; an in-flight Docker stop can complete later, so an unchanged current state is not permission to clear it. Stale/unrelated Caddy JSON, protected drift, signature/source mismatch, missing nodes or unsupported topology stop before another mutation. Expired approval still permits same-owned-state `status`/`restore`, not a new freeze/adoption.

If restore itself fails, do not claim cleanup succeeded. Retain the primary failure and report which owned config/policy/scheduler obligation remains. If a process was recreated, only the explicitly approved adopted IDs are eligible for controller recovery. Do not start an old removed scheduler by name, restore old payment authority, or overwrite another operator's config. The controller has no production override, force-drain, finite worker-stop, purge, re-enqueue or marker-publication option.

## Verification boundary

Offline tests exercise native-shaped JSON, fake command/HTTP transport, full freeze/double-drain/exact-restore, signed private checkpoints, incomplete node/queue/task/durable/HTTP evidence, production denial/immutability, drift, re-entry/lost outcomes, exclusive lock/claim races and approved app identity transfer. Test URLs use disposable dead-port endpoints and `LLM_ENABLED=false`; no actual mutating Docker, application database, payment or provider operation is used. The published backup Bash is executed with command stubs, including success/failure/signals, and must run live controller drain immediately before writer stop.

Provisioning, actual authenticated/unauthenticated maintenance HTTP checks, complete live drain/restore, independently reviewed app refresh/isolation/no-payment settings and S15/S16 qualification remain execution gates. This source implementation and read-only Caddy validation do not claim a deployed controller, successful staging maintenance or E22 acceptance.
