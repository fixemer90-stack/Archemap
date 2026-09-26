# E9 staging environment — discrepancy audit

## Purpose

This register records the 2026-09-26 re-audit of the E9 staging contract, repository topology and live `staging.astrotype.ru` runtime. Story criteria remain authoritative; this file separates verified infrastructure from implementation, isolation and rollout-evidence gaps.

## Verified baseline

Repository/runtime audit:

- local E9 contracts, Compose, Caddy and application settings were inspected;
- live checks were read-only;
- public staging returns HTTP 401 without Basic Auth and includes `X-Robots-Tag: noindex, nofollow, noarchive` plus HSTS;
- public production health remains HTTP 200;
- staging backend health reports database and Redis `ok`;
- staging and production Compose contracts parse successfully on the VPS;
- staging Caddy configuration validates successfully;
- staging Alembic current/head is `a6b7c8d9e0f1`;
- staging uses project `astrotype-staging`, separate PostgreSQL/Redis containers and volumes;
- production backend, worker, frontend, PostgreSQL and Redis remain only on `astrotype_default`; only production Caddy also joins `astrotype_edge`.

Current live staging state:

- six staging users;
- one YooKassa payment is provider-confirmed `succeeded`, `paid=true`, `test=true`, 999 RUB;
- the same local payment has `paid_at`, an active `self` entitlement and `account_tier=plus`;
- there are zero staging `payment_webhooks` rows;
- effective backend environment is `APP_ENV=staging`, `AUTO_VERIFY_EMAIL=true`, `LLM_ENABLED=false`, `LLM_PROVIDER=mock`;
- `.env.staging` and the Basic Auth include file have mode `600`;
- staging PostgreSQL password and application secret differ from production.

## Summary status

| Area                    | Status      | Reason                                                                                                                      |
| ----------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------- |
| Stateful isolation      | ✅ Verified | PostgreSQL/Redis containers, networks, database and named volumes are separate from production.                             |
| Public ingress          | ✅ Verified | TLS, Basic Auth challenge, noindex header and production regression health are live.                                        |
| Edge-network isolation  | 🟡 Partial  | Staging backend and frontend join `astrotype_edge`; the contract says production Caddy should see only the staging gateway. |
| Credential isolation    | 🟡 Partial  | Staging uses a valid test shop, but staging and production containers currently use the same YooKassa credential pair.      |
| Deploy traceability     | 🟡 Partial  | `.deploy-sha` is stale and the live source tree combines files from different repository revisions.                         |
| Runtime topology parity | 🟡 Partial  | Current repository Compose includes a scheduler, while the live staging project has no scheduler container.                 |
| Browser auth hardening  | 🟡 Partial  | Auth cookies are marked Secure only for `APP_ENV=production`, not for the public HTTPS staging environment.                 |
| YooKassa smoke          | 🟡 Partial  | Checkout/provider/payment/entitlement/tier evidence exists, but no webhook was received or stored.                          |

## Implementation and contract gaps

| Gap                                        | Evidence                                                                                                                                                                                                                   | Impact                                                                                                                                                                                                                              | Closure proof                                                                                                                                                                          |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Edge network exposes more than the gateway | `staging-backend` and `staging-frontend` are attached to `astrotype_edge` alongside `staging-gateway`; production Caddy is also on that network.                                                                           | The documented single ingress boundary is false. Containers on the shared edge network can address staging backend/frontend directly, bypassing gateway Basic Auth as a network boundary.                                           | Put gateway, backend and frontend on a staging-private application network; attach only gateway to `astrotype_edge`; verify Docker network membership and public Basic Auth afterward. |
| YooKassa credentials are shared            | Staging and production credential hashes match. Both credential probes return HTTP 200 and only `test=true` payment objects.                                                                                               | Staging is using a test shop, but payment configuration is not isolated from the production runtime. Rotation or test activity affects both environments, and an accidental production credential replacement would propagate risk. | Provision a staging-only test-shop credential pair, prove its hash differs from production, and verify provider objects remain `test=true`.                                            |
| Staging deploy identity is not coherent    | `.deploy-sha` points to `0a498a0` from 2026-09-04, before E9. Live `docker-compose.staging.yml` matches `a7d3b2e`, E9 docs/Caddy match later repository state, while the deployed runbook and env example match `1f6a9c9`. | Operators cannot map the running staging topology to one exact reviewed/green SHA or reproduce it reliably.                                                                                                                         | Deploy one exact green commit, write a staging-specific deploy marker, record image/source hashes, and verify all runtime contract files match that commit.                            |
| Current scheduler topology is not deployed | Current repository staging Compose declares `scheduler`; live staging has backend, worker, frontend, gateway, PostgreSQL and Redis only.                                                                                   | Periodic tasks documented/required by the current runtime may not execute on staging, so staging cannot validate scheduler-dependent behavior.                                                                                      | Deploy the committed Compose revision, verify exactly one healthy/running beat scheduler, and add scheduler logs/readback to the runbook.                                              |
| Staging auth cookies lack `Secure`         | Auth router uses `secure=settings.APP_ENV == "production"`.                                                                                                                                                                | Browser sessions on a public HTTPS staging host do not exercise the production cookie security contract and are less hardened than expected.                                                                                        | Treat `staging` as a secure-cookie environment, add config tests, deploy, and inspect `Set-Cookie` flags through the Basic Auth protected host.                                        |

## YooKassa smoke evidence gap

The existing staging payment proves:

- checkout/provider credentials work against a YooKassa test shop;
- provider truth is `succeeded`, `paid=true`, `test=true`;
- local fallback reconciliation can set `paid_at`, grant `self`, and upgrade the account to Plus.

It does not close the E9 webhook criterion because `payment_webhooks` contains zero rows. The result can only prove fallback reconciliation, not `YooKassa -> automatic webhook -> canonical reconciliation -> entitlement/tier` delivery.

Closure proof:

1. Register the staging webhook URL in the test shop.
2. Complete a fresh checkout without manually replaying a notification and without triggering billing/report fallback first.
3. Record a processed `payment.succeeded` webhook row for that provider payment.
4. Verify local succeeded payment, `paid_at`, active entitlement, Plus tier and authenticated `plus_active` state for the same staging user.
5. Verify the staging return URL and webhook URL never point to production.

## Documentation drift corrected

- E9 is no longer described as waiting for the entire checkout smoke: checkout and fallback readback exist, while webhook delivery specifically remains open.
- S01 now names the edge-network, credential, deploy-identity, scheduler and cookie-security gaps.
- Historical 2026-09-12 evidence remains labeled as historical and is separated from current 2026-09-26 readback.
- The Feature links this consolidated audit register.

## Closure order

1. Restore a gateway-only edge boundary.
2. Separate staging YooKassa test credentials from the production runtime.
3. Make staging cookies Secure and add regression coverage.
4. Deploy one exact current green Compose revision, including the scheduler, with a staging-specific deploy marker.
5. Run a fresh automatic webhook smoke and authenticated billing readback.
6. Re-run production regression health, Caddy/Compose validation, network inspection and exact-SHA CI.

## Closure rule

A succeeded test payment and active entitlement do not prove webhook delivery when no webhook row exists. Separate env files do not prove credential isolation when their secret values are identical. Healthy containers do not prove deploy traceability when the source tree and marker cannot be tied to one exact commit.
