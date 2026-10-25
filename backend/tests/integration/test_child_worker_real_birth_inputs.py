from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.dependencies import get_current_user
from app.main import app
from tests.integration.test_child_generation_lifecycle import _grant_direct_child_access, _seed_claimable_full_pipeline
from workers.tasks import child as worker

pytestmark = [pytest.mark.asyncio, pytest.mark.usefixtures("_setup_database")]


@pytest.mark.parametrize("confidence", ["exact", "unknown", "approximate"])
async def test_http_real_birth_chart_reaches_disabled_narrative_not_transient_failure(
    db_session: AsyncSession, client: AsyncClient, monkeypatch: pytest.MonkeyPatch, confidence: str
) -> None:
    seed, _ = await _seed_claimable_full_pipeline(db_session, idempotency_key="real-chart-foundation")
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    monkeypatch.setattr("app.modules.child.service.settings.LLM_ENABLED", False)
    monkeypatch.setattr("app.modules.child.router.dispatch_child_generation", lambda **_: "test-dispatch")
    monkeypatch.setattr(worker, "async_session_factory", async_sessionmaker(db_session.bind, expire_on_commit=False))
    response = await client.post(
        "/api/v1/child/children",
        headers={"Idempotency-Key": "real-chart-child"},
        json={
            "display_name": "Synthetic real chart",
            "relationship_type": "parent",
            "birth_date": "2019-03-12",
            "birth_time": None if confidence == "unknown" else "10:20:00",
            "birth_time_confidence": confidence,
            "birth_place": {
                "label": "Synthetic city",
                "latitude": 55.75,
                "longitude": 37.62,
                "timezone": "Europe/Moscow",
            },
        },
    )
    assert response.status_code == 201, response.text
    cid = response.json()["id"]
    q = (await client.get(f"/api/v1/child/children/{cid}/questionnaires/current")).json()
    saved = await client.put(
        f"/api/v1/child/questionnaires/{q['session_id']}/answers",
        json={
            "answers": [{"question_key": item["key"], "option": item["options"][0]["code"]} for item in q["questions"]]
        },
    )
    assert saved.status_code == 200, saved.text
    completed = await client.post(
        f"/api/v1/child/questionnaires/{q['session_id']}/complete",
        headers={"Idempotency-Key": "real-chart-complete"},
        json={},
    )
    assert completed.status_code == 200, completed.text
    accepted = await client.post(
        "/api/v1/child/reports",
        headers={"Idempotency-Key": "real-chart-report"},
        json={"child_profile_id": cid, "questionnaire_session_id": q["session_id"]},
    )
    assert accepted.status_code == 202, accepted.text
    result = await worker._generate_child_report_async(
        generation_id=accepted.json()["generation_id"], task_id="real-chart-worker"
    )
    assert result["status"] == "narrative_failed", result
    assert result["provider_calls"] == 0
    assert result["report_id"] is not None
    reader = await client.get(f"/api/v1/child/reports/{result['report_id']}")
    assert reader.status_code == 200, reader.text
    assert len(reader.json()["presentation"]["sections"]) == 15
    for section in reader.json()["presentation"]["sections"]:
        assert len(section["actions"]) == len(set(section["actions"]))
