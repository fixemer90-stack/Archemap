from __future__ import annotations

from uuid import UUID, uuid4

from app.modules.authorization.report_access import ReportAccessPolicy


class _PlusReader:
    def __init__(self, active: bool, *, direct_products: set[str] | None = None) -> None:
        self.active = active
        self.calls: list[UUID] = []
        self.direct_products = direct_products or set()
        self.direct_calls: list[tuple[UUID, str]] = []

    async def has_active_plus_access(self, user_id: UUID) -> bool:
        self.calls.append(user_id)
        return self.active

    async def has_active_direct_product_access(self, user_id: UUID, product: str) -> bool:
        self.direct_calls.append((user_id, product))
        return product in self.direct_products


async def test_basic_report_is_available_without_paid_access() -> None:
    reader = _PlusReader(active=False)
    user_id = uuid4()

    decision = await ReportAccessPolicy(reader).check(user_id, "basic_natal")

    assert decision.allowed is True
    assert decision.access_state == "active"
    assert decision.report_type == "basic_natal"
    assert reader.calls == []


async def test_free_user_receives_safe_plus_locked_metadata() -> None:
    decision = await ReportAccessPolicy(_PlusReader(active=False)).check(uuid4(), "career")

    assert decision.allowed is False
    assert decision.to_payload() == {
        "access_state": "locked",
        "report_type": "career",
        "required_level": "plus",
        "reason": "plus_required",
        "upgrade_url": "/billing",
    }
    assert not ({"payload", "content", "segments", "artifact_url"} & decision.to_payload().keys())


async def test_active_plus_user_can_access_plus_only_report() -> None:
    decision = await ReportAccessPolicy(_PlusReader(active=True)).check(uuid4(), "career")

    assert decision.allowed is True
    assert decision.access_state == "active"
    assert decision.report_type == "career"


async def test_direct_grandfathered_product_grant_only_unlocks_that_report() -> None:
    user_id = uuid4()
    reader = _PlusReader(active=False, direct_products={"love"})

    love = await ReportAccessPolicy(reader).check(user_id, "love")
    child = await ReportAccessPolicy(reader).check(user_id, "child")

    assert love.allowed is True
    assert love.report_type == "love"
    assert child.allowed is False
    assert reader.direct_calls == [(user_id, "love"), (user_id, "child")]


async def test_tier_only_plus_does_not_bypass_backend_plus_proof() -> None:
    user_id = uuid4()
    reader = _PlusReader(active=False)

    decision = await ReportAccessPolicy(reader).check(user_id, "career")

    assert decision.allowed is False
    assert reader.calls == [user_id]


async def test_unknown_report_type_fails_closed() -> None:
    decision = await ReportAccessPolicy(_PlusReader(active=True)).check(uuid4(), "future_report")

    assert decision.allowed is False
    assert decision.reason == "unsupported_report_type"
    assert decision.required_level == "plus"
