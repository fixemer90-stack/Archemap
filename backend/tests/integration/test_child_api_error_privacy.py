from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.main import app
from tests.integration.test_child_api import PAYLOAD
from tests.integration.test_child_generation_lifecycle import _grant_direct_child_access, _seed_lifecycle

pytestmark = [pytest.mark.asyncio, pytest.mark.usefixtures("_setup_database")]


async def test_child_errors_are_uncacheable_and_unknown_field_names_are_redacted(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    seed = await _seed_lifecycle(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    absent = await client.get(f"/api/v1/child/children/{uuid4()}")
    assert absent.status_code == 404
    assert absent.headers.get("cache-control") == "private, no-store"
    body = {**PAYLOAD, "Private child DOB 2021-05-12": "private-value"}
    invalid = await client.post("/api/v1/child/children", headers={"Idempotency-Key": "private-errors"}, json=body)
    assert invalid.status_code == 422
    assert invalid.headers.get("cache-control") == "private, no-store"
    assert "Private child DOB" not in invalid.text
    assert "private-value" not in invalid.text
