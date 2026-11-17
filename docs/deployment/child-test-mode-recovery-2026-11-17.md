# Restoring Child and test payments — 2026-11-17

Status: runtime configuration restored and native readback passed. This is the owner's explicitly requested TEST shop on the production domain, not a live-merchant cutover or historical-data restoration.

## Cause and owner instruction

The rebuilt instance retained the application code but initially left `CHILD_REPORT_ENABLED=false` and omitted YooKassa app credentials. The owner clarified that Child and test YooKassa checkout were already enabled before server loss and requested their return without restoring old data. Requiring live-merchant acceptance for that test-mode restoration was the wrong boundary.

## Restored configuration

- `CHILD_REPORT_ENABLED=true` in backend, worker, scheduler and refinement-monitor, verified in actual settings. No frontend Child build flag exists; billing `child_enabled` controls native discovery.
- YooKassa shop ID/secret were reloaded narrowly from the owner's named repository `.env`, without shell evaluation or disclosure. The secret has the test prefix, and canonical authenticated `GET /v3/me` returned HTTP 200 with `test=true` before installation and from the actual configured backend before reopening ingress.
- The three running consumers were recreated under the unchanged production/recovery Compose chain; scheduler was separately created held, checked, then started. Exact runtime credential values matched the named source in all four consumers; unrelated environment values, including database/session/SMTP/OAuth/LLM settings, were preserved.
- The old recovery-only POST `/payments` 503 guard was removed. Canonical Plus checkout is POST `/api/v1/subscriptions/checkout`, not the retired legacy SKU flow; its unauthenticated response is now the expected 401. No authenticated checkout was submitted.

## Safe transition and retained proof

- Application code remains `789d7b77fab675f8aead9ea3cafd356fb01d82a7`. All image IDs were unchanged; PostgreSQL, Redis, frontend and Caddy retained their exact container IDs. All eight services were running and original restart policies were read back.
- Full API ingress except health was briefly frozen through the existing Caddy mount; scheduler was stopped/restart-disabled. Exact-node active/reserved/scheduled inspections, all broker lists and unacked representations, durable task/unknown-outcome checks and accepted API sockets were checked twice before writer changes. Backend supervisor received graceful TERM only with automatic restart disabled; worker recreation used infinite stop grace.
- The production-specific private controller was reviewed, corrected and tested before mutation. The staging-only maintenance controller was not invoked. Only its reviewed portable read-only diagnostic functions were reused.
- A conservative broker diagnostic initially stopped on Kombu 5.7.0's `_kombu.binding_deadlines` zset. Installed transport source proved this is expiring-binding bookkeeping, distinct from `unacked`/`unacked_index`. A version/key/type-guarded classification was reviewed and tested: only that metadata is recorded separately; every actual task list/hash/other zset remains counted. Nothing was deleted or cleared to manufacture a drain.
- Private checkpoint progression reached `restored`. An interrupted readiness check has a non-recreating `verify` continuation; scheduler validation failures re-hold it before public restore.
- Fresh database dump was privately copied off-server with matching SHA256. Private config, Caddy and overlay backups plus checkpoints are under `/root/astrotype-recovery-evidence/child-test-config-restore/`; credentials and full state inventories must never be published.

## Native acceptance and honest limits

- Public health returned application/database/Redis `ok`; maintenance was removed.
- Actual authenticated billing access reported `child_enabled=true`; the sidebar Child link was active and opened the native Child page without response mocks. Existing tariff enforcement remains unchanged; no Plus entitlement was fabricated.
- Native billing rendered an enabled “Оформить Плюс” button. The verifier blocked mutations and did not click checkout, create/select a child, open a questionnaire, retry or generate content.
- Post-readback counts remained: zero Child profiles/generations/payments, one completed natal generation and six ready natal segments. No operator payment or LLM generation was created. Existing data/volumes were not restored over or deleted.
- This proves restored configuration, test-shop identity, route/auth readiness and UI discovery, not a completed checkout, provider-delivered webhook or Child narrative-quality acceptance. Live merchant/fiscalization readiness and broader E22 observation/budget gates remain separate. Birth-refinement flags were not changed.

See [fresh-instance recovery](recovery-2026-11-16.md) and the [Child rollout runbook](child-report-rollout.md). Historical release paths in the latter are not the rebuilt host's active chain.
