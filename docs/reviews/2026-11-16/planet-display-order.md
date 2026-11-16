# Classical planet display order — 2026-11-16

Status: classical planet ordering deployed and verified on the existing saved report. Exact-head CI passed all eight jobs. A separate pre-existing mobile table-width issue was exposed by the additional native geometry check and remains open below.

## Scope and cause

The owner reported apparently random planet ordering. The saved calculation payload places Sun/Moon/Ascendant first and otherwise uses English alphabetical order. The current reader localizes body IDs to Russian, but its old table comparator recognized only English IDs. Every translated label fell through to the same rank while untranslated MC retained a numeric rank and jumped to the beginning.

Native before-state reproduced MC first, followed by Sun/Moon/Ascendant and the wrong remaining order. This was not an astronomical-coordinate or LLM defect.

## Required display behavior

Main bodies always appear first:

1. Солнце / Sun
2. Луна / Moon
3. Меркурий / Mercury
4. Венера / Venus
5. Марс / Mars
6. Юпитер / Jupiter
7. Сатурн / Saturn
8. Уран / Uranus
9. Нептун / Neptune
10. Плутон / Pluto

Known additional bodies/points follow: Chiron, North Node, South Node, Lilith, Part of Fortune, Vertex, Ascendant, MC. Unknown items follow known bodies in stable input order. Duplicate/equal-ranked items preserve their relative order.

The shared presentation helper understands English IDs, Russian labels and display aliases. It sorts a copied array and preserves the original row objects, labels, numeric values and associations. Current v2 VM/table and legacy direct/nested calculation-layer VM use it. Stored calculations, narratives, report versions and provider configuration are not changed.

## Evidence before deployment

- Executable regression was RED on the actual saved-DTO → Russian VM → table path before production changes. The legacy path independently failed before its edit.
- Parent reran behavior groups: localized DTO/table, exact persisted MC regression, RU/EN main bodies/extras, aliases, stable duplicate/unknown handling, identity/nonmutation and direct/nested legacy paths — PASS.
- Full npm test chain, whole ESLint, TypeScript `--noEmit --incremental false` and exact-path Prettier passed. Two pre-existing Next navigation warnings remain; there are no new lint errors.
- Author's focused synthetic-route Playwright run passed desktop/mobile (2 tests); no snapshots or tolerances changed.
- Independent SPEC/code/security reviewer inspected all eight frozen paths, recomputed fingerprints and independently executed behavior tests plus additional Russian DTO/table/legacy cases. PASS, with no blocking findings. This was not independent CI/deployment verification.
- Code commit: `906a4edeb038a8c202147a5a4586b917b4d53b1b`.
- Candidate tree: `d1bdc04c49d88c0d2723bcb9e27e40efa97b7355`, built through a temporary alternate Git index; eventual committed tree was asserted identical.
- Uploaded archive SHA256: `074ab6c94434e6c7d0d4d224cd34185eb65c1632325fc5803253aeb246fd639c`.
- Actual frontend Docker build passed, image index `sha256:a2ce2f70b06d2c3611a77ed3ea5a698611155478ad5fde250deace4372d3a5ac`, tag `astrotype-frontend:tree-d1bdc04c49d8`.
- Delta from deployed code was verified frontend/documentation only; backend, contracts, workflows and production Compose source were unchanged. Existing SMTP/OAuth/LLM private configuration and checkout gate were preserved during archive extraction.

## Data and billing safeguards

A fresh backup containing the owner's completed report—not just the initial empty database—was copied off-server into the private mode-0700 recovery-backup directory; archive mode is 0600 and both copies matched SHA256. Private evidence retains the exact archive path, report identifier, before-state row associations and persisted payload hashes. No customer prose or birth coordinates are published in this report.

The existing report was opened through the native inspected `force=false` lookup, which returned HTTP 200 `already_exists` before any enqueue. Browser request guards permit that exact cache lookup and abort other mutations; responses are not mocked. No force/retry/regeneration request or paid generation was triggered by this investigation.

The earlier owner-initiated report was verified read-only: six real POST requests to DeepSeek chat completions, all HTTP 200; six ready narrative sections; generation duration 14.320454 seconds. Sections are generated concurrently. This establishes real-provider execution for that report, not a new operator-paid smoke or an editorial-quality verdict.

## Final acceptance

- Exact-head CI `43924711975`: SUCCESS, all eight final jobs including downstream Docker build. Frontend logs independently confirmed all behavioral groups and 133 browser tests passed, one skipped.
- Frontend-only rollout passed using the actual candidate image above. Backend, worker, refinement monitor, scheduler, PostgreSQL, Redis and Caddy retained their exact container/image identities. Private env and Caddy configuration fingerprints were unchanged; checkout still returns 503.
- Native, unmocked existing-report desktop after-state passed: all ten main bodies are in classical order, all 14 rows remain, and every row's displayed values/associations match before-state. The report lookup returned 200 `already_exists`; no generation was enqueued.
- The exact original report's deterministic/narrative/assembled payload hashes and stored body order were unchanged in an explicit READ ONLY transaction.
- Public apex/www returned HTTPS 200 with TLS validation; health JSON confirmed application/database/Redis `ok`.
- All 1308 tracked source blobs matched the approved commit. Only after native desktop/order/preservation acceptance were `.deploy-sha` and `.deploy-source-tree` written and read back as the code commit/tree above.
- A documentation-only follow-up records closeout; it is not the tested code/image revision.

## Separate mobile geometry finding — OPEN

The additional native 390px mobile probe passed classical ordering and exact row-association assertions, but then failed its document-width assertion: `clientWidth=390`, `scrollWidth=814`. This is not recorded as an overall mobile smoke PASS.

The overflowing grid item is `V2CalculationLayer`'s `xl:col-span-8` wrapper. Its planet table has `min-w-[760px]`; the grid child lacks a narrow-screen minimum-width constraint, so the table's intrinsic width expands the document instead of remaining within the intended inner scroller. Both the wrapper source and the table's layout classes are unchanged from recovery code `91d63c7` to repair code `906a4ed`. This layout issue was not introduced or fixed by the sorting-only change. No CSS, snapshots, or geometry assertions were weakened to conceal it.

Private evidence retains the failed native geometry assertion, DOM bounding boxes and screenshot. Keep a separate responsive-layout repair open; do not describe this release as having passed the native mobile no-overflow gate.

See [fresh-instance recovery](../../deployment/recovery-2026-11-16.md) for private configuration and operational overlay requirements. Payment and unrelated feature rollout gates remain separate.
