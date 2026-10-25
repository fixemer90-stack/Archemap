from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.main import app
from app.modules.child import models
from tests.integration.test_child_generation_lifecycle import _grant_direct_child_access, _seed_lifecycle

pytestmark = [pytest.mark.asyncio, pytest.mark.usefixtures("_setup_database")]


async def test_private_export_is_owner_scoped_archived_read_and_strips_worker_credentials(
    db_session: AsyncSession, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed = await _seed_lifecycle(db_session)
    child = await db_session.get(models.ChildProfile, seed.child_id)
    assert child is not None
    child.status = "archived"
    child.caregiver_context = {"LLM_API_KEY": "never-export", "nested": {"lifecycle_token": "never-export"}}
    await db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    path = f"/api/v1/child/children/{seed.child_id}/export"
    assert (await client.get(path)).status_code == 402
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", False)
    response = await client.get(path)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert "attachment" in response.headers["content-disposition"]
    assert response.json()["records"]["child_profiles"][0]["id"] == str(seed.child_id)
    assert "never-export" not in response.text
    app.dependency_overrides[get_current_user] = uuid4
    assert (await client.get(path)).json() == (await client.get(f"/api/v1/child/children/{uuid4()}/export")).json()
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.APP_ENV", "production")
    denied = await client.get(path)
    assert denied.status_code == 403
    assert "records" not in denied.text
