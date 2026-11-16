# Report mobile width repair — 2026-11-17

Status: deployed and verified. Exact-head CI passed all eight jobs; the native existing report passed document/inner-scroll geometry and data preservation at all five widths. The mobile overflow finding is closed.

## Cause and bounded fix

The calculation layer uses grid children with automatic minimum widths. The planet table deliberately retains a readable minimum width of 760px inside an `overflow-x-auto` wrapper, but its grid child's intrinsic minimum expanded the entire document. The original native 390px viewport produced `scrollWidth=814`.

The production delta adds `min-w-0` to the four existing calculation-grid children, permitting the cards to shrink within the available track. The table retains its minimum width and its own horizontal scroller. There is no global overflow hiding, typography redesign, column removal, data mutation, narrative regeneration or backend change. Classical planet ordering is unchanged.

## TDD and local verification

- Before production edits, the new browser regression failed at 390px: document overflow was 424px, reproducing 814px document width against a 390px viewport.
- After the four minimum-width constraints, all 10 focused browser cases passed: 360/390/768/1024/1440px, in both desktop and mobile browser projects.
- Cases assert document containment, all 14 bodies in classical order, unchanged synthetic Sun/Pluto degree associations, table width at least 760px, real inner scroll movement, rightmost-column visibility and zero document horizontal scroll. They do not replace overflowing data with hidden/clipped content.
- Existing visual matrix passed all six desktop/tablet/mobile light/dark cases without changing snapshots or tolerances.
- Full npm contract/behavior chain, changed-path ESLint/Prettier and full TypeScript no-emit check passed.
- Independent read-only SPEC/code/security review passed. It confirmed that removing exactly four `min-w-0` tokens reproduces the base component byte-for-byte; it did not independently rerun the parent's browser suites. The reviewer’s optional scroller-bounds hardening is included in the private native verifier; reviewed production/test files were not changed afterward.

## Release binding

- Code: `789d7b77fab675f8aead9ea3cafd356fb01d82a7`.
- Exact source tree: `fec2a9a1a5476637e5095fb0f24fb838c12cc523`.
- Candidate was archived with a temporary alternate Git index; the committed tree was asserted identical. The uploaded archive checksum was verified, and private env/Caddy files were preserved.
- Candidate frontend tag: `astrotype-frontend:tree-fec2a9a1a547`; actual VPS Docker build exited 0.
- Exact-head CI: `43958195473`, SUCCESS, all eight final jobs including downstream Docker builds. Actual frontend logs confirmed 143 browser tests passed, one skipped.
- Delta from production code `906a4ed` contains frontend and documentation only; backend, workers, contracts and schema are unchanged. Only frontend recreation is permitted.
- Fresh current-data backup was copied off-server into the private recovery-backup directory with matching SHA256 and mode 0600. No customer coordinates, identities or prose are included in this document.

## Native acceptance — PASS

The actual existing saved report passed at 360/390/768/1024/1440px with no mocked responses. Document `scrollWidth` equaled `clientWidth` at every width. The original 390px/814px failure is now 390px/390px. Inner scroller bounds remain within the viewport; real inner scrolling reaches the last column without moving the document. All 14 rows, their displayed value associations and persisted deterministic/narrative/assembled payload hashes were unchanged. Native navigation used only the inspected `force=false` cache lookup returning 200 `already_exists`; no paid force/retry/generation was dispatched.

The actual frontend image is `sha256:5e07e5443f92b9944fcda41bf81d169506ed91ef014177161f71e1ad164a5379`, tagged above. The other seven container/image identities, private configuration and checkout gate were preserved; all eight services were running. Public apex/www returned HTTPS 200 with certificate verification; application/database/Redis health was `ok`, and checkout remained 503. All 1310 tracked blobs matched the approved code before deployment markers were written and read back. A documentation-only closeout is separate from the tested/deployed code SHA.

Private evidence is retained under the recovery incident's `2026-11-16` directory, including `planet-table-mobile-width-{width}.json/png`, payload preservation and source-identity receipts. The 390px native screenshot was visually inspected for contained card/table geometry. Source data and customer prose were not changed.

Related incident: [classical planet ordering and original width finding](../2026-11-16/planet-display-order.md). Operational prerequisites: [recovery runbook](../../deployment/recovery-2026-11-16.md).
