# Astrotype v2 Desktop Thin Client Decision

## Status

Accepted for Astrotype v2 planning.

## Decision

Decision: do not require a Windows `.exe` for Astrotype v2 core launch.

Desktop is optional, not a prerequisite. The launch path remains:

```text
web-first responsive reader
→ PWA readiness
→ Android/PWA/Capacitor path remains ahead of desktop packaging
→ optional desktop shell only if demand justifies it
```

The desktop product decision is therefore:

1. Ship the v2 core through backend API + reusable responsive web reader first.
2. Do not delay v2 core launch for installer, signing, auto-update or native shell work.
3. If a Windows app is built, it is a thin shell over the existing Astrotype v2 API and persisted report artifacts.
4. Do not build a desktop-local report runtime or canonical local database for the main v2 product.

## Rationale

Astrotype v2 already has the cloud-core shape required for web, Android and possible desktop clients:

- canonical chart/fact/report storage lives in backend PostgreSQL;
- report generation can continue while the client is closed;
- LLM prompts, API keys, retry policy and cost observability stay server-side;
- web, Android and desktop can all read the same persisted report;
- the Android/PWA/Capacitor path remains ahead of desktop packaging because Android is a product roadmap target, while a Windows `.exe` is optional.

A desktop-local-first `.exe` would create duplicate report storage, synchronization problems, entitlement drift, separate update/migration problems and a slower Android path.

## Product decision

| Question                                                        | Decision                                              |
| --------------------------------------------------------------- | ----------------------------------------------------- |
| Is `.exe` required for v2 core launch?                          | No.                                                   |
| Does desktop block Android/PWA work?                            | No.                                                   |
| Should desktop own chart/report generation?                     | No. Backend remains the canonical generator.          |
| Should desktop have a local report database as source of truth? | No local DB is source of truth.                       |
| Can desktop cache generated reports?                            | Yes, cache is disposable.                             |
| Can desktop store draft profile input?                          | Yes, drafts may be local until submitted.             |
| Can desktop contain production LLM credentials?                 | No production LLM key is embedded in the desktop app. |
| Preferred shell if built?                                       | Tauri-first, Electron fallback.                       |

## Thin-client contract

A desktop shell, if built, must use:

- same backend API;
- same account identity;
- same report ids;
- same entitlement checks;
- same status/progress model;
- same deterministic infographic data;
- same final report payloads.

Required v2 API surface for the shell:

```text
POST /api/v1/astrotype-v2/reports
GET /api/v1/astrotype-v2/reports/generations/{generation_id}
GET /api/v1/astrotype-v2/reports/{report_id}
GET /api/v1/astrotype-v2/reports/{report_id}/progress
GET /api/v1/astrotype-v2/reports/{report_id}/facts
GET /api/v1/astrotype-v2/reports/{report_id}/infographic
GET /api/v1/astrotype-v2/reports/{report_id}/segments
POST /api/v1/astrotype-v2/reports/{report_id}/regenerate
```

Desktop must not introduce compatibility aliases or alternate desktop-only report identifiers. A report opened on desktop must be the same report opened on web or Android.

## Cache contract

PostgreSQL remains canonical.

SQLite is allowed only for cache/drafts, not canonical report state. The desktop client may store:

- cached report JSON for offline reading;
- cached deterministic infographic payloads;
- cached facts/evidence payloads;
- UI preferences;
- non-submitted draft birth/profile input;
- download/export metadata.

The desktop client must not store as canonical source of truth:

- generated report rows;
- LLM segment artifacts;
- final assembled report versions;
- entitlement state;
- billing/subscription state;
- permanent user profile state;
- production LLM prompts or provider keys.

The cache is disposable. Clearing the desktop cache must not delete or corrupt canonical report data. Reinstalling the desktop app must allow the user to log in and reload reports from the backend.

## Offline behavior

Supported:

- read cached reports;
- view cached infographics;
- view cached facts/evidence;
- edit draft profile input before submission;
- queue a generation request locally until network returns.

Out of scope for v2 desktop MVP:

- full offline generation is out of scope;
- full chart calculation offline;
- offline LLM report generation;
- desktop-only report history;
- local-first sync/merge conflict handling.

## Tauri vs Electron spike outcome

Recommendation: Tauri-first.

Reason:

- smaller installer/runtime footprint;
- good fit for a webview wrapper around the existing frontend;
- adequate for PDF/export/share helpers;
- Rust shell can stay thin and avoid duplicating product logic;
- better default posture for a lightweight optional desktop client.

Electron fallback is acceptable if the team later needs:

- faster JS-only desktop iteration;
- richer ecosystem for auto-update/signing helpers;
- mature desktop debugging tools;
- less Rust maintenance burden.

Spike constraints for either shell:

- frontend reuse is mandatory;
- auth/session storage must use platform-secure storage where available;
- auto-update/signing must be planned before public distribution;
- no production LLM key may be packaged;
- no backend source-of-truth logic may be copied into the shell.

## Packaging plan if desktop is pursued

Desktop packaging is a follow-on task, not a v2 core-launch blocker.

Required before public `.exe` distribution:

1. Choose shell: Tauri-first unless a short spike proves Electron materially cheaper.
2. Define update channel: internal, beta, stable.
3. Define signing strategy for Windows installer.
4. Add crash/log collection boundaries that do not leak birth data or report prose by default.
5. Verify login/logout/session refresh in desktop shell.
6. Verify report read/progress/infographic/regenerate against the same backend API.
7. Verify cache deletion/reinstall does not remove backend reports.
8. Document support boundaries: desktop shell issues vs backend account/report issues.

## Consequences

- V2-E13 is a decision and contract slice, not a new runtime implementation epic.
- No desktop project scaffold is required now.
- No package dependency on Tauri or Electron is required now.
- No local desktop database migration is required now.
- V2-E14 QA/smoke can continue against backend + web/PWA path.
- A later desktop implementation must prove it conforms to this document before adding shell-specific source-of-truth behavior.

## Links

- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/ROADMAP-v2.md`
- `docs/features/E16-v2-e13-desktop-thin-client-decision/FEATURE.md`
