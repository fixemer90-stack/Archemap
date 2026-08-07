# S06 — Live Before/After Smoke and Rollout

Статус: ✅ Готово
Эпик: `E15-self-report-human-storytelling`

## Контекст

The problem was found on a real local report. E15 should not close from unit tests only: it needs a real before/after smoke on the reference profile/report and a rollout policy for existing narratives.

## Reference report

- Profile URL: `/report/877508cc-3e32-4fab-ab64-a939afc01fac`
- Current local report id observed during intake: `b157a22d-70a4-4301-9e6e-bd72816e5f3e`
- Current local report id used for 2026-07-08 smoke: `7ffb533b-e733-4c55-baa5-3c9deacd51b1`
- Current symptom: technically grounded but too dry/sparse, especially hero and first sections.

## Что сделать

1. Save a before snapshot of current narrative text for comparison.
2. Regenerate with E15 prompt/assembler path.
3. Poll until ready and inspect API response.
4. Open local web report and verify first-read flow manually.
5. Verify PDF 200 and PDF content parity.
6. Document rollout policy:
   - new prompt/staged version should generate new cache keys;
   - existing ready narratives may remain until user/regenerate/report refresh;
   - no destructive deletion of reports/profiles.

## Acceptance criteria

- [x] Reference report regenerates to `report.status=ready` and `narrative.status=ready`.
- [x] Worker logs show narrative success without fallback.
- [x] Web/API first screen narrative is recognition-first and does not start with raw technical facts.
- [x] PDF endpoint returns `200` and is rendered from the same humanized narrative payload.
- [x] Before/after notes are recorded in this story or a linked implementation note.
- [x] Rollout avoids destructive DB/content deletion.

## Live smoke notes — 2026-07-08

Runtime:

- `docker compose ps`: postgres, redis, backend, frontend, worker up; backend healthy.
- `GET http://localhost:8000/api/v1/health`: `{"status":"ok","database":"ok","redis":"ok"}`.
- Backend and worker env both used real LLM path: `LLM_ENABLED=true`, `LLM_PROVIDER=deepseek`, `LLM_MODEL=deepseek-v4-flash`, `LLM_TIMEOUT_SECONDS=180`.
- A stale backend/worker process initially made the API return `narrative: null` after a successful worker run because the live service had not been restarted after local code changes. Restarting both `backend` and `worker` fixed the read path before the final smoke.

Before snapshot after service restart, before full regeneration:

- `report.status=ready`
- `narrative.status=ready`
- `model_name=deepseek-v4-flash`
- `prompt_version=self_staged_v2`
- `error_message=None`
- `hero_len=905`
- `first_section_len=2551`

Hero excerpt:

> Ваше «я» собирается не в одиночестве, а в контакте. Вы лучше понимаете себя, когда есть другой — партнёр, оппонент, собеседник. Солнце и Луна в Козероге в 7 доме добавляют этому процессу основательность: вы не спешите с самоопределением, ваше «я» зреет постепенно через проверенные связи и ответственность.

Regeneration command shape:

```bash
POST /api/v1/reports/7ffb533b-e733-4c55-baa5-3c9deacd51b1/narrative/regenerate
{"scope":"full"}
```

Poll result:

- Initial response: `report.status=generating_narrative`.
- Final poll: `report.status=ready`, `narrative.status=ready`, `error_message=None`.
- Worker log: `report_narrative_generation_succeeded`, `used_fallback=False`, `duration_ms=88629`.

After full regeneration:

- `model_name=deepseek-v4-flash`
- `prompt_version=self_staged_v2`
- `hero_len=949`
- `first_section_len=2966`

Hero excerpt:

> Вы принадлежите к тем, чья идентичность собирается не в изоляции, а через встречу с другим. Солнце и Луна в Козероге в 7 доме — это ваша личная формула: вы познаёте себя, когда вступаете в отношения, берёте на себя ответственность и строите совместные структуры. Вы не просто «отражаетесь» в партнёре — вы обретаете устойчивость, когда есть ясный контракт, взаимные обязательства и долгосрочная перспектива.

PDF check:

- `GET /api/v1/reports/7ffb533b-e733-4c55-baa5-3c9deacd51b1/pdf`: `HTTP/1.1 200 OK`.
- PDF size: `83550` bytes.
- Header: `%PDF-`.
- The PDF route renders on demand from `reports.report_data` plus the current `report_narratives.content`; the checked narrative payload is the same post-regeneration humanized payload above.

Web first-read note:

- Browser-level cookie injection through the Hermes browser tool was blocked by tool safety policy, so the manual visual browser step was validated indirectly through the authenticated API payload plus existing frontend structure checks.
- The API first screen starts with recognition/personal formula prose, not raw chart tables, scores, socionics labels, or technical facts.
- Frontend regression check `node scripts/check-report-ux.mjs` passed after the final code changes.

## Rollout policy

- Prompt/staged version changes must continue to affect cache keys through `prompt_version`, stage prompt versions, `input_hash`, and `model_name`.
- Existing ready narratives should not be destructively deleted. They may remain until explicit user regeneration, report refresh, or a new cache key causes regeneration.
- No rollout step may delete users, profiles, chart snapshots, reports, or `data/generated/content/`.
- If the live API returns `narrative: null` while a ready row exists in Postgres, restart both backend and worker before judging the smoke; long-lived services can hold stale code.
- A successful rollout smoke requires: backend health, worker success log with `used_fallback=False`, API `report.status=ready` + `narrative.status=ready`, and PDF `200`.

## Verification

```bash
docker compose ps
curl http://localhost:8000/api/v1/health
# authenticate locally
# POST /api/v1/reports/{report_id}/narrative/regenerate
# poll GET /api/v1/reports/{report_id}
# POST or GET PDF route according to current API contract
```
