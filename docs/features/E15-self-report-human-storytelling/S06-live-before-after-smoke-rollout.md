# S06 — Live Before/After Smoke and Rollout

Статус: ⬜ Не начато
Эпик: `E15-self-report-human-storytelling`

## Контекст

The problem was found on a real local report. E15 should not close from unit tests only: it needs a real before/after smoke on the reference profile/report and a rollout policy for existing narratives.

## Reference report

- Profile URL: `/report/877508cc-3e32-4fab-ab64-a939afc01fac`
- Current local report id observed during intake: `b157a22d-70a4-4301-9e6e-bd72816e5f3e`
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

- [ ] Reference report regenerates to `report.status=ready` and `narrative.status=ready`.
- [ ] Worker logs show narrative success without fallback.
- [ ] Web first screen is recognition-first and does not start with raw technical facts.
- [ ] PDF endpoint returns `200` and contains the humanized narrative.
- [ ] Before/after notes are recorded in this story or a linked implementation note.
- [ ] Rollout avoids destructive DB/content deletion.

## Verification

```bash
docker compose ps
curl http://localhost:8000/api/v1/health
# authenticate locally
# POST /api/v1/reports/{report_id}/narrative/regenerate
# poll GET /api/v1/reports/{report_id}
# POST or GET PDF route according to current API contract
```
