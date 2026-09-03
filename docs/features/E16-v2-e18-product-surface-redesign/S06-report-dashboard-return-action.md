# S06: Add report-to-dashboard return action

## Status

✅ Реализовано

## Context

The v2 report route is rendered as a standalone reading surface. This is intentional: the report should feel like a focused document, not like a dashboard subpage. However, the user still needs an obvious way to return from `/report/v2/[profileId]` to `/dashboard` without relying on browser back history or manually editing the URL.

The current dashboard layout already treats `/report/v2/*` as standalone and hides the normal dashboard sidebar/header. This story adds a minimal, report-style return control inside the report surface itself.

## Routes in scope

- `frontend/src/app/(dashboard)/report/v2/[profileId]/page.tsx`
- `frontend/src/components/astrotype-v2/report/V2ReportReader.tsx`

Legacy report routes may be handled separately if still user-facing, but this story targets the current v2 report reader first.

## User story

As a user reading my Astrotype report, I want a visible button back to my dashboard so I can return to my reports/account area after reading or downloading the report.

## Requirements

- Add a visible link/button to `/dashboard` on the v2 report page.
- The control must be present on the ready report state.
- The control should also be present on loading/error/progress states before the report is ready.
- The control must use normal Next.js navigation (`Link href="/dashboard"`) rather than browser-history back behavior.
- The label should be user-facing Russian copy, for example `В кабинет` or `Вернуться в кабинет`.
- The control should visually match the report surface: subtle outline/ghost treatment, rounded shape, no generic admin/header look.
- The control must not reintroduce the dashboard sidebar/header into the standalone report reader.
- The control must not alter report generation, polling, PDF download, or report view-model logic.

## UX notes

- Preferred placement: above the report hero, aligned with the report content width.
- The button should be easy to notice but secondary to the report itself.
- Do not use `Назад` if it implies browser history. The destination is specifically `/dashboard`.
- The route text can say `В кабинет`, because dashboard is the user's personal Astrotype workspace.

## Acceptance criteria

- [x] `/report/v2/[profileId]` ready state contains a link/button with `href="/dashboard"`.
- [x] Loading/error/progress state for `/report/v2/[profileId]` contains the same return action.
- [x] The report route remains standalone: no dashboard sidebar/header is added for `/report/v2/*`.
- [x] PDF download button still works from the report hero.
- [x] Report polling/generation state still renders while waiting for the report.
- [x] The return-action copy is Russian and does not expose internal route jargon.
- [x] Targeted report reader DOM regression check covers the return action.
- [x] Frontend lint/typecheck pass for the changed files.

## Suggested implementation

1. Add `Link` from `next/link` and the shared `Button` component where the return action is rendered.
2. In `V2ReportReader`, render a compact top row before `V2ReportHero`:
   - `Button variant="outline" asChild`
   - `Link href="/dashboard"`
   - label `В кабинет`
3. In `AstrotypeV2ReportPage`, render the same return action in the non-ready card state.
4. Extend `frontend/scripts/check-v2-report-reader-dom.mjs` to assert:
   - `href="/dashboard"`
   - Russian label exists
   - no sidebar/header marker is required for the standalone route
5. Run exact-path verification.

## Verification commands

```bash
cd frontend
node scripts/check-v2-report-reader-dom.mjs
npx eslint src/app/\(dashboard\)/report/v2/[profileId]/page.tsx src/components/astrotype-v2/report/V2ReportReader.tsx scripts/check-v2-report-reader-dom.mjs
npx prettier --check src/app/\(dashboard\)/report/v2/[profileId]/page.tsx src/components/astrotype-v2/report/V2ReportReader.tsx scripts/check-v2-report-reader-dom.mjs
npx tsc --noEmit --pretty false
```

Optional runtime smoke when the local frontend/backend are available:

```bash
cd frontend
npm run dev
# open /report/v2/<profileId>, confirm the button navigates to /dashboard
```

## Implementation evidence

Implemented and verified with:

```bash
cd frontend
npm test
npx eslint .
npx prettier --check .
npx tsc --noEmit --pretty false
npm run build
```

Result: all commands passed; Next production build completed successfully.
