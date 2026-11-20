"""The resume read must not reconcile external payments as a hidden side effect."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.career import router as career_router
from app.modules.career.access import CareerAccessDecision, CareerAccessPolicy
from app.modules.payments.service import PaymentsService


@pytest.mark.parametrize("allowed", [True, False])
async def test_current_report_checks_saved_access_without_payment_reconciliation(
    monkeypatch: pytest.MonkeyPatch, allowed: bool
) -> None:
    user_id, profile_id = uuid4(), uuid4()
    profile = SimpleNamespace(id=uuid4(), chart_id=uuid4())
    repository = AsyncMock()
    repository.get_profile_for_person.return_value = profile
    repository.get_latest_generation.return_value = None
    monkeypatch.setattr(career_router, "CareerRepository", lambda db: repository)
    monkeypatch.setattr(settings, "CAREER_REPORT_ENABLED", True)
    reconcile = AsyncMock()
    monkeypatch.setattr(PaymentsService, "reconcile_latest_pending_provider_payment", reconcile)
    check_access = AsyncMock(
        return_value=CareerAccessDecision(allowed=allowed, reason=None if allowed else "missing_career_access")
    )
    monkeypatch.setattr(CareerAccessPolicy, "check", check_access)
    db = AsyncMock(spec=AsyncSession)

    if allowed:
        assert await career_router.get_current_career_report(profile_id=profile_id, db=db, current_user=user_id) is None
    else:
        with pytest.raises(HTTPException) as exc:
            await career_router.get_current_career_report(profile_id=profile_id, db=db, current_user=user_id)
        assert exc.value.status_code == 402
        repository.get_latest_generation.assert_not_awaited()
    check_access.assert_awaited_once_with(user_id)
    reconcile.assert_not_awaited()
    db.add.assert_not_called()
    db.commit.assert_not_awaited()
