from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.modules.authorization.report_access import ReportAccessPolicy
from app.modules.catalog.service import REPORT_CATALOG, AccessClass


class _PlusReader:
    def __init__(self, active: bool) -> None:
        self.active = active
        self.calls: list[UUID] = []

    async def has_active_plus_access(self, user_id: UUID) -> bool:
        self.calls.append(user_id)
        return self.active


@pytest.mark.parametrize("report_identifier", ["basic_natal", "self", "self_full"])
async def test_free_and_plus_accounts_keep_basic_report_access(report_identifier: str) -> None:
    for plus_active in (False, True):
        reader = _PlusReader(active=plus_active)
        decision = await ReportAccessPolicy(reader).check(uuid4(), report_identifier)

        assert decision.allowed is True
        assert decision.report_type == "basic_natal"
        assert decision.access_state == "active"
        assert reader.calls == []


async def test_free_account_denies_every_current_plus_only_report_without_payload() -> None:
    user_id = uuid4()
    plus_only = [
        definition.report_type
        for definition in REPORT_CATALOG.values()
        if definition.access_class is AccessClass.PLUS_ONLY
    ]
    reader = _PlusReader(active=False)
    policy = ReportAccessPolicy(reader)

    for report_type in plus_only:
        decision = await policy.check(user_id, report_type)

        assert decision.allowed is False
        assert decision.to_payload() == {
            "access_state": "locked",
            "report_type": report_type,
            "required_level": "plus",
            "reason": "plus_required",
            "upgrade_url": "/billing",
        }
        assert set(decision.to_payload()) == {
            "access_state",
            "report_type",
            "required_level",
            "reason",
            "upgrade_url",
        }

    assert reader.calls == [user_id] * len(plus_only)


async def test_active_plus_account_allows_every_current_plus_only_report() -> None:
    user_id = uuid4()
    plus_only = [
        definition.report_type
        for definition in REPORT_CATALOG.values()
        if definition.access_class is AccessClass.PLUS_ONLY
    ]
    reader = _PlusReader(active=True)
    policy = ReportAccessPolicy(reader)

    for report_type in plus_only:
        decision = await policy.check(user_id, report_type)
        assert decision.allowed is True
        assert decision.report_type == report_type
        assert decision.access_state == "active"

    assert reader.calls == [user_id] * len(plus_only)


async def test_legacy_career_sku_uses_plus_only_policy_without_identifier_rewrite() -> None:
    denied = await ReportAccessPolicy(_PlusReader(active=False)).check(uuid4(), "career_full")
    allowed = await ReportAccessPolicy(_PlusReader(active=True)).check(uuid4(), "career_full")

    assert denied.allowed is False
    assert denied.report_type == "career"
    assert allowed.allowed is True
    assert allowed.report_type == "career"


@pytest.mark.parametrize("state", ["expired_plus", "tier_only_plus"])
async def test_inactive_plus_states_keep_basic_and_lock_every_plus_only_report(state: str) -> None:
    del state  # Both states intentionally resolve to the same backend proof: no active Plus.
    user_id = uuid4()
    reader = _PlusReader(active=False)
    policy = ReportAccessPolicy(reader)

    basic = await policy.check(user_id, "basic_natal")
    assert basic.allowed is True

    for definition in REPORT_CATALOG.values():
        if definition.access_class is AccessClass.BASIC:
            continue
        decision = await policy.check(user_id, definition.report_type)
        assert decision.allowed is False
        assert decision.reason == "plus_required"
