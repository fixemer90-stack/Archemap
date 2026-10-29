# Child staging: operator procedures and explicit gates

This is the executable companion to [the rollout runbook](./child-report-rollout.md), not permission to deploy. Execute mutations only in the recorded staging window. Production, paid-provider calls and canary remain separately gated. Never run destructive pytest fixtures against application databases.

## Locations, authority and credentials

Two shells have different jobs:

- Client checkout: reviewed clean Git checkout, `backend/.venv/bin/python`, HTTPS access to staging. Run `scripts.child_rollout_smoke` here.
- Approved staging Docker host: SSH as the authorized operator, verified Docker project `astrotype-staging`. Run the stdlib-only `backend/scripts/child_runtime_state.py` here, from a reviewed operator checkout. Do not assume WSL's Docker daemon is the VPS daemon.

Initialize a fresh private read-only evidence record. `OPERATOR_SHA` identifies the reviewed tooling/docs checkout; it is **not** the deployed application revision. Record `APP_SHA` only if all application consumers share one verified revision; otherwise record separate API, frontend, worker, scheduler, refinement-monitor and infrastructure revisions/image IDs plus their active Compose file chain in the private release record. Composite deployments must not be flattened to the operator SHA. Read-only checks need neither a new release archive nor a build/redeploy. Supply the following from the approved operator record, never the current directory:

```bash
set -euo pipefail
: "${OPERATOR_SHA:?approved full tooling source SHA}"
: "${CHECKOUT:?absolute reviewed Git checkout}"
: "${PRIVATE_DIR:?new absolute private evidence directory outside checkout}"
[[ "$OPERATOR_SHA" =~ ^[0-9a-f]{40}$ ]]
[[ "$CHECKOUT" = /* && "$PRIVATE_DIR" = /* ]]
case "$PRIVATE_DIR/" in "$CHECKOUT/"*) exit 1 ;; esac
test "$(git -C "$CHECKOUT" rev-parse HEAD)" = "$OPERATOR_SHA"
test -z "$(git -C "$CHECKOUT" status --porcelain)"
umask 077
mkdir -m 700 "$PRIVATE_DIR"
export CHILD_ALERT_SECRETS_DIR=/opt/astrotype-staging/secrets/child-alertmanager
export CHILD_ALERT_PROBE_DIR=/opt/astrotype-staging/alert-probes/child
```

For a separately authorized application rollout, `TARGET_SHA` is the intended application revision and `RELEASE_DIR` is its checksum-verified Git archive, not necessarily a Git checkout. Assert Git identity in the application build checkout, then archive/checksum and compare deployed application source separately. Do not run `git rev-parse` in a directory without `.git` and infer release identity from a parent repository. A read probe's `--sha` is a recorded label, not identity verification: use `OPERATOR_SHA` and retain independent runtime identities alongside its output.

Only for application rollout, privately provision the approved staging `.env.staging`, staging gateway auth include and every required data bind in the new release. They are operator-owned inputs, not files to invent or copy from production. The following base-file identity guard applies to the staging rollout example; an active deployment with overlays must use its recorded complete Compose chain instead. Missing release inputs/overlay inventory is STOP. Before any `build/up`, execute this identity guard on the staging host; it never prints the rendered environment:

```bash
python3 - "$RELEASE_DIR" <<'PY'
import json,subprocess,sys
from pathlib import Path
r=Path(sys.argv[1]);assert r.is_absolute()
cmd=['docker','compose','-p','astrotype-staging','--project-directory',str(r),'--env-file',str(r/'.env.staging'),'-f',str(r/'docker-compose.staging.yml')]
cfg=json.loads(subprocess.check_output(cmd+['config','--format','json'],text=True))
for service,target,key in [('postgres','/var/lib/postgresql/data','postgres_staging_data'),('redis','/data','redis_staging_data'),('prometheus','/prometheus','prometheus_staging_data')]:
    live=json.loads(subprocess.check_output(['docker','inspect','astrotype-staging-'+service+'-1'],text=True))[0]
    assert live['Config']['Labels']['com.docker.compose.project']=='astrotype-staging'
    actual=next(m['Name'] for m in live['Mounts'] if m['Destination']==target)
    assert cfg['volumes'][key]['name']==actual
for service in cfg['services'].values():
    for v in service.get('volumes',[]):
        if v['type']=='bind':
            p=Path(v['source']);assert p.is_absolute() and p.exists()
            if v['target'].startswith('/run/secrets/'):assert p.is_file()
am=cfg['services']['alertmanager'];assert not am.get('ports') and set(am['networks'])=={'default'}
print('PASS: staging volume identities and existing private binds')
PY
```

Credential names for public probes are `CHILD_GATEWAY_USER`, `CHILD_GATEWAY_PASSWORD`, `CHILD_SMOKE_OWNER_TOKEN`, `CHILD_SMOKE_FOREIGN_TOKEN`, and `CHILD_SMOKE_LOCKED_TOKEN`. Load values through the approved secret manager/private launcher. Never source dotenv files, pass credential values in argv, print login JSON or place tokens in manifests. With gateway flags the CLI sends Basic Authorization to the gateway and the selected actor's `access_token` cookie to the backend. Without those flags it retains API-client Bearer mode. Both gateway environment names are mandatory together; redirects are not followed.

## Fixture acquisition ledger

Checkpoint each returned ID immediately in `$PRIVATE_DIR/fixtures.json`; never publish DOB/name/password/prose. Keep one stable idempotency key for each accepted operation and retain it after an ambiguous transport outcome.

| Operation                       | Supported acquisition                                                                                                                                             | Required input / private checkpoint                                                                                                                                                                                                                                                                                           |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Synthetic adults A/B/C          | `/register`, `/login`; or POST `/api/v1/auth/register` then `/api/v1/auth/login`                                                                                  | Register JSON: `email,password,name,birth_date,birth_time,birth_time_accuracy,birth_place,latitude,longitude,timezone`. Use synthetic adults; obey verification if `requires_verification` is true. Login JSON: `email,password`. Capture cookie/access token privately, not stdout. Reuse sessions; obey 429/Retry-After.    |
| Identity/profile                | GET `/api/v1/users/me`, GET `/api/v1/profiles`                                                                                                                    | Record user ID and owned profile ID from `items`; do not confuse profile and report IDs.                                                                                                                                                                                                                                      |
| Parent natal report             | POST `/api/v1/astrotype-v2/reports` with `profile_id`                                                                                                             | On `already_exists`, read returned report; otherwise checkpoint generation and poll `/api/v1/astrotype-v2/reports/generations/{generation_id}`. Read `/api/v1/astrotype-v2/reports/{report_id}`; current narrative state is nested at `report.status`. Stage provider must remain mock.                                       |
| Access fixtures                 | Canonical Plus/direct `child` entitlement, provisioned by the authorized synthetic-fixture operator                                                               | No public self-grant endpoint exists. Reuse the approved registry below or obtain explicit fixture provisioning. Never improvise customer DB edits or a real payment. C must first own a child while access is active, then its synthetic grant expires. Using B's child with C's token tests 404, not owned-resource 402.    |
| Exact/approximate/unknown child | POST `/api/v1/child/children`, stable `Idempotency-Key`                                                                                                           | JSON: `display_name,relationship_type,birth_date,birth_time,birth_time_confidence,birth_place,caregiver_context`. `birth_place` is `{label,latitude,longitude,timezone}`; context is `{primary_caregiver,daily_contact,boundary_role,soothing_role}`. Unknown uses null time. Read returned `/children/{id}` and record `id`. |
| Questionnaire                   | GET `/api/v1/child/children/{id}/questionnaires/current`                                                                                                          | Record `session_id,age_snapshot_id`; use returned `questions[].key/options[].code`, never positional guesses. PUT `/questionnaires/{session_id}/answers` with `{"answers":[{"question_key":"server-key","option":"server-code"}]}`. GET again to prove resume.                                                                |
| Confirmation/report             | POST `/questionnaires/{session_id}/complete` with `{}` and stable key; POST `/reports` with `child_profile_id,questionnaire_session_id` and a separate stable key | Complete returns `session_id`; report admission returns `generation_id`. Poll `/generations/{generation_id}`. Record `report_id` and GET `/reports/{report_id}`; pin PDF to `presentation.metadata.age_snapshot_id`.                                                                                                          |

Existing approved synthetic registry is private at `/opt/astrotype-staging/evidence/01e41a9d548e2510d2aa54295f76524e4b91881f/fixture-identities.json`. The colocated `session.py` issues bounded native sessions only for its verified synthetic identities; capture its output inside the private launcher, never run it to visible stdout. The colocated `grant.py` supports `grant/expired/restore` only for the registry's synthetic owner and records original grant fields. It is an operator fixture tool, not a general authorization API. A separate C-owned expired fixture and its allowlisted grant controller are retained under `/opt/astrotype-staging/evidence/6114db2cdbd2e5f64fec858c8133fd2b054c181a/locked-fixture/`. Those private paths are explicit provisioning dependencies; a fresh environment without them must provision equivalent synthetic identities under approval before claiming this inventory is runnable.

## Complete private manifests

No complete reusable probe manifest or credential launcher path is established by this document. The fixture registry/session/grant paths above are not a launcher or a full scenario inventory. Before probes, the approved fixture operator must privately provide (1) enabled eight-case and disabled two-case JSON manifests with real owned IDs, pinned snapshots and retained failure fixture, (2) the exact launcher path/command and reviewed source identity that loads gateway credentials and bounded A/B/C sessions into the probe environment without printing them, (3) the separate locked-owner fixture/controller and (4) access/expiry authorization and cleanup ownership. Use `$PRIVATE_DIR/child-enabled.json` and `$PRIVATE_DIR/child-disabled.json` as newly provisioned output filenames, not claims that files already exist. STOP if any dependency, launcher invocation or allowlisted fixture is unavailable; do not invent a launcher path, run `session.py` visibly, self-grant access or execute placeholders. Even the enabled PDF GET may persist a cached artifact: only the state helper is strictly read-only; HTTP probes need their recorded fixture permission.

Substitute the ledger's actual opaque IDs. These are templates, not executed example results. `locked-owned-child` belongs to C, whose access has expired; the foreign case uses active verified B against A's resource. The failed generation is a retained terminal fixture, not an invented ID.

```json
[
  {
    "name": "exact",
    "path": "/api/v1/child/children/<exact-child>",
    "token_env": "CHILD_SMOKE_OWNER_TOKEN",
    "equals": { "/id": "<exact-child>" }
  },
  {
    "name": "approximate",
    "path": "/api/v1/child/children/<approximate-child>",
    "token_env": "CHILD_SMOKE_OWNER_TOKEN",
    "equals": { "/id": "<approximate-child>" }
  },
  {
    "name": "unknown",
    "path": "/api/v1/child/children/<unknown-child>",
    "token_env": "CHILD_SMOKE_OWNER_TOKEN",
    "equals": { "/id": "<unknown-child>" }
  },
  {
    "name": "two_child",
    "path": "/api/v1/child/children/<exact-child>",
    "token_env": "CHILD_SMOKE_OWNER_TOKEN",
    "equals": { "/id": "<exact-child>" },
    "forbidden_values": ["<sibling-child-id>", "<sibling-chart-id>"]
  },
  {
    "name": "locked",
    "path": "/api/v1/child/children/<locked-owned-child>",
    "token_env": "CHILD_SMOKE_LOCKED_TOKEN"
  },
  {
    "name": "foreign",
    "path": "/api/v1/child/children/<exact-child>",
    "token_env": "CHILD_SMOKE_FOREIGN_TOKEN"
  },
  {
    "name": "provider_failure",
    "path": "/api/v1/child/generations/<failed-generation>",
    "token_env": "CHILD_SMOKE_OWNER_TOKEN",
    "equals": { "/generation_id": "<failed-generation>" }
  },
  {
    "name": "pdf",
    "path": "/api/v1/child/reports/<report>/pdf?age_snapshot_id=<canonical-snapshot-uuid>",
    "token_env": "CHILD_SMOKE_OWNER_TOKEN"
  }
]
```

The disabled manifest has a valid owned completed questionnaire, not a malformed body that could mask the flag gate:

```json
[
  {
    "name": "flag_off_read",
    "path": "/api/v1/child/reports/<report>",
    "token_env": "CHILD_SMOKE_OWNER_TOKEN",
    "equals": { "/report_id": "<report>", "/child_id": "<child>" }
  },
  {
    "name": "flag_off_write",
    "path": "/api/v1/child/reports",
    "token_env": "CHILD_SMOKE_OWNER_TOKEN",
    "body": {
      "child_profile_id": "<child>",
      "questionnaire_session_id": "<completed-session>"
    }
  }
]
```

## Read-only persisted-state evidence

Run on the staging Docker host. The helper verifies the exact container plus Docker project/service labels, refuses production/other databases, and wraps SQL reads in read-only transactions. Files are private, baselines cannot be overwritten, errors never print rows/credentials. Default scope is all `child_` tables plus users/profiles/entitlements/payments (currently 21). It is not a single cross-table MVCC snapshot: use a quiescent window; concurrent writes invalidate equality and require investigation, not ignored differences.

```bash
STATE="$CHECKOUT/backend/scripts/child_runtime_state.py"
python3 "$STATE" --container astrotype-staging-postgres-1 --snapshot "$PRIVATE_DIR/before.json"
# Execute exactly one approved denied/replay/rollback scenario.
python3 "$STATE" --container astrotype-staging-postgres-1 \
  --compare "$PRIVATE_DIR/before.json" --report "$PRIVATE_DIR/after.json"
```

`--all-public` adds every public table and normalized public schema hash for application restore comparisons. `--database` accepts only disposable `e22_restore_<12 lowercase hex>_<digits>` names; omission selects the staging application's configured database. It never permits arbitrary DB URLs or production targets. Full application mode and protected-Child mode are distinct scopes; do not compare different scopes or call a 21-table hash check a full restore proof.

## Application backup/restore SOP

This is for a separately approved staging maintenance window, not a command to execute during a read probe. On the approved host verify `astrotype-staging-postgres-1` project/service labels first. Record production identities/marker, staging writer identities and retained rollback images. Complete the mandatory drain below first; no external provider call or unknown outcome may be interrupted. Never stop production, PostgreSQL or Redis.

### Mandatory quiescence before consumer recreation or writer stop

1. Record maintenance authorization, all producer/consumer identities, exact Celery node names and their consumed queues from the live approved Compose chain. Freeze new ingress writes using the existing approved maintenance controller (not an invented flag toggle that itself recreates consumers); prevent all other API/direct task producers, then stop the scheduler producer only. Keep workers and reconciliation available while accepted work finishes. If the maintenance controller or full producer inventory is unavailable, STOP without recreating anything.
2. On the authorized host use the existing pinned `compose` function from the rollout runbook. Supply each exact node name from the recorded inventory, never a guessed wildcard. Run these read-only inspections for **both** worker services and any additional registered consumers. Capture output privately: Celery task diagnostics may contain identifiers/arguments.

```bash
set -euo pipefail
: "${CELERY_NODE:?exact recorded Celery node name}"
for inspection in ping active_queues active reserved scheduled; do
  compose exec -T worker celery -A workers.celery_app.app inspect "$inspection" \
    --destination "$CELERY_NODE" --timeout 10 --json \
    > "$PRIVATE_DIR/drain-${CELERY_NODE}-${inspection}.json"
done
```

3. Require replies from every expected node, empty `active`, `reserved` and `scheduled` sets, and zero pending messages on every recorded consumed broker queue, using the approved broker diagnostic. Inspect persisted `child_generations`, `child_generation_events` and `child_segment_generations` diagnostics for queued/running work and unresolved external outcomes; inspect other task families too. Celery replies alone do not establish broker emptiness or a settled provider outcome. Missing reply (including a busy solo worker), unknown queue inventory, queued work, scheduled work or an unknown provider outcome is STOP: let workers finish/reconcile or obtain a separate incident decision, never revoke/purge/re-enqueue to manufacture a drain.
4. With producers still frozen, repeat the complete inspections and broker/persisted checks immediately before stopping/recreating consumers. Record a signed operator drain decision in the private release record and set `DRAIN_CONFIRMED=true` only after these checks pass. This variable is an explicit manual gate, not automated drain proof. Keep maintenance in place across the transition, read back readiness/flags and reconcile durable state before restoring producers/ingress. A stop timeout is not a drain strategy; never let Docker kill a worker with active/reserved/scheduled work or unresolved provider outcome. If state changes, clear confirmation and STOP.

The following Bash sequence runs only after that drain, stops only currently running staging writers/frontend, creates a private nonempty custom archive, restores only into a uniquely created disposable DB, compares all public schema/table rows, rechecks the source, and restarts those services. The already paused scheduler must be recorded separately and resumed only after readiness and the maintenance owner's go decision; it is not restarted by this trap. It deliberately retains the dump/manifests. Any failed comparison blocks rollout; inspect private artifacts before retrying. `CHECKOUT`, `PRIVATE_DIR` and `OPERATOR_SHA` are the validated tooling values above, on this Docker host. No `--clean`, application drop or schema deletion is allowed.

```bash
(
set -euo pipefail
umask 077
test "${DRAIN_CONFIRMED:-false}" = true
PG=astrotype-staging-postgres-1
STATE="$CHECKOUT/backend/scripts/child_runtime_state.py"
# This guard also proves the correct Docker daemon/project before stopping anything.
python3 "$STATE" --container "$PG" --all-public --snapshot "$PRIVATE_DIR/pre-freeze-identity.json"
RESTORE_DB="e22_restore_${OPERATOR_SHA:0:12}_$(date +%s)"
created=false
writers=()
for service in backend worker refinement-monitor frontend; do
  name="astrotype-staging-$service-1"
  if test "$(docker inspect -f '{{.State.Running}}' "$name")" = true; then writers+=("$name"); fi
done
cleanup() {
  status=$?
  trap - EXIT INT TERM
  if $created; then
    docker exec "$PG" sh -c 'dropdb -U "$POSTGRES_USER" "$1"' sh "$RESTORE_DB" || { if ((status == 0)); then status=1; fi; }
  fi
  if ((${#writers[@]})); then
    docker start "${writers[@]}" || { if ((status == 0)); then status=1; fi; }
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
# Infinite grace: never escalate a stop to SIGKILL if the drain was invalidated.
if ((${#writers[@]})); then docker stop -t -1 "${writers[@]}"; fi
python3 "$STATE" --container "$PG" --all-public --snapshot "$PRIVATE_DIR/application-before.json"
# Require populated application history. Before the first Child migration,
# legacy public tables suffice; when Child tables exist require their history.
python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));t=d["tables"];assert any(v["rows"]>0 for v in t.values());assert "child_profiles" not in t or all(t[n]["rows"]>0 for n in ["child_profiles","child_generations","child_reports"])' "$PRIVATE_DIR/application-before.json"
(set -o noclobber; docker exec "$PG" sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$PRIVATE_DIR/application.dump")
test -s "$PRIVATE_DIR/application.dump"
sha256sum "$PRIVATE_DIR/application.dump" > "$PRIVATE_DIR/application.dump.sha256"
docker exec "$PG" sh -c 'createdb -U "$POSTGRES_USER" "$1"' sh "$RESTORE_DB"
created=true
docker exec -i "$PG" sh -c 'pg_restore --exit-on-error --no-owner --no-privileges -U "$POSTGRES_USER" -d "$1"' sh "$RESTORE_DB" < "$PRIVATE_DIR/application.dump"
python3 "$STATE" --container "$PG" --all-public --database "$RESTORE_DB" \
  --compare "$PRIVATE_DIR/application-before.json" --report "$PRIVATE_DIR/restore-proof.json"
python3 "$STATE" --container "$PG" --all-public \
  --compare "$PRIVATE_DIR/application-before.json" --report "$PRIVATE_DIR/source-unchanged.json"
)
```

The subshell scopes shell options and traps: cleanup finishes before the next caller command on success, failure, INT or TERM. It preserves the original failure/signal status; a cleanup failure turns an otherwise successful run into status 1. Run this as a standalone command, not inside `if`, `!`, `&&` or `||` (which suppress Bash `errexit`). On nonzero status stop; do not run acceptance steps. Untrappable termination (SIGKILL/host loss) still requires operator recovery.

After the trap completes, independently verify every originally running service's readiness and public staging health, then production health/unchanged identities/marker. The cleanup owner is the recorded staging operator. The retained dump must stay root-private under the deployment backup policy; checksum and restore success do not imply indefinite retention. The previous application backup is `/opt/astrotype-staging/evidence/06b72c0f06c6f50a1831d407ec1350eb2f9e7bf8/staging-before.dump`, with `backup-proof.json`/`application-before.json` in that directory. Read back file presence/checksum before relying on it. Its historic proof covers 66 tables/56 nonempty and unchanged source; it predates later synthetic fixtures and must not be called a backup of those later rows.

## Safe scenario trigger matrix

| Scenario                                     | Trigger and expected boundary                                                                                                                                                                                                                                                                                       | Invariants / cleanup                                                                                                                                                                                                                                                                                                                                                                      |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Late authentication expiry                   | Follow the isolated late-expiry recipe below for a saved draft, confirmation review or ready reader. A single replaced access cookie is insufficient: native auth accepts alternate access credentials and refresh fallback.                                                                                        | Require the actual denied action's HTTP 401 before UI/data invariants; cleanup is context-only. This tests late expiry on actions, not interruption of an accepted provider call or every active-poll timing race.                                                                                                                                                                        |
| Stale source after review                    | On a dedicated synthetic child with a completed questionnaire and ready report, open confirmation review. Through PATCH `/children/{id}`, change its synthetic `birth_date` to a different valid date, read correction back, then submit the old questionnaire with a fresh report key.                             | Expect generic private/no-store 404; no new generations/events/artifacts. Original accepted key must replay original generation/report. Existing report and parent stay unchanged. Snapshot equality starts after the intentional source correction; do not erase the new chart/history to conceal it.                                                                                    |
| Owned locked resource                        | Provision C's child during authorized active synthetic access, then expire only C's synthetic `child` grant. GET that exact owned child with C's valid token.                                                                                                                                                       | Expect 402 lock allowlist, not foreign 404. State snapshot starts after intentional expiry. Reuse the retained expired fixture; original A's access must remain active. Synthetic test payment rows are not external payments.                                                                                                                                                            |
| Controlled native disabled-provider terminal | Prefer retained failed generation `1ae31437-b121-4308-b6f4-2d9fb5c58eb4` in the approved owner registry. For a fresh fixture, an approved drained staging window may set `LLM_PROVIDER=mock,LLM_ENABLED=false`, recreate all four consumers using the pinned Compose function, and admit a fresh synthetic request. | Expect deterministic content plus `narrative_failed`, `child_narrative_disabled`, zero provider calls; this is a disabled-sentinel test, not a real upstream outage/cost test. Restore original settings in finally, recreate consumers, verify flags/readiness and a fresh native-mock ready generation. Do not perform this global setting transition during unapproved/shared traffic. |
| Stale age block                              | Use a retained previous-local-date report; verify the reader's stale-age notice. POST `/reports/{id}/age-updates` with the reader core version and a new stable key; confirm actual request schema in live internal OpenAPI before mutation.                                                                        | Poll returned generation to `age_update_ready`/`age_update_failed`, preserve core, pin PDF to resulting age snapshot. No server clock changes, invented birth time or edits of historic snapshots.                                                                                                                                                                                        |

### Isolated late-expiry recipe

`backend/app/dependencies.py` tries Bearer plus both access cookies, then accepts either refresh cookie directly when no valid access candidate remains. `backend/app/modules/auth/router.py` also accepts a refresh token in the refresh request body and sets login access/refresh cookies. Merely expiring one access cookie can therefore leave an authenticated request.

1. Use a fresh isolated synthetic browser context for each expiry scenario, never a normal operator/customer profile or imported normal-login storage state. Load the draft, confirmation review or ready reader using only the approved synthetic identity's bounded native access session; provide no refresh credential at setup. Keep the loaded page open, without reload or re-login.
2. Before the denied action, clear **all** access/refresh cookies across all domains and paths: `access_token`, `astrotype_token`, `refresh_token`, `astrotype_refresh_token` (including HttpOnly variants through browser-context cookie controls). Clear token-bearing `localStorage` and `sessionStorage`, in-memory auth-store/API-client tokens/default headers, context/page/request extra headers and any injected `Authorization: Bearer` credential. Remove any refresh request-body credential or background helper able to restore it. Gateway Basic Auth, if required, remains separate and must not inject a backend Bearer token. Keep no normal login/refresh fallback: if any valid candidate or refresh credential remains, stop and rebuild the isolated setup rather than accepting its result.
3. Install only one genuinely signed expired native access token as the context's `access_token` cookie for the target origin/path. The approved staging fixture operator issues it solely for that synthetic identity; do not change the JWT payload without signing, expose the signing key or use another user's session. Verify credential **names/presence only**, not values: the expired access cookie must be the sole backend credential on the outgoing action. Do not intercept/mock API responses, bypass native authentication or alter the server clock. Take the private persisted-state baseline after setup and before the action.
4. Attempt autosave, confirmation or age update respectively. Observe the action's actual HTTP 401 from the native backend before asserting sign-in link, preserved loaded read-only content, disabled writes and all 21 hashes unchanged. A refresh recovery, redirect/login page, locally blocked action, mock response or successful request is not an expiry pass; stop and investigate. Record only sanitized status/scenario and private invariant results, never request headers/bodies or response credentials.
5. Close only this browser context in finally and discard its private in-memory credentials; do not call logout, revoke/blacklist tokens, edit grants or clear another context's sessions. Never log tokens or save token-bearing storage state, HAR, traces, screenshots of credentials or console/network dumps.

Historical expiry probes used fresh contexts, not the normal login/refresh-cookie path. This recipe clarification is not a new execution or a claim of live acceptance.

For raw query-plan/provider accounting requirements use the named runtime code/tests and a separately approved read-only DB diagnostic, not ad-hoc `EXPLAIN ANALYZE` against customer data. Durable generation/section evidence lives in `child_generations`, `child_generation_events`, and `child_segment_generations`; inspect the actual persisted diagnostics/worker contract for provider accounting, rather than inventing provider-intent/attempt tables. The hash helper proves row equality, not a query-plan timing distribution, broker enqueue count, provider spend or literal zero-stuck observation window. Those claims require their separate recorded evidence.

## Acceptance record and gate matrix

Create `$PRIVATE_DIR/release-record.json` with operator/approver, approved target/window, workload/sample size/concurrency, exact UTC observation start/due/end, provider/model, thresholds and measured distributions. The following missing values are a STOP decision, not default acceptance:

- create/poll/deterministic-publication/narrative/PDF p95 limits;
- provider attempts/tokens/currency cost per report; queued/running age and reconciliation limits;
- terminal-failure rate, sample size/load and literal observation duration.

The existing generation 120-second and PDF 15-second functional deadlines, and the alert's worker p95 threshold, are not an approved complete performance budget. Do not invent an approver or call unmeasured values zero. With mock, record paid calls as prohibited/zero but leave real-provider token/cost/quality unqualified. Real-provider qualification needs a separate explicit spend cap and permission.

| Gate                                                                 | Current proof class                                                                                              | Closure authority                                                                          |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Native functional/browser/PDF/access/data safety/expiry/stale/replay | Mock-functional; recorded live outcomes on app `06b72c0`                                                         | Evidence review, not paid-model quality                                                    |
| Collector/rules/native Telegram firing+resolved                      | Deployed operational proof on infra `40f3fb1`                                                                    | Does not establish full budgets                                                            |
| Numeric budgets/workload/observation                                 | Full measured distributions and approved workload/window/budgets still missing                                   | Named approver must set limits before the next acceptance enable; measurements must follow |
| Real-provider cost/quality/unknown-outcome                           | One authorized real DeepSeek full generation on app `3e3ee67`; quality still limited, tokens/currency unrecorded | No more paid calls authorized; quality and accounting remain open                          |
| New-operator full execution                                          | Independent document review found prerequisites; full execution remains open                                     | Actual independent operator records commands/results; code/doc presence is insufficient    |
| Production/cohort canary/accepted marker                             | Global release authorized and deployed; latest app `3e3ee67`, independent runtime readback; not a cohort canary  | Release-specific owner budget exception is not full E22 acceptance                         |

Current production detail is in the [BUG-50 evidence record](../reviews/2026-10-28/BUG-50-child-content-quality.md). The new v3 artifact has 11 distinct bodies/35 distinct claims and four evidence-based omissions, no terminal failure, and eleven section calls with one attempt each. Standard caveat/uncertainty sentences still repeat 26/18 times: BUG-50 and E22 remain open. Historical v1/v2 artifacts and 109 prior rows were preserved. One sample cannot establish p95, a failure rate or unknown-outcome safety; currency/tokens are unrecorded, not zero. The paid budget is exhausted; this document authorizes no additional calls. The earlier diagnostic enable before the complete budget/alert prerequisite remains a historical gate violation. Later successful tests and the explicit global-release exception do not retroactively supply missing acceptance proof.
