# V2-E13 S04: Write packaging plan

## Status

✅ Завершено

## Context

This story belongs to `V2-E13 — Desktop thin client decision`.

Document installer, signing, updates, logs and support boundaries if desktop is pursued.

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

| Path                                                     | Action                                                        |
| -------------------------------------------------------- | ------------------------------------------------------------- |
| `backend/app/modules/astrotype_v2/`                      | Add/update v2 backend module code when implementation starts. |
| `docs/features/E16-v2-e13-desktop-thin-client-decision/` | Keep feature/story docs synchronized.                         |
| `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`            | Update if functional/API/data contract changes.               |

## Acceptance criteria

- [x] Scope is implemented without crossing into unrelated v2 epics.
- [x] v2 remains natal-only and does not depend on socionics/Model A/function strengths.
- [x] Behavior is backed by tests or documented verification evidence.
- [x] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Decision recorded: packaging is follow-on only, with signing/update/log/support prerequisites before public distribution.

Decision artifact: `docs/architecture/astrotype-v2-desktop-thin-client-decision.md`

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_desktop_thin_client_decision.py::test_desktop_shell_is_thin_client_over_same_v2_api_and_report_ids tests/unit/test_astrotype_v2/test_desktop_thin_client_decision.py::test_tauri_electron_spike_selects_tauri_first_with_electron_fallback -v --tb=short
```
