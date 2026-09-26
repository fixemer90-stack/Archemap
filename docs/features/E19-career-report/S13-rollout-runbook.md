# S13: Career rollout / rollback runbook

## Статус

✅ Завершено — операторский runbook готов; stage-исполнение вынесено в S14, canary/production evidence остаются в S12

## Scope and safety invariant

Target Career uses only additive `career_*` tables plus `career_generations`. Legacy `reports.product='career'`, legacy PDFs, payments and entitlements are never backfilled, rewritten, truncated or deleted by this rollout.

Rollback means `CAREER_REPORT_ENABLED=false` and stopping new target writes. It does not mean downgrading destructive schema or deleting already committed target artifacts.

## Initial budgets

| Signal                    |                   Canary budget | Action                                                    |
| ------------------------- | ------------------------------: | --------------------------------------------------------- |
| deterministic stage p95   |                           ≤ 5 s | stop canary if exceeded for 15 min                        |
| full narrative p95        |                         ≤ 180 s | inspect provider latency and section failures             |
| one narrative section p95 |                          ≤ 30 s | retry only failed section                                 |
| stuck generation          | no active job older than 20 min | page operator immediately                                 |
| validator failures        |                   < 5 in 15 min | pause canary and inspect outputs without logging payloads |
| estimated provider cost   |  ≤ USD 0.20 per complete report | pause expansion and correct configured rates/model        |

Set current provider rates in `CAREER_LLM_INPUT_COST_PER_MILLION` and `CAREER_LLM_OUTPUT_COST_PER_MILLION`. Token and cost values are conservative character-based estimates until the provider boundary returns an authoritative usage object; do not use them for invoice reconciliation.

## Metrics and alerts

Configure `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` and `OTEL_SERVICE_NAME`. The API exports:

- `career_operations_total` — bounded `stage`, `outcome`, `operation`, optional safe `error_code`, section and version labels;
- `career_operation_duration_seconds` — deterministic/narrative latency;
- `career_provider_tokens_total` — aggregate input/output token estimate, no payload or identity labels;
- `career_provider_cost_usd` — aggregate configured-rate cost estimate.

Celery beat runs `career.monitor_pipeline` every 5 minutes. It warns with `career_pipeline_alert` for:

- any `queued|calculating_dimensions|deterministic_ready|generating_sections` generation older than `CAREER_STUCK_AFTER_MINUTES`;
- at least `CAREER_VALIDATOR_ALERT_THRESHOLD` `career_validation_failure` segments in `CAREER_MONITOR_WINDOW_MINUTES`.

Questionnaire telemetry records only `draft_saved` / `completed`; answers, free text, user IDs and report payloads are not metric labels.

## Pre-migration evidence

Run against the exact target database before `alembic upgrade head`:

```bash
set -eu
export BACKUP="career-preflight-$(date -u +%Y%m%dT%H%M%SZ).dump"
pg_dump "$DATABASE_URL" --format=custom --file="$BACKUP"
pg_restore --list "$BACKUP" >/dev/null
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
BEGIN TRANSACTION READ ONLY;
SELECT 'person_profiles', count(*), md5(coalesce(string_agg(id::text, ',' ORDER BY id), '')) FROM person_profiles;
SELECT 'reports', count(*), md5(coalesce(string_agg(id::text, ',' ORDER BY id), '')) FROM reports;
SELECT 'payments', count(*), md5(coalesce(string_agg(id::text, ',' ORDER BY id), '')) FROM payments;
SELECT 'entitlements', count(*), md5(coalesce(string_agg(id::text, ',' ORDER BY id), '')) FROM entitlements;
COMMIT;
SQL
```

Store the backup path, row counts and checksums in the deployment evidence. If a table name differs in the target schema, resolve it before migration; do not omit the dataset silently.

## Migration and staging

1. Deploy code with `CAREER_REPORT_ENABLED=false`.
2. Run `alembic upgrade head`.
3. Repeat the four legacy row-count/checksum queries; every value must match preflight.
4. Verify Career migrations are additive and no automatic legacy backfill ran.
5. Set OTLP endpoint and current provider rate settings.
6. Enable the feature only on staging.
7. Run the mock-provider flow, then the real-provider flow.

Staging matrix:

- active Plus: questionnaire → deterministic report → all narrative sections → reader → PDF;
- grandfathered legacy Career: same target flow remains allowed and old legacy reader/PDF still opens;
- locked/expired: create, status, read, sections, regenerate and PDF return no protected payload;
- provider failure: deterministic content remains readable, failed section has a safe code, isolated retry succeeds;
- feature flag off: target routes stop new work while existing target and legacy artifacts remain in storage.

Human review the real-provider report against `../../design/astrotype_career_report.md` and `../../design/astrotype-career-report-sample.html`: specificity, contradiction retention, conditional low-confidence wording, no diagnosis, no guaranteed outcomes, no prescribed profession and no duplicate sections.

## Canary

1. Record the deployed Git SHA and CI run URL.
2. Enable a small controlled cohort at the edge/config layer while keeping `CAREER_REPORT_ENABLED=true` only in that deployment.
3. Compare completion, latency, validator failure, stuck count and estimated cost against the budgets above.
4. Expand only after a full observation window with zero stuck generations and no access leak.
5. Keep the legacy route readable during the migration window; disable legacy generation only after access/history evidence is signed off.

## Rollback

1. Set `CAREER_REPORT_ENABLED=false` and redeploy/restart API and worker.
2. Stop new Career enqueue at the target UI/edge.
3. Let active jobs finish or mark them retryable; do not delete their rows.
4. Keep target report reads available only if the access policy and rollback decision explicitly allow them; keep all legacy reads/PDFs unchanged.
5. Re-run the legacy row-count/checksum queries and verify target `career_*` rows still exist.
6. Record incident window, Git SHA, counts and the reason for rollback.

Never run `alembic downgrade`, `DROP`, `TRUNCATE`, mutable legacy backfill or cleanup of generated reports as an emergency rollback.

## Evidence required before S12 can become complete

Stage-публикация и сбор первых семи блоков evidence выполняются по [`S14-stage-publication-live-evidence.md`](S14-stage-publication-live-evidence.md). Production smoke остаётся отдельным финальным gate S12.

- green exact CI SHA;
- staging mock and real-provider report IDs;
- human quality review result;
- active Plus / grandfathered / locked matrix results;
- pre/post legacy row counts and checksums plus tested backup restore;
- latency/token/cost dashboard links and a zero-stuck observation window;
- rollback flag rehearsal result;
- production smoke report/PDF IDs with secrets and personal payload redacted.
