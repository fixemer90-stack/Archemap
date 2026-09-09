# SRS-E8: Account-level report access

Status: target requirements; implementation pending
Feature: `docs/features/E8-account-level-report-access/FEATURE.md`
Architecture: `docs/architecture/account-levels-report-access-policy.md`

## 1. Purpose and scope

This SRS defines which reports are available to Astrotype account levels and how backend APIs and clients must enforce that matrix.

Normative product rule:

```text
Basic report: every authenticated account level
All other reports: active Plus only
```

## 2. Definitions

| Term             | Definition                                                        |
| ---------------- | ----------------------------------------------------------------- |
| Free             | Default registered-account level                                  |
| Plus             | Paid account level with currently active backend-confirmed access |
| Basic report     | Canonical baseline Astrotype Self natal report                    |
| Plus-only report | Every report type other than the basic report                     |
| Access class     | Backend catalog value `basic` or `plus_only`                      |

## 3. Functional requirements

### FR-E8.1 Account levels

- Every registered account shall have a Free- or Plus-compatible state.
- Authentication shall be required for report access.
- Account display tier shall not replace active subscription/entitlement verification.

### FR-E8.2 Basic report availability

- The system shall classify exactly one canonical report type as `basic`.
- Every authenticated Free or Plus account shall be able to create, generate, read, regenerate and export its own basic report.
- The backend shall not require a paid entitlement solely for the basic report.
- Ownership checks shall still prevent access to another user's basic report.

### FR-E8.3 Plus-only reports

- Every report type other than the basic report shall be `plus_only`.
- A new or unknown report type shall not default to free access.
- Career, Love, Child and any future specialized/expanded report shall require active Plus.
- Free/expired/inactive accounts shall receive safe locked metadata, not protected content.

### FR-E8.4 Active Plus proof

For monthly SaaS, Plus-only access shall require:

```text
plan_code == 'astrotype_plus_monthly'
AND status IN ('active', 'cancel_scheduled')
AND current_period_start <= now < current_period_end
```

`account_tier='plus'` alone shall not grant Plus-only access.

### FR-E8.5 Operation coverage

The same report policy shall be applied to:

- create/generate;
- report/status reads;
- narrative segments and calculation layer;
- regenerate;
- PDF/export/share/download artifacts.

### FR-E8.6 API response

A locked Plus-only response shall include a machine-readable access state, report type, `required_level=plus`, denial reason and safe upgrade URL. It shall not include report body, segment payload, calculations or artifact URL.

A Free request for the basic report shall not return payment-required solely due to account level.

### FR-E8.7 Frontend behavior

- Dashboard/product surfaces shall show the basic report as available at all account levels.
- Other report cards shall show `Доступно с Plus` while locked.
- Billing shall state that the basic report remains available without Plus.
- Frontend shall consume backend access decisions and shall not infer Plus from checkout return state.

### FR-E8.8 Retention and migration

- Upgrade, downgrade, expiry and identifier migration shall not delete profiles, reports or generated artifacts.
- Existing `self` / `self_full` identifiers shall be mapped to the canonical basic-report code without breaking persisted references.
- Read-after-expiry behavior for previously generated Plus-only reports shall be explicitly decided before rollout.

## 4. Non-functional requirements

| ID       | Requirement                                                            |
| -------- | ---------------------------------------------------------------------- |
| NFR-E8.1 | Authorization is server-side and fail-closed for unknown report types. |
| NFR-E8.2 | All clients receive consistent decisions from the same backend policy. |
| NFR-E8.3 | Policy decisions are testable at exact subscription time boundaries.   |
| NFR-E8.4 | Locked responses leak no protected report data or artifact URLs.       |
| NFR-E8.5 | Migration is non-destructive and auditable.                            |

## 5. Data/catalog contract

Every report catalog item shall expose at least:

| Field          | Meaning                           |
| -------------- | --------------------------------- |
| `report_type`  | Stable backend identifier         |
| `display_name` | User-visible title                |
| `access_class` | `basic` or `plus_only`            |
| `enabled`      | Whether the report can be created |

Invariant:

```text
count(report_catalog where access_class == 'basic') == 1
```

## 6. API contract

Minimum policy metadata:

```json
{
  "report_type": "career",
  "access_state": "locked",
  "required_level": "plus",
  "reason": "plus_required",
  "upgrade_url": "/billing"
}
```

The concrete HTTP status may follow the existing Astrotype locked-response convention, but payload safety and consistency across routes are mandatory.

## 7. Verification criteria

E8 requires automated tests and live smoke proving:

1. Free basic create/read/regenerate/export succeeds.
2. Plus basic create/read/regenerate/export succeeds.
3. Free direct access to every Plus-only route fails without payload leakage.
4. Active Plus access to enabled Plus-only reports succeeds.
5. Expired Plus retains basic access and fails Plus-only access.
6. Tier-only Plus without active proof fails Plus-only access.
7. Unknown report types never become free by default.
8. Existing report/profile/artifact data survives migration.
9. Frontend labels and CTAs match backend policy.

## 8. Dependencies

- E7 account-tier foundation.
- E6 monthly Plus subscription/access lifecycle.
- Astrotype v2 report APIs and artifact routes.
- Backend report/product catalog.
- Dashboard, billing and report-reader clients.

## 9. Current implementation discrepancy

At documentation time, current Astrotype v2 Self routes use a paid `self` entitlement gate. Therefore the target basic-report requirement is not yet implemented. E8 Stories must remove that gate only for the canonical basic report and preserve Plus-only protection elsewhere.
