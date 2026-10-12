from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.main import app
from app.modules.profiles.models import PersonProfile
from app.modules.reports.models import Report
from app.modules.users.models import User


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_legacy_reports_api_hides_plus_payloads_from_free_accounts(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"legacy-reports-{user_id}@example.com",
        name="Алина",
        hashed_password="not-used",  # noqa: S106 - inert fixture value
        is_active=True,
        is_verified=True,
    )
    profile = PersonProfile(
        id=profile_id,
        user_id=user_id,
        name="Алина",
        birth_date=date(1990, 1, 1),
        birth_time_accuracy="unknown",
        birth_place="Москва",
        latitude=55.75,
        longitude=37.61,
        timezone="Europe/Moscow",
    )
    basic_report = Report(
        user_id=user_id,
        profile_id=profile_id,
        product="self",
        version=1,
        status="generating",
        mode="full",
        report_data={"basic_marker": "visible"},
        pdf_generated=False,
    )
    love_report = Report(
        user_id=user_id,
        profile_id=profile_id,
        product="love",
        version=1,
        status="ready",
        mode="full",
        report_data={"plus_secret_marker": "must-not-leak"},
        pdf_generated=False,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(profile)
    await db_session.flush()
    db_session.add_all([basic_report, love_report])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user_id
    monkeypatch.setattr(
        "app.modules.reports.router.get_latest_narrative_for_report",
        AsyncMock(return_value=None),
    )

    basic = await client.get(f"/api/v1/reports/{basic_report.id}")
    locked = await client.get(f"/api/v1/reports/{love_report.id}")
    listed = await client.get("/api/v1/reports")

    assert basic.status_code == 200
    assert basic.json()["report_data"]["basic_marker"] == "visible"
    assert locked.status_code == 402
    assert locked.json()["detail"] == {
        "access_state": "locked",
        "report_type": "love",
        "required_level": "plus",
        "reason": "plus_required",
        "upgrade_url": "/billing",
    }
    assert "plus_secret_marker" not in locked.text
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert [item["id"] for item in listed.json()["items"]] == [str(basic_report.id)]
