"""API integration coverage for birth-data refinement."""

from __future__ import annotations

import uuid
from datetime import date, time
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.main import app
from app.modules.profiles.models import PersonProfile, ProfileBirthDataRevision
from app.modules.users.models import User


async def _seed_user_profile(db: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    db.add(
        User(
            id=user_id,
            email=f"refinement-api-{user_id}@example.com",
            name="Refinement API",
            hashed_password="not-used",  # noqa: S106
            is_active=True,
            is_verified=True,
        )
    )
    db.add(
        PersonProfile(
            id=profile_id,
            user_id=user_id,
            name="Profile",
            birth_date=date(1990, 1, 1),
            birth_time=time(12, 0),
            birth_time_accuracy="exact",
            birth_place="Moscow, Russia",
            latitude=55.7558,
            longitude=37.6173,
            timezone="Europe/Moscow",
        )
    )
    await db.commit()
    return user_id, profile_id


def _payload(*, place: str = "Saint Petersburg, Russia") -> dict[str, object]:
    return {
        "birth_time": "08:35:00",
        "birth_time_accuracy": "exact",
        "birth_place": place,
        "latitude": 59.9343,
        "longitude": 30.3351,
        "timezone": "Europe/Moscow",
    }


@pytest.mark.usefixtures("_setup_database")
async def test_refinement_api_success_replay_conflict_cooldown_and_status(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, profile_id = await _seed_user_profile(db_session)
    app.dependency_overrides[get_current_user] = lambda: user_id
    delay = monkeypatch.setattr(
        "workers.tasks.astrotype_v2.generate_natal_report_v2.delay",
        lambda **_kwargs: SimpleNamespace(id="task-1"),
    )
    del delay
    key = str(uuid.uuid4())

    response = await client.post(
        f"/api/v1/profiles/{profile_id}/birth-data-refinements",
        headers={"Idempotency-Key": key},
        json=_payload(),
    )
    assert response.status_code == 202
    accepted = response.json()
    assert accepted["status"] == "queued"
    assert accepted["changed_fields"] == ["birth_time", "birth_place", "latitude", "longitude"]

    replay = await client.post(
        f"/api/v1/profiles/{profile_id}/birth-data-refinements",
        headers={"Idempotency-Key": key},
        json=_payload(),
    )
    assert replay.status_code == 202
    assert replay.json()["revision_id"] == accepted["revision_id"]

    conflict = await client.post(
        f"/api/v1/profiles/{profile_id}/birth-data-refinements",
        headers={"Idempotency-Key": key},
        json=_payload(place="Different label"),
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_key_conflict"

    cooldown = await client.post(
        f"/api/v1/profiles/{profile_id}/birth-data-refinements",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={**_payload(), "birth_time": "09:00:00"},
    )
    assert cooldown.status_code == 429
    assert cooldown.json()["code"] == "birth_data_refinement_cooldown"
    assert int(cooldown.headers["Retry-After"]) > 0

    status_response = await client.get(f"/api/v1/profiles/{profile_id}/birth-data-refinement-status")
    assert status_response.status_code == 200
    assert status_response.json()["can_refine"] is False

    revision_response = await client.get(
        f"/api/v1/profiles/{profile_id}/birth-data-refinements/{accepted['revision_id']}"
    )
    assert revision_response.status_code == 200
    assert revision_response.json()["generation_id"] == accepted["generation_id"]


@pytest.mark.usefixtures("_setup_database")
async def test_enqueue_failure_is_retry_safe_without_second_revision(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id, profile_id = await _seed_user_profile(db_session)
    app.dependency_overrides[get_current_user] = lambda: user_id
    key = str(uuid.uuid4())

    def fail_delay(**_kwargs: object) -> object:
        raise RuntimeError("broker down")

    monkeypatch.setattr("workers.tasks.astrotype_v2.generate_natal_report_v2.delay", fail_delay)
    failed = await client.post(
        f"/api/v1/profiles/{profile_id}/birth-data-refinements",
        headers={"Idempotency-Key": key},
        json=_payload(),
    )
    assert failed.status_code == 503
    assert failed.json()["code"] == "refinement_enqueue_unavailable"

    monkeypatch.setattr(
        "workers.tasks.astrotype_v2.generate_natal_report_v2.delay",
        lambda **_kwargs: SimpleNamespace(id="task-recovered"),
    )
    recovered = await client.post(
        f"/api/v1/profiles/{profile_id}/birth-data-refinements",
        headers={"Idempotency-Key": key},
        json=_payload(),
    )
    assert recovered.status_code == 202
    assert await db_session.scalar(select(func.count()).select_from(ProfileBirthDataRevision)) == 1


@pytest.mark.usefixtures("_setup_database")
async def test_refinement_status_rejects_non_owner(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, profile_id = await _seed_user_profile(db_session)
    app.dependency_overrides[get_current_user] = lambda: uuid.uuid4()

    response = await client.get(f"/api/v1/profiles/{profile_id}/birth-data-refinement-status")

    assert response.status_code == 403
    assert response.json()["code"] == "profile_not_owned"
