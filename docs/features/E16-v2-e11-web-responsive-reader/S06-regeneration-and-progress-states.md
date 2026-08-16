# S06: Regeneration and progress states

## Status

⬜ Не начато

## Context

Regenerate/polling behavior must be a clear state machine, not ad-hoc self-calling callbacks.

## What to do

1. Extract report generation state into a dedicated hook.
2. Model queued, polling, loading report, ready, failed, and regenerating states explicitly.
3. Keep regenerate available from ready state.
4. Prevent infinite polling and duplicate force submissions.

## Files affected

| Action | Path                                                          |
| ------ | ------------------------------------------------------------- |
| Modify | `frontend/src/app/(dashboard)/report/v2/[profileId]/page.tsx` |
| Create | `frontend/src/lib/astrotype-v2/use-v2-report-generation.ts`   |
| Modify | `frontend/src/lib/api/astrotype-v2.ts`                        |

## Acceptance criteria

- [ ] Ready report can be regenerated.
- [ ] Queued report eventually resolves to latest report_id.
- [ ] Errors are recoverable.
- [ ] No hook lint violations.

## Verification

```bash
cd frontend && npx eslint src/app/\(dashboard\)/report/v2/\[profileId\]/page.tsx src/lib/astrotype-v2 && npx prettier --check src/app/\(dashboard\)/report/v2/\[profileId\]/page.tsx src/lib/astrotype-v2 && npx tsc --noEmit
```
