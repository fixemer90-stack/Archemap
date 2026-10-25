"""S12 real PostgreSQL ownership, rollout and public API contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.dependencies import get_current_user
from app.main import app
from app.modules.child import models
from app.modules.child.repository import ChildRepository
from app.modules.child.service import run_claimed_full_generation
from tests.integration.test_child_generation_lifecycle import (
    NOW,
    CountingProvider,
    _grant_direct_child_access,
    _seed_claimable_full_pipeline,
    _seed_lifecycle,
)

pytestmark = pytest.mark.usefixtures("_setup_database")

PAYLOAD = {
    "display_name": "Alias",
    "relationship_type": "son",
    "child_gender": "male",
    "birth_date": "2021-05-12",
    "birth_time": None,
    "birth_time_confidence": "unknown",
    "birth_place": {"label": "Moscow", "latitude": 55.75, "longitude": 37.61, "timezone": "Europe/Moscow"},
    "caregiver_context": {
        "primary_caregiver": True,
        "daily_contact": "high",
        "boundary_role": "shared",
        "soothing_role": "mostly_me",
    },
}


async def test_children_crud_chart_and_idempotency(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = await _seed_lifecycle(db_session)
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    response = await client.post("/api/v1/child/children", json=PAYLOAD, headers={"Idempotency-Key": "create"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["current_chart"]["version"] == 1
    assert body["age"]["age_stage"] == "3-6"
    replay = await client.post("/api/v1/child/children", json=PAYLOAD, headers={"Idempotency-Key": "create"})
    assert replay.json()["id"] == body["id"]
    mismatch = await client.post(
        "/api/v1/child/children", json=PAYLOAD | {"display_name": "Different"}, headers={"Idempotency-Key": "create"}
    )
    assert mismatch.status_code == 409
    path = f"/api/v1/child/children/{body['id']}"
    patched = await client.patch(path, json={"display_name": "Updated", "birth_date": "2021-05-13"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["current_chart"]["version"] == 2
    assert (await client.get(path)).json()["display_name"] == "Updated"
    assert (await client.get("/api/v1/child/children")).status_code == 200
    assert (await client.delete(path)).status_code == 204
    assert (await client.get(path)).status_code == 404
    assert (await client.delete(path + "?mode=purge")).status_code == 204
    assert (await client.get(path + "?include_archived=true")).status_code == 404


async def test_children_foreign_free_and_flag_off_are_safe(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = await _seed_lifecycle(db_session)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    own = f"/api/v1/child/children/{seed.child_id}"
    missing = f"/api/v1/child/children/{uuid4()}"
    assert (await client.get(own)).status_code == 402
    assert (await client.get(missing)).status_code == 404
    foreign = await _seed_lifecycle(db_session)
    assert (await client.get(f"/api/v1/child/children/{foreign.child_id}")).json() == (await client.get(missing)).json()
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", False)
    assert (await client.get(own)).status_code == 200
    assert (await client.patch(own, json={"display_name": "Blocked"})).status_code == 503
    assert (await client.get(own)).json()["display_name"] == "Ребёнок"


async def test_http_age_update_is_server_owned_and_version_checked(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed, generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="api-age")
    repo = ChildRepository(db_session)
    claim = await repo.claim_generation(
        generation_id=generation.generation_id, task_id="api-test", now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()
    result = await run_claimed_full_generation(db_session, claim=claim, provider=CountingProvider(), now=NOW)
    assert result.report_id is not None
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    monkeypatch.setattr(
        "app.modules.child.router.dispatch_child_generation",
        lambda *, generation_id: f"child-generation-{generation_id}",
    )
    path = f"/api/v1/child/reports/{result.report_id}/age-updates"
    headers = {"Idempotency-Key": "age-http"}
    stale = await client.post(path, headers=headers, json={"expected_core_report_version": 999})
    assert stale.status_code == 409
    unsafe = await client.post(
        path, headers=headers, json={"expected_core_report_version": 1, "payload": {"advice": "unsafe"}}
    )
    assert unsafe.status_code == 422
    accepted = await client.post(path, headers=headers, json={"expected_core_report_version": 1})
    assert accepted.status_code == 202, accepted.text
    replay = await client.post(path, headers=headers, json={"expected_core_report_version": 1})
    assert replay.json() == accepted.json()
    polled = await client.get(f"/api/v1/child/generations/{accepted.json()['generation_id']}")
    assert polled.status_code == 200
    assert polled.json()["operation"] == "age_update"
    assert polled.json()["report_id"] == str(result.report_id)
    assert await db_session.scalar(select(func.count()).select_from(models.ChildReport)) == 1


@pytest.mark.parametrize("scope", ["full_pair", "narrative_all", "failed_sections"])
async def test_regenerate_scopes_have_distinct_immutable_lineage(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    scope: str,
) -> None:
    from uuid import UUID

    from app.modules.child.narrative import DisabledChildSegmentProvider
    from app.modules.child.service import run_claimed_narrative_retry

    seed, generation = await _seed_claimable_full_pipeline(
        db_session, idempotency_key="api-regenerate", snapshot_as_of=datetime.now(UTC)
    )
    repo = ChildRepository(db_session)
    claim = await repo.claim_generation(
        generation_id=generation.generation_id, task_id="first", now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()
    provider = DisabledChildSegmentProvider() if scope == "failed_sections" else CountingProvider()
    result = await run_claimed_full_generation(db_session, claim=claim, provider=provider, now=NOW)
    assert result.report_id is not None
    before = await db_session.scalar(select(func.count()).select_from(models.ChildParentStyleScore))
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    dispatches: list[UUID] = []

    def dispatch(*, generation_id: UUID) -> str:
        dispatches.append(generation_id)
        return f"child-generation-{generation_id}"

    monkeypatch.setattr("app.modules.child.router.dispatch_child_generation", dispatch)
    path = f"/api/v1/child/reports/{result.report_id}/regenerate"
    headers = {"Idempotency-Key": "regen"}
    response = await client.post(path, headers=headers, json={"scope": scope})
    assert response.status_code == 202, response.text
    replay = await client.post(path, headers=headers, json={"scope": scope})
    assert replay.json() == response.json()
    accepted_id = UUID(response.json()["generation_id"])
    assert dispatches == ([accepted_id] if scope == "full_pair" else [])

    # Persist the independent review's public HTTP conflict probe. Compare all
    # columns across the complete Child graph, not merely generation counts.
    from app.modules.child.privacy_export import CHILD_EXPORT_TABLES

    graph_before = {
        table.name: (await db_session.execute(select(table).order_by(*table.primary_key.columns))).mappings().all()
        for table in CHILD_EXPORT_TABLES
    }
    incompatible = "narrative_all" if scope == "full_pair" else "full_pair"
    conflict = await client.post(path, headers=headers, json={"scope": incompatible})
    assert conflict.status_code == 409, conflict.text
    assert conflict.json() == {"detail": "Idempotency key was already used for another target"}
    assert conflict.headers["cache-control"] == "private, no-store"
    graph_after = {
        table.name: (await db_session.execute(select(table).order_by(*table.primary_key.columns))).mappings().all()
        for table in CHILD_EXPORT_TABLES
    }
    assert graph_after == graph_before
    assert dispatches == ([accepted_id] if scope == "full_pair" else [])
    accepted = await db_session.scalar(
        select(models.ChildGeneration).where(models.ChildGeneration.generation_id == accepted_id)
    )
    assert accepted is not None
    assert accepted.source_report_id == result.report_id
    assert accepted.operation == ("full_report" if scope == "full_pair" else "narrative_retry")
    if scope == "full_pair":
        full_claim = await repo.claim_generation(
            generation_id=accepted_id, task_id="full-pair", now=NOW, lease_duration=timedelta(minutes=5)
        )
        assert full_claim is not None
        await db_session.commit()
        counter = CountingProvider()
        full = await run_claimed_full_generation(db_session, claim=full_claim, provider=counter, now=NOW)
        assert full.status == "ready"
        assert full.report_id != result.report_id
        assert counter.calls > 0
        assert await db_session.scalar(select(func.count()).select_from(models.ChildReport)) == 2
    else:
        assert accepted.next_retry_at is not None
        now = accepted.next_retry_at + timedelta(seconds=1)
        retry_claim = await repo.claim_generation(
            generation_id=accepted_id, task_id="retry", now=now, lease_duration=timedelta(minutes=5)
        )
        assert retry_claim is not None
        await db_session.commit()
        counter = CountingProvider()
        retry = await run_claimed_narrative_retry(db_session, claim=retry_claim, provider=counter, now=now)
        assert retry.status == "ready"
        assert retry.report_id == result.report_id
        assert counter.calls > 0
        assert await db_session.scalar(select(func.count()).select_from(models.ChildReport)) == 1
        assert await db_session.scalar(select(func.count()).select_from(models.ChildParentStyleScore)) == before
        published = await client.get(f"/api/v1/child/reports/{result.report_id}")
        assert published.status_code == 200
        assert published.json()["generation_id"] == str(accepted_id)


async def test_questionnaire_ui_contract_completion_and_rollback_reads(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = await _seed_lifecycle(db_session)
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    response = await client.get(f"/api/v1/child/children/{seed.child_id}/questionnaires/current")
    assert response.status_code == 200, response.text
    data = response.json()
    assert 8 <= len(data["questions"]) <= 12
    assert set(data["missing_required"]) == set(data["required_question_ids"])
    assert all(q["prompt"] and all(o["code"] and o["label"] for o in q["options"]) for q in data["questions"])
    path = f"/api/v1/child/questionnaires/{data['session_id']}"
    answers = [{"question_key": q["key"], "option": q["options"][0]["code"]} for q in data["questions"]]
    assert (await client.put(path + "/answers", json={"answers": answers})).status_code == 200
    bad_complete = await client.post(
        path + "/complete", headers={"Idempotency-Key": "bad-complete"}, json={"answers_hash": "client-owned"}
    )
    assert bad_complete.status_code == 422
    completed = await client.post(path + "/complete", headers={"Idempotency-Key": "complete"})
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"
    assert (await client.post(path + "/complete", headers={"Idempotency-Key": "complete"})).json() == completed.json()
    assert (await client.put(path + "/answers", json={"answers": answers})).status_code == 404
    # A later historical-version import must never replace the current UI set.
    historical = models.ChildQuestionnaireSession(
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        age_snapshot_id=UUID(data["age_snapshot_id"]),
        status="completed",
        selected_question_keys=[],
        questionnaire_version="legacy-questionnaire",
        answer_version="legacy-answer",
        context_version="legacy-context",
        consent_version="legacy-consent",
        completion_idempotency_key="historical",
        answers_hash="h" * 64,
    )
    db_session.add(historical)
    await db_session.commit()
    current = await client.get(f"/api/v1/child/children/{seed.child_id}/questionnaires/current")
    assert current.json()["questionnaire_version"] == data["questionnaire_version"]
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", False)
    read = await client.get(f"/api/v1/child/children/{seed.child_id}/questionnaires/current")
    assert read.status_code == 200
    assert read.json()["session_id"] == data["session_id"]
    assert read.headers.get("cache-control") == "private, no-store"


async def test_real_cookie_and_bearer_authentication_and_safe_validation(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.security import create_access_token

    seed = await _seed_lifecycle(db_session)
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)

    async def never_blacklisted(jti: str) -> bool:
        return False

    monkeypatch.setattr("app.dependencies.is_token_blacklisted", never_blacklisted)
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    assert get_current_user not in app.dependency_overrides
    path = f"/api/v1/child/children/{seed.child_id}"
    assert (await client.get(path)).status_code == 401
    assert (await client.get(path, headers={"Authorization": "Bearer invalid"})).status_code == 401
    token, _ = create_access_token(str(seed.owner_id))
    assert (await client.get(path, headers={"Authorization": f"Bearer {token}"})).status_code == 200
    client.cookies.set("access_token", token)
    assert (await client.get(path)).status_code == 200
    bad = await client.post(
        "/api/v1/child/children",
        headers={"Idempotency-Key": "bad"},
        json=PAYLOAD | {"birth_date": "Private invalid birth input"},
    )
    assert bad.status_code == 422
    assert "Private invalid" not in bad.text


@pytest.mark.parametrize("access", ["free", "expired", "inactive", "direct", "plus"])
async def test_every_route_access_matrix_and_denial_payload_load_order(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    access: str,
) -> None:
    from typing import Any

    from sqlalchemy import event
    from sqlalchemy.ext.asyncio import AsyncEngine

    from tests.integration.test_child_generation_lifecycle import _grant_plus_access

    seed, generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="matrix")
    # Upstream score fixtures deliberately omit public input fields; use a valid
    # public profile while retaining their canonical persisted score artifacts.
    from datetime import time

    child = await db_session.get(models.ChildProfile, seed.child_id)
    assert child is not None
    child.birth_time = time(12)
    child.caregiver_context = {}
    await db_session.commit()
    repo = ChildRepository(db_session)
    claim = await repo.claim_generation(
        generation_id=generation.generation_id, task_id="matrix", now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()
    result = await run_claimed_full_generation(db_session, claim=claim, provider=CountingProvider(), now=NOW)
    assert result.report_id is not None
    if access == "plus":
        await _grant_plus_access(db_session, user_id=seed.owner_id)
    elif access != "free":
        await _grant_direct_child_access(
            db_session,
            user_id=seed.owner_id,
            status="inactive" if access == "inactive" else "active",
            expires_at=NOW - timedelta(days=2) if access == "expired" else NOW + timedelta(days=30),
        )
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", False)
    paths: list[tuple[str, str, dict[str, Any] | None, int]] = [
        ("GET", "/children", None, 200),
        ("POST", "/children", PAYLOAD, 503),
        ("GET", f"/children/{seed.child_id}", None, 200),
        ("PATCH", f"/children/{seed.child_id}", {"display_name": "Blocked"}, 503),
        ("DELETE", f"/children/{seed.child_id}", None, 503),
        ("GET", f"/children/{seed.child_id}/questionnaires/current", None, 200),
        ("PUT", f"/questionnaires/{seed.questionnaire_id}/answers", {"answers": []}, 503),
        ("POST", f"/questionnaires/{seed.questionnaire_id}/complete", None, 503),
        (
            "POST",
            "/reports",
            {"child_profile_id": str(seed.child_id), "questionnaire_session_id": str(seed.questionnaire_id)},
            503,
        ),
        ("GET", f"/generations/{generation.generation_id}", None, 200),
        ("GET", f"/reports/{result.report_id}", None, 200),
        ("GET", f"/reports/{result.report_id}/sections", None, 200),
        ("GET", f"/reports/{result.report_id}/versions", None, 200),
        ("POST", f"/reports/{result.report_id}/regenerate", {"scope": "narrative_all"}, 503),
        ("POST", f"/reports/{result.report_id}/age-updates", {"expected_core_report_version": 1}, 503),
        ("GET", f"/reports/{result.report_id}/age-snapshots", None, 200),
        ("GET", f"/reports/{result.report_id}/pdf", None, 200),
    ]
    assert len(paths) == 17
    paid = access in {"plus", "direct"}
    queries: list[str] = []

    def record(conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: bool) -> None:
        queries.append(statement.lower())

    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    event.listen(engine.sync_engine, "before_cursor_execute", record)
    try:
        for method, path, payload, success in paths:
            queries.clear()
            response = await client.request(
                method, "/api/v1/child" + path, json=payload, headers={"Idempotency-Key": "matrix"}
            )
            assert response.status_code == (success if paid else 402), (method, path, response.text)
            if paid and path.endswith("/age-snapshots"):
                assert len(response.json()["age_snapshots"]) == 1
            if paid and path == f"/reports/{result.report_id}":
                assert response.json()["display_name"] == "Child"
            if not paid:
                assert response.json() == {
                    "detail": {
                        "access_state": "locked",
                        "report_type": "child",
                        "required_level": "plus",
                        "reason": "plus_required",
                        "upgrade_url": "/billing",
                    }
                }
                protected = [
                    "child_profiles.display_name",
                    "child_profiles.birth_date",
                    "child_profiles.caregiver_context",
                    "child_reports.report_payload",
                    "child_questionnaire_sessions.answers_hash",
                    "child_generations.operation_payload",
                    "child_answers.answer",
                    "child_guidance_facts.payload",
                    "child_segment_generations.content",
                ]
                assert not any(column in sql for sql in queries for column in protected), queries
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record)
    # The entire persisted graph remains after denial/expiry/flag-off.
    assert await db_session.scalar(select(func.count()).select_from(models.ChildReport)) == 1
    assert await db_session.scalar(select(func.count()).select_from(models.ChildGeneration)) == 1


async def test_foreign_missing_archived_pending_and_cross_child_ids_are_concealed(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.middleware.settings.RATE_LIMIT_ANONYMOUS_PER_MINUTE", 1000)
    from typing import Any

    from sqlalchemy import update

    seed, generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="foreign-matrix")
    repo = ChildRepository(db_session)
    claim = await repo.claim_generation(
        generation_id=generation.generation_id, task_id="foreign", now=NOW, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()
    result = await run_claimed_full_generation(db_session, claim=claim, provider=CountingProvider(), now=NOW)
    assert result.report_id is not None
    foreign = await _seed_lifecycle(db_session)
    await _grant_direct_child_access(db_session, user_id=foreign.owner_id)
    app.dependency_overrides[get_current_user] = lambda: foreign.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)

    def requests_for(
        child: str, questionnaire: str, report: str, gen: str
    ) -> list[tuple[str, str, dict[str, Any] | None]]:
        return [
            ("GET", f"/children/{child}", None),
            ("GET", f"/children/{child}/export", None),
            ("PATCH", f"/children/{child}", {"display_name": "Hidden"}),
            ("DELETE", f"/children/{child}?mode=purge", None),
            ("GET", f"/children/{child}/questionnaires/current", None),
            ("PUT", f"/questionnaires/{questionnaire}/answers", {"answers": []}),
            ("POST", f"/questionnaires/{questionnaire}/complete", None),
            ("POST", "/reports", {"child_profile_id": child, "questionnaire_session_id": questionnaire}),
            ("GET", f"/generations/{gen}", None),
            ("GET", f"/reports/{report}", None),
            ("GET", f"/reports/{report}/sections", None),
            ("GET", f"/reports/{report}/versions", None),
            ("POST", f"/reports/{report}/regenerate", {"scope": "narrative_all"}),
            ("POST", f"/reports/{report}/age-updates", {"expected_core_report_version": 1}),
            ("GET", f"/reports/{report}/age-snapshots", None),
            ("GET", f"/reports/{report}/pdf", None),
        ]

    actual = requests_for(
        str(seed.child_id), str(seed.questionnaire_id), str(result.report_id), str(generation.generation_id)
    )
    missing = requests_for(*(str(uuid4()) for _ in range(4)))
    engine = db_session.bind
    assert isinstance(engine, AsyncEngine)
    statements: list[str] = []

    def capture(conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: bool) -> None:
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        for target, absent in zip(actual, missing, strict=True):
            responses = []
            traces = []
            for method, path, payload in (target, absent):
                statements.clear()
                responses.append(
                    await client.request(
                        method, "/api/v1/child" + path, json=payload, headers={"Idempotency-Key": "foreign"}
                    )
                )
                traces.append(tuple(statements))
            assert [r.status_code for r in responses] == [404, 404]
            assert responses[0].json() == responses[1].json() == {"detail": "Child resource not found"}
            # Bounded timing/work class, not a noisy wall-clock constant-time claim:
            # exactly the same one minimal ownership projection, no payload/provider work.
            assert len(traces[0]) == len(traces[1]) == 1
            assert traces[0] == traces[1]
            assert traces[0][0].startswith("SELECT child_profiles.id")
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
    # Even same-owner but cross-child questionnaire linkage is hidden.
    sibling = await client.post("/api/v1/child/children", headers={"Idempotency-Key": "sibling"}, json=PAYLOAD)
    assert sibling.status_code == 201
    mismatch = await client.post(
        "/api/v1/child/reports",
        headers={"Idempotency-Key": "mismatch"},
        json={"child_profile_id": sibling.json()["id"], "questionnaire_session_id": str(foreign.questionnaire_id)},
    )
    assert mismatch.status_code == 404
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    report_path = f"/api/v1/child/reports/{result.report_id}"
    wrong_age = await client.get(report_path + f"/pdf?age_snapshot_id={uuid4()}")
    assert wrong_age.status_code == 404
    for state in ("archived", "deletion_pending"):
        await db_session.execute(
            update(models.ChildProfile).where(models.ChildProfile.id == seed.child_id).values(status=state)
        )
        await db_session.commit()
        for method, path, payload in actual:
            if method == "DELETE" or (state == "archived" and path.endswith("/export")):
                continue  # archived records remain explicitly purgeable/exportable
            response = await client.request(
                method, "/api/v1/child" + path, json=payload, headers={"Idempotency-Key": "inactive"}
            )
            assert response.status_code == 404, (state, method, path, response.text)
