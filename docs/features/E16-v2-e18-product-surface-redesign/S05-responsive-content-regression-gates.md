# S05: Add responsive/content regression gates

## Status

⬜ Не начато

## Context

After redesigning homepage, dashboard and billing, the repo needs lightweight checks that prevent regressions back to old language and old layout markers.

This story is not a replacement for manual visual review, but it should catch obvious drift in CI/local checks.

## What to do

1. Add a targeted frontend script:
   - recommended path: `frontend/scripts/check-product-surface-redesign.mjs`.
2. The script should inspect source files and/or built DOM snapshots if the project already has a pattern for that.
3. Cover at minimum:
   - homepage route source;
   - dashboard route source;
   - billing route source.
4. Check required markers:
   - homepage has new hero promise and registration CTA;
   - dashboard has personal workspace/latest-report/empty-state markers;
   - billing has YooKassa confirmation/trust markers.
5. Check forbidden user-facing terms:
   - `Model A`
   - `MBTI`
   - `function_strengths`
   - `socionics`
   - `Соционика`
   - `v2/json`
   - raw `evidence ids`
   - old `архетип` wording in homepage/billing/dashboard public copy.
6. Add npm script if this repo convention supports it, or document the direct command in this feature doc.
7. Run the script with lint/format/typecheck.

## Files likely affected

| Path                                                           | Action                                                         |
| -------------------------------------------------------------- | -------------------------------------------------------------- |
| `frontend/scripts/check-product-surface-redesign.mjs`          | Create                                                         |
| `frontend/package.json`                                        | Add script only if consistent with existing script conventions |
| `docs/features/E16-v2-e18-product-surface-redesign/FEATURE.md` | Update verification command if script name changes             |

## Acceptance criteria

- [ ] Regression script fails when required page markers are missing.
- [ ] Regression script fails when forbidden legacy/technical terms appear in user-facing page source.
- [ ] Script covers `/`, `/dashboard`, and `/billing` source paths.
- [ ] Script is runnable locally with a single documented command.
- [ ] Frontend lint, format and TypeScript checks pass.
- [ ] Manual visual smoke is documented for mobile/tablet/desktop widths.

## Verification

```bash
cd frontend
node scripts/check-product-surface-redesign.mjs
npx eslint .
npx prettier --check .
npx tsc --noEmit
npm test
```

Manual visual widths when browser is available:

- 390px
- 768px
- 1440px
- 1920px
