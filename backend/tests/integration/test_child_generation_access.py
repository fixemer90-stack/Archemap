"""HTTP paid-access and server-owned lineage regression coverage.

Uses the shared destructive schema fixture: run only with an explicit disposable
PostgreSQL TEST_DATABASE_URL, never against an application database.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.main import app
from app.modules.authorization.service import EntitlementsService
from app.modules.child import models
from app.modules.child.repository import ChildRepository
from tests.integration.test_child_generation_lifecycle import (
    NOW,
    _grant_direct_child_access,
    _grant_plus_access,
    _seed_lifecycle,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.usefixtures("_setup_database")]

ARTIFACT_MODELS = (
    models.ChildGeneration,
    models.ChildGenerationEvent,
    models.ChildReport,
    models.ChildSegmentGeneration,
    models.ChildReportAssembly,
    models.ChildParentStyleScore,
    models.ChildNeedScore,
    models.ChildInteractionScore,
    models.ChildContextResolution,
    models.ChildGuidanceFacts,
)


@pytest.fixture
def dispatched(monkeypatch: pytest.MonkeyPatch) -> list[UUID]:
    calls: list[UUID] = []
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    monkeypatch.setattr(
        "app.modules.child.router.EntitlementsService",
        lambda db: EntitlementsService(db, now=lambda: NOW),
    )

    def dispatch(*, generation_id: UUID) -> str:
        calls.append(generation_id)
        return f"child-generation-{generation_id}"

    monkeypatch.setattr("app.modules.child.router.dispatch_child_generation", dispatch)

    def forbidden_provider() -> None:
        pytest.fail("HTTP acceptance must not construct or invoke a narrative provider")

    monkeypatch.setattr("app.modules.child.service.configured_child_provider", forbidden_provider)
    return calls


async def assert_no_artifacts(db: AsyncSession, dispatched: list[UUID]) -> None:
    assert dispatched == []
    for model in ARTIFACT_MODELS:
        assert await db.scalar(select(func.count()).select_from(model)) == 0, model.__tablename__


@pytest.mark.parametrize(
    "grant",
    ["free", "display_plus", "unrelated", "expired", "inactive", "future", "subscription_backed_child"],
)
async def test_http_paid_gate_rejects_non_authorizing_grants_without_side_effects(
    db_session: AsyncSession,
    client: AsyncClient,
    dispatched: list[UUID],
    grant: str,
) -> None:
    seed = await _seed_lifecycle(db_session)
    if grant == "display_plus":
        from app.modules.users.models import User

        owner = await db_session.get(User, seed.owner_id)
        assert owner is not None
        owner.account_tier = "plus"
        await db_session.commit()
    elif grant not in {"free", "display_plus"}:
        await _grant_direct_child_access(
            db_session,
            user_id=seed.owner_id,
            product="career" if grant == "unrelated" else "child",
            status="inactive" if grant == "inactive" else "active",
            starts_at=NOW + timedelta(days=1) if grant == "future" else NOW - timedelta(days=1),
            expires_at=NOW - timedelta(seconds=1) if grant == "expired" else NOW + timedelta(days=30),
        )
        if grant == "subscription_backed_child":
            from app.modules.authorization.models import Entitlement

            entitlement = await db_session.scalar(select(Entitlement))
            assert entitlement is not None
            entitlement.metadata_json = {"subscription_id": str(uuid4())}
            await db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    response = await client.post(
        "/api/v1/child/reports",
        headers={"Idempotency-Key": f"denied-{grant}"},
        json={"child_profile_id": str(seed.child_id), "questionnaire_session_id": str(seed.questionnaire_id)},
    )
    assert response.status_code == 402
    assert response.json() == {
        "detail": {
            "access_state": "locked",
            "report_type": "child",
            "required_level": "plus",
            "reason": "plus_required",
            "upgrade_url": "/billing",
        }
    }
    await assert_no_artifacts(db_session, dispatched)


@pytest.mark.parametrize("grant", ["plus", "child"])
async def test_http_paid_gate_accepts_canonical_access_and_pins_server_lineage(
    db_session: AsyncSession,
    client: AsyncClient,
    dispatched: list[UUID],
    grant: str,
) -> None:
    seed = await _seed_lifecycle(db_session)
    if grant == "plus":
        await _grant_plus_access(db_session, user_id=seed.owner_id)
    else:
        await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    response = await client.post(
        "/api/v1/child/reports",
        headers={"Idempotency-Key": "allowed"},
        json={"child_profile_id": str(seed.child_id), "questionnaire_session_id": str(seed.questionnaire_id)},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["report_id"] is None
    generation = await db_session.scalar(select(models.ChildGeneration))
    assert generation is not None
    assert dispatched == [generation.generation_id]
    assert generation.generation_id == UUID(response.json()["generation_id"])
    assert generation.owner_user_id == seed.owner_id
    assert generation.parent_chart_id == seed.parent_chart_id
    assert generation.child_chart_version_id == seed.child_chart_id
    assert generation.questionnaire_session_id == seed.questionnaire_id
    for model in ARTIFACT_MODELS[2:]:
        assert await db_session.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize(
    "target",
    [
        "foreign",
        "missing",
        "archived",
        "deletion_pending",
        "foreign_questionnaire",
        "draft_questionnaire",
        "missing_parent_chart",
        "missing_child_chart",
        "stale_questionnaire",
        "chart_confidence_mismatch",
    ],
)
async def test_http_unavailable_lineage_is_private_and_never_dispatches(
    db_session: AsyncSession,
    client: AsyncClient,
    dispatched: list[UUID],
    target: str,
) -> None:
    seed = await _seed_lifecycle(db_session)
    other = await _seed_lifecycle(db_session)
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    child_id, questionnaire_id = seed.child_id, seed.questionnaire_id
    if target == "foreign":
        child_id, questionnaire_id = other.child_id, other.questionnaire_id
    elif target == "missing":
        child_id = uuid4()
    elif target in {"archived", "deletion_pending"}:
        child = await db_session.get(models.ChildProfile, seed.child_id)
        assert child is not None
        child.status = target
    elif target == "foreign_questionnaire":
        questionnaire_id = other.questionnaire_id
    elif target == "draft_questionnaire":
        questionnaire = await db_session.get(models.ChildQuestionnaireSession, questionnaire_id)
        assert questionnaire is not None
        draft = models.ChildQuestionnaireSession(
            owner_user_id=seed.owner_id,
            child_profile_id=seed.child_id,
            age_snapshot_id=questionnaire.age_snapshot_id,
            status="draft",
            selected_question_keys=[],
            questionnaire_version="draft-questionnaire-v1",
            answer_version=questionnaire.answer_version,
            context_version=questionnaire.context_version,
            consent_version=questionnaire.consent_version,
        )
        db_session.add(draft)
        await db_session.flush()
        questionnaire_id = draft.id
    elif target == "missing_parent_chart":
        from app.modules.astrotype_v2.models import NatalChart

        chart = await db_session.get(NatalChart, seed.parent_chart_id)
        assert chart is not None
        await db_session.delete(chart)
    elif target == "missing_child_chart":
        # Infrastructure-loss fixture: normal ORM deletion is correctly forbidden.
        await db_session.execute(
            delete(models.ChildChartVersion).where(models.ChildChartVersion.id == seed.child_chart_id)
        )
    elif target == "chart_confidence_mismatch":
        # An obsolete chart must not be used after the child's source confidence changes.
        from datetime import time

        child = await db_session.get(models.ChildProfile, seed.child_id)
        assert child is not None
        child.birth_time_confidence = "exact"
        child.birth_time = time(12)
        child.version += 1
    elif target == "stale_questionnaire":
        await ChildRepository(db_session).create_age_snapshot_idempotently(
            owner_user_id=seed.owner_id,
            child_profile_id=seed.child_id,
            now=datetime.now(UTC) + timedelta(days=1),
        )
    await db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    response = await client.post(
        "/api/v1/child/reports",
        headers={"Idempotency-Key": "unavailable"},
        json={"child_profile_id": str(child_id), "questionnaire_session_id": str(questionnaire_id)},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Child resource not found"}
    await assert_no_artifacts(db_session, dispatched)


@pytest.mark.parametrize(
    "field", ["parent_chart_id", "child_chart_version_id", "owner_user_id", "age_snapshot_id", "operation_payload"]
)
async def test_http_request_rejects_client_owned_lineage_fields_before_writes(
    db_session: AsyncSession,
    client: AsyncClient,
    dispatched: list[UUID],
    field: str,
) -> None:
    seed = await _seed_lifecycle(db_session)
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    response = await client.post(
        "/api/v1/child/reports",
        headers={"Idempotency-Key": "injected-lineage"},
        json={
            "child_profile_id": str(seed.child_id),
            "questionnaire_session_id": str(seed.questionnaire_id),
            field: str(uuid4()),
        },
    )
    assert response.status_code == 422
    assert any(
        error["type"] == "extra_forbidden" and error["loc"] == ["body", "unknown_field"]
        for error in response.json()["detail"]
    )
    await assert_no_artifacts(db_session, dispatched)
