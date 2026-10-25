"""E22 S12 review regressions through HTTP on disposable PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.main import app
from app.modules.child import models
from tests.integration.test_child_api import PAYLOAD
from tests.integration.test_child_generation_lifecycle import _grant_direct_child_access, _seed_lifecycle

pytestmark = pytest.mark.usefixtures("_setup_database")


async def _completed_current(client: AsyncClient, child_id: str, *, key: str) -> str:
    response = await client.get(f"/api/v1/child/children/{child_id}/questionnaires/current")
    assert response.status_code == 200, response.text
    data = response.json()
    path = f"/api/v1/child/questionnaires/{data['session_id']}"
    answers = [{"question_key": q["key"], "option": q["options"][0]["code"]} for q in data["questions"]]
    assert (await client.put(path + "/answers", json={"answers": answers})).status_code == 200
    response = await client.post(path + "/complete", headers={"Idempotency-Key": key})
    assert response.status_code == 200, response.text
    return str(data["session_id"])


async def _setup_current(
    db: AsyncSession, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> tuple[str, str, list[UUID]]:
    seed = await _seed_lifecycle(db)
    await _grant_direct_child_access(db, user_id=seed.owner_id)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    dispatches: list[UUID] = []

    def dispatch(*, generation_id: UUID) -> str:
        dispatches.append(generation_id)
        return f"child-generation-{generation_id}"

    monkeypatch.setattr("app.modules.child.router.dispatch_child_generation", dispatch)
    response = await client.post("/api/v1/child/children", json=PAYLOAD, headers={"Idempotency-Key": "review-child"})
    assert response.status_code == 201, response.text
    child_id = str(response.json()["id"])
    questionnaire_id = await _completed_current(client, child_id, key="review-complete")
    return child_id, questionnaire_id, dispatches


async def _counts(db: AsyncSession) -> tuple[int, ...]:
    counts = []
    for model in (
        models.ChildGeneration,
        models.ChildGenerationEvent,
        models.ChildAgeSnapshot,
        models.ChildChartVersion,
        models.ChildQuestionnaireSession,
        models.ChildReport,
        models.ChildSegmentGeneration,
    ):
        counts.append(int(await db.scalar(select(func.count()).select_from(model)) or 0))
    return tuple(counts)


async def test_accepted_retry_precedes_changed_current_lineage(
    db_session: AsyncSession, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    child_id, questionnaire_id, dispatches = await _setup_current(db_session, client, monkeypatch)
    target: dict[str, Any] = {"child_profile_id": child_id, "questionnaire_session_id": questionnaire_id}
    headers = {"Idempotency-Key": "review-accepted"}
    original = await client.post("/api/v1/child/reports", json=target, headers=headers)
    assert original.status_code == 202, original.text
    generation_id = UUID(original.json()["generation_id"])
    generation = await db_session.scalar(
        select(models.ChildGeneration).where(models.ChildGeneration.generation_id == generation_id)
    )
    assert generation is not None
    original_chart_id = generation.child_chart_version_id
    # A public correction changes the chart and a subsequent questionnaire read
    # appends a newer immutable age snapshot. Neither changes the accepted target.
    patched = await client.patch(f"/api/v1/child/children/{child_id}", json={"birth_date": "2021-05-13"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["current_chart"]["version"] == 2
    assert (
        await db_session.scalar(
            select(models.ChildChartVersion.id)
            .where(models.ChildChartVersion.child_profile_id == UUID(child_id))
            .order_by(models.ChildChartVersion.version.desc())
            .limit(1)
        )
        != original_chart_id
    )
    newer_questionnaire_id = await _completed_current(client, child_id, key="review-newer-complete")
    assert newer_questionnaire_id != questionnaire_id
    generation.status = "failed"
    await db_session.commit()
    tomorrow = datetime.now(UTC) + timedelta(days=1)

    class NextDayClock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> NextDayClock:
            return cls.fromtimestamp(tomorrow.timestamp(), tz)

    monkeypatch.setattr("app.modules.child.repository.datetime", NextDayClock)
    before = await _counts(db_session)
    replay = await client.post("/api/v1/child/reports", json=target, headers=headers)
    assert replay.status_code == 202, replay.text
    assert replay.json()["generation_id"] == str(generation_id)
    assert replay.json()["status"] == "failed"
    assert replay.json()["report_id"] == original.json()["report_id"]
    fresh = await client.post("/api/v1/child/reports", json=target, headers={"Idempotency-Key": "review-fresh-stale"})
    assert fresh.status_code == 404, fresh.text
    conflict = await client.post(
        "/api/v1/child/reports", json=target | {"questionnaire_session_id": newer_questionnaire_id}, headers=headers
    )
    assert conflict.status_code == 409, conflict.text
    assert await _counts(db_session) == before
    assert dispatches == [generation_id]


@pytest.mark.parametrize("stale_input", ["dob", "local_date", "rules", "input_hash"])
async def test_new_acceptance_rejects_authoritatively_stale_latest_snapshot(
    db_session: AsyncSession, client: AsyncClient, monkeypatch: pytest.MonkeyPatch, stale_input: str
) -> None:
    child_id, questionnaire_id, dispatches = await _setup_current(db_session, client, monkeypatch)
    questionnaire = await db_session.get(models.ChildQuestionnaireSession, UUID(questionnaire_id))
    assert questionnaire is not None
    snapshot = await db_session.get(models.ChildAgeSnapshot, questionnaire.age_snapshot_id)
    assert snapshot is not None
    assert snapshot.age_stage == "3-6"
    if stale_input == "dob":
        before_correction = await _counts(db_session)
        # Do not call GET questionnaires/current after the public correction:
        # validation must not depend on that read appending a new age snapshot.
        patched = await client.patch(f"/api/v1/child/children/{child_id}", json={"birth_date": "2019-05-12"})
        assert patched.status_code == 200, patched.text
        assert patched.json()["current_chart"]["version"] == 2
        assert (await _counts(db_session))[2] == before_correction[2]
    elif stale_input == "local_date":
        # SQL fixture setup deliberately models an already-persisted historical
        # artifact; production ORM append-only guards remain enabled.
        await db_session.execute(
            update(models.ChildAgeSnapshot)
            .where(models.ChildAgeSnapshot.id == snapshot.id)
            .values(as_of_date=snapshot.as_of_date - timedelta(days=1))
        )
    elif stale_input == "rules":
        await db_session.execute(
            update(models.ChildAgeSnapshot)
            .where(models.ChildAgeSnapshot.id == snapshot.id)
            .values(age_rules_version="obsolete-review-rules")
        )
    else:
        await db_session.execute(
            update(models.ChildAgeSnapshot).where(models.ChildAgeSnapshot.id == snapshot.id).values(input_hash="0" * 64)
        )
    await db_session.commit()
    before = await _counts(db_session)
    rejected = await client.post(
        "/api/v1/child/reports",
        json={"child_profile_id": child_id, "questionnaire_session_id": questionnaire_id},
        headers={"Idempotency-Key": "review-stale-acceptance"},
    )
    assert rejected.status_code == 404, rejected.text
    assert rejected.json() == {"detail": "Child resource not found"}
    assert await _counts(db_session) == before
    assert dispatches == []
