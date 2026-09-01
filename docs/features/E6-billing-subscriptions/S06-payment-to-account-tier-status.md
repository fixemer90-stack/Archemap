# S06: Payment-to-account-tier status update

## Status

⬜ Не начато

## Context

The account must have a visible Free/Plus status, but in the first implementation that status must not restrict functionality.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`

## Files affected

- `docs/architecture/account-tier-role-foundation.md`
- `backend/app/modules/users/models.py`
- user schemas / `/users/me` response
- payment success orchestration
- database migration
- backend tests

## What to do

For implemented stories, keep this document as the acceptance contract and regression checklist. For pending stories, implement only this slice and update the status after code/tests pass.

## Acceptance criteria

- [ ] User model stores account tier/status `free` or `plus`.
- [ ] Existing users default to `free`.
- [ ] Confirmed payment updates account tier to `plus`.
- [ ] Tier update is idempotent for repeated webhooks.
- [ ] `/users/me` or billing access state exposes the tier.
- [ ] No endpoint starts blocking Free users because of this story.
- [ ] Tests prove tier is status-only.

## Verification

```bash
./backend/.venv/bin/python -m pytest backend/tests/unit/test_payments.py -q
```

Add narrower or broader checks in the implementation PR when this story touches additional modules.
