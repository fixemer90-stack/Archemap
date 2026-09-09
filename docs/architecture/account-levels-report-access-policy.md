# Account levels and report access policy

Status: target product/access contract; implementation pending
Feature contract: `docs/features/E8-account-level-report-access/FEATURE.md`
SRS: `docs/SRS/SRS-E8-account-level-report-access.md`
Related account-tier foundation: `docs/architecture/account-tier-role-foundation.md`
Related subscription contract: `docs/architecture/monthly-plus-subscription-contract.md`

## Product decision

Astrotype has two user account levels:

- `Free` — the default level for every registered account;
- `Plus` — a paid level backed by active commercial access.

The report rule is intentionally simple:

```text
basic report -> available to every authenticated account, Free or Plus
any other report -> available only while Plus access is active
```

This contract changes the target access model. The current implementation still gates the Astrotype v2 Self report with a `self` entitlement; that behavior must not be described as already compliant until E8 is implemented and verified.

## What “basic report” means

The basic report is the canonical natal report that introduces the account owner to Astrotype. In the active v2 product it is the baseline Astrotype Self natal report built from the user profile and natal calculation.

The basic report includes the useful report experience required by the active v2 contract: deterministic foundation and the standard narrative sections when generation is available. It is not a teaser whose complete payload is returned by the backend and merely hidden in the frontend.

The exact internal report code must be defined once in the backend report catalog. This document uses `basic_natal` as the target canonical code; migration from current `self` / `self_full` identifiers belongs to E8.S01 and must preserve existing report rows and URLs.

## Account levels

| Level  | How it is obtained                   | Report access                             |
| ------ | ------------------------------------ | ----------------------------------------- |
| `Free` | Default for every registered account | Basic report only                         |
| `Plus` | Backend-confirmed active paid access | Basic report plus every other report type |

Authentication remains required. “Available to every account level” does not mean anonymous public access.

`account_tier` is a display/cache field, not sufficient authorization proof. For monthly SaaS, Plus is active only inside a valid paid subscription period. Historical non-expiring purchases may be honored only through an explicit migration/grandfather policy.

## Report access matrix

| Report class | Examples                                                                                  | Free                                                | Plus                                                |
| ------------ | ----------------------------------------------------------------------------------------- | --------------------------------------------------- | --------------------------------------------------- |
| Basic        | Baseline Astrotype Self natal report (`basic_natal`)                                      | Create, generate, read, regenerate, download/export | Same access                                         |
| Plus-only    | Expanded/specialized personal reports; Career; Love; Child; every future non-basic report | Locked metadata and upgrade path only               | Create, generate, read, regenerate, download/export |

Rules:

1. There is exactly one report type classified as `basic` unless a later product decision changes this contract.
2. Every other report type is `plus_only`.
3. A newly added or unknown report type defaults to `plus_only`; it must never become free by omission.
4. The same policy applies to every operation and representation: creation, generation, status, retrieval, segments, calculation layer, regeneration, PDF/export and share/download endpoints.
5. Frontend hiding is not authorization. Backend routes must enforce the matrix.

## Authorization policy

Target policy:

```text
can_access_report(user, report_type) =
  authenticated(user)
  AND (
    report_type.access_class == 'basic'
    OR (
      report_type.access_class == 'plus_only'
      AND plus_access_active(user)
    )
  )
```

For target monthly SaaS:

```text
plus_access_active(user) =
  subscription.plan_code == 'astrotype_plus_monthly'
  AND subscription.status IN ('active', 'cancel_scheduled')
  AND subscription.current_period_start <= now()
  AND subscription.current_period_end > now()
```

`users.account_tier == 'plus'` alone must not unlock Plus-only reports after expiry. A valid legacy entitlement may be accepted only if a documented migration policy explicitly maps it to Plus-compatible access.

## Backend contract

The backend must own a report catalog entry for every report type:

```json
{
  "report_type": "basic_natal",
  "display_name": "Базовый отчёт",
  "access_class": "basic"
}
```

A Plus-only example:

```json
{
  "report_type": "career",
  "display_name": "Карьера",
  "access_class": "plus_only"
}
```

The policy must be evaluated before protected payloads are loaded or serialized. A locked response may expose safe metadata but must not contain the Plus-only report body, narrative segments, calculation payload or downloadable artifact URL.

Suggested locked response:

```json
{
  "access_state": "locked",
  "report_type": "career",
  "required_level": "plus",
  "reason": "plus_required",
  "upgrade_url": "/billing"
}
```

Basic-report endpoints must not return `402` or `missing_entitlement` solely because the account is Free.

## Frontend contract

Free account:

- show the basic report as a normal available product;
- do not label it as a temporary preview;
- show other report cards as requiring Plus;
- route upgrade actions to billing without suggesting that browser return alone activates access.

Plus account:

- show the basic report with no special gate;
- show every other report as available while backend access state is active;
- show period/renewal state according to the monthly Plus contract.

Required copy direction:

| Context           | Copy direction                                                                            |
| ----------------- | ----------------------------------------------------------------------------------------- |
| Free/basic        | `Базовый отчёт доступен на любом уровне аккаунта.`                                        |
| Free/other report | `Этот отчёт доступен с Plus.`                                                             |
| Plus active       | `Все отчёты доступны, пока Plus активен.`                                                 |
| Plus expired      | `Базовый отчёт остаётся доступен. Остальные отчёты снова откроются после продления Plus.` |

Avoid “полный личный отчёт закрыт” when referring to the basic report: under this policy the basic report is available to Free accounts.

## Existing reports and expiry

- A report already generated as the basic report remains available after Plus expires.
- Plus-only reports require active Plus on each protected read/download/regenerate operation unless a separate retention policy explicitly grants read-only history.
- Before implementation, product must choose whether an expired user may read previously generated Plus-only reports. Until that decision is documented, the safe default is locked access after expiry without deleting report data.
- Expiry or downgrade must never delete generated reports or profile data.

## Security and consistency rules

- Backend is the source of truth for report access.
- Direct API and artifact URLs must not bypass policy checks.
- Locked responses contain no protected payload.
- All clients—web, Android/PWA and optional desktop—use the same policy result.
- Unknown report types fail closed as `plus_only` or unsupported.
- Access changes never delete stored user content.

## Verification contract

E8 cannot be marked complete until tests and live smoke prove:

- Free can create, generate, read, regenerate and export the basic report;
- Plus can perform the same basic-report operations;
- Free cannot retrieve any Plus-only report body through direct routes;
- active Plus can create/read every enabled Plus-only report;
- expired/cancelled-at-period-end Plus retains the basic report but loses Plus-only access at the exact access boundary;
- `account_tier='plus'` without active access cannot unlock Plus-only reports;
- unknown report types do not default to free;
- frontend cards and CTAs match backend decisions;
- report rows and generated artifacts are not deleted during upgrade, expiry or migration.

## Open product decision

Define read-after-expiry behavior for already generated Plus-only reports before E8.S05 rollout. This does not affect the invariant that the basic report is always available to an authenticated account.
