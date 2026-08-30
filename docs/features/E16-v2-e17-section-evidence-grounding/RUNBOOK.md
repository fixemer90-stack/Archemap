# E16-v2-E17 production smoke and retry runbook

## Safety rules

- Do not delete `data/generated/content/` or truncate production tables.
- Do not run broad cleanup commands against v2 generated artifacts.
- Retry by enqueueing a new generation with `force=true`; keep old rows for comparison unless a separate data-retention task approves archival.
- Never paste `.env.production`, API keys, passwords, or full auth tokens into logs or tickets.

## Service health

Run from the VPS in `/opt/astrotype`:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T postgres pg_isready -U astrotype -d astrotype
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T redis redis-cli ping
docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=80 worker | grep -E "ready|astrotype_v2_generation|succeeded|failed" || true
curl -fsS https://astrotype.ru/api/v1/health
```

Expected:

- backend is healthy;
- postgres is accepting connections;
- redis returns `PONG`;
- worker log includes Celery `ready` or recent task events;
- public health endpoint returns JSON with `status`, `database`, and `redis` all `ok`.

## Start a generation

Preferred user/API path: start from the authenticated frontend regeneration action, then copy `generation_id` from the API response.

Operator path from the worker container, when API credentials are not available:

```bash
GENERATION_ID=$(python - <<'PY'
import uuid
print(uuid.uuid4())
PY
)
PROFILE_ID='<person_profiles.id>'
USER_ID='<users.id>'

docker exec astrotype-worker-1 python - <<PY
from workers.tasks.astrotype_v2 import generate_natal_report_v2
r = generate_natal_report_v2.delay(
    profile_id='$PROFILE_ID',
    user_id='$USER_ID',
    generation_id='$GENERATION_ID',
    force=True,
)
print('GENERATION_ID=$GENERATION_ID')
print('CELERY_TASK_ID=' + r.id)
PY
```

When using the operator path directly, create or verify the generation status row through the API path when possible. Direct worker enqueues are reserved for incident response and still leave the final report traceable by `astrotype_v2_natal_reports.generation_id`.

## Poll generation status by id

Authenticated API path:

```bash
curl -fsS \
  -H "Authorization: Bearer <token>" \
  "https://astrotype.ru/api/v1/astrotype-v2/reports/generations/$GENERATION_ID"
```

Expected response fields:

- `generation_id` equals the id from the enqueue response;
- `status` is `queued`, `running`, `narrative_generating`, `partial`, `complete`, `narrative_failed`, `failed`, or `already_exists`;
- `report_id` appears once the deterministic report row is created;
- `sections[]` lists each section with `grounding_status`, evidence counts, `segment_status`, provider/model, and error text when relevant.

## Database diagnostics

Generation row:

```bash
docker exec astrotype-postgres-1 psql -U astrotype -d astrotype -x -c "
SELECT generation_id, celery_task_id, user_id, profile_id, report_id, status, diagnostics, created_at, updated_at
FROM astrotype_v2_natal_report_generations
WHERE generation_id = '$GENERATION_ID';"
```

Report row:

```bash
docker exec astrotype-postgres-1 psql -U astrotype -d astrotype -x -c "
SELECT id, generation_id, chart_id, status, version, created_at, updated_at
FROM astrotype_v2_natal_reports
WHERE generation_id = '$GENERATION_ID'
ORDER BY created_at DESC;"
```

Section diagnostics:

```bash
docker exec astrotype-postgres-1 psql -U astrotype -d astrotype -x -c "
WITH report AS (
  SELECT chart_id FROM astrotype_v2_natal_reports WHERE generation_id = '$GENERATION_ID' ORDER BY created_at DESC LIMIT 1
), outline AS (
  SELECT id FROM astrotype_v2_report_outlines WHERE chart_id = (SELECT chart_id FROM report) ORDER BY created_at DESC LIMIT 1
)
SELECT
  section_key,
  status,
  provider,
  model,
  error,
  jsonb_array_length(COALESCE(payload->'response'->'evidence_ids', '[]'::jsonb)) AS evidence_count,
  payload->'error' AS error_payload
FROM astrotype_v2_report_segment_generations
WHERE outline_id = (SELECT id FROM outline)
ORDER BY section_key;"
```

Smoke passes when every `ready` segment has `evidence_count > 0`. A `partial` report is acceptable only when failed/skipped sections are represented explicitly and the failure is visible in `sections[]`, segment rows, and worker logs.

## Worker log correlation

```bash
docker logs astrotype-worker-1 --since 2h | grep "$GENERATION_ID" || true
docker logs astrotype-worker-1 --since 2h | grep "$CELERY_TASK_ID" || true
```

The worker emits searchable events:

- `astrotype_v2_generation_started`
- `astrotype_v2_generation_reused_existing_report`
- `astrotype_v2_generation_reused_existing_report_after_wait`
- `astrotype_v2_generation_finished`
- `astrotype_v2_generation_narrative_failed`
- `astrotype_v2_generation_failed`

## Retry failed old generations

1. Resolve the profile/user pair from the failed report or profile URL.
2. Check latest report status and segment diagnostics first; do not delete rows.
3. Trigger regeneration with `force=true` from the frontend/API. If API auth is unavailable during an incident, use the worker operator path above with a new `GENERATION_ID`.
4. Poll generation status by the new id.
5. Confirm `ready` segment evidence counts are non-empty.
6. Compare the new report row with the old failed row before any cleanup/archive decision.

Useful lookup:

```bash
docker exec astrotype-postgres-1 psql -U astrotype -d astrotype -x -c "
SELECT p.id AS profile_id, p.user_id, r.id AS report_id, r.generation_id, r.status, r.created_at
FROM person_profiles p
LEFT JOIN astrotype_v2_natal_charts c ON c.profile_id = p.id
LEFT JOIN astrotype_v2_natal_reports r ON r.chart_id = c.id
WHERE p.id = '<person_profiles.id>'
ORDER BY r.created_at DESC NULLS LAST
LIMIT 10;"
```

## Disable/rollback switch

If real-provider failures spike:

1. Set `LLM_ENABLED=false` in production env or deploy a hotfix that disables real-provider segment generation.
2. Rebuild/restart backend and worker:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml build backend worker
docker compose --env-file .env.production -f docker-compose.prod.yml up -d backend worker
```

3. Confirm health, worker readiness, and that deterministic-first reports still produce visible content.
4. Keep failed generation rows and logs for diagnosis.

## Verification record

Fill this section after each production smoke.

```text
Date/time UTC:
Commit:
Profile id:
Generation id:
Celery task id:
Report id:
Final status:
Health result:
Ready section evidence counts:
Worker log correlation:
Notes:
```
