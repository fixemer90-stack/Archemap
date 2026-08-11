# V2-E9 S03: Expose infographic API contract

## Status

✅ Завершено

## Context

This story belongs to `V2-E9 — Infographics & factual basis`.

Return deterministic infographic JSON for web/mobile clients.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`

## What to do

1. Read the related architecture and roadmap documents.
2. Inspect existing code/docs relevant to this boundary before implementation.
3. Implement only the scope of this story.
4. Add or update tests/documentation for the changed contract.
5. Verify with targeted commands and record the evidence in this story when work starts.

## Files likely affected

| Path                                                  | Action                                                        |
| ----------------------------------------------------- | ------------------------------------------------------------- |
| `backend/app/modules/astrotype_v2/`                   | Add/update v2 backend module code when implementation starts. |
| `docs/features/E16-v2-e9-infographics-factual-basis/` | Keep feature/story docs synchronized.                         |
| `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`         | Update if functional/API/data contract changes.               |

## Acceptance criteria

- [x] Scope is implemented without crossing into unrelated v2 epics.
- [x] v2 remains natal-only and does not depend on socionics/Model A/function strengths.
- [x] Behavior is backed by tests or documented verification evidence.
- [x] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_infographic_data.py::test_build_infographic_api_payload_v2_is_client_reusable_and_llm_free -v --tb=short
```
