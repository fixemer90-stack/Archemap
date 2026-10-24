from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.dependencies import get_current_user
from app.main import app
from app.modules.astrotype_v2.models import NatalChart
from app.modules.authorization.models import Entitlement
from app.modules.child import models
from app.modules.child.narrative import ChildSectionRenderInput, MockChildSegmentProvider
from app.modules.child.questionnaire import AnswerInput, questions_for_age_stage
from app.modules.child.questionnaire_persistence import ChildQuestionnaireRepository
from app.modules.child.repository import ChildLineageMismatchError, ChildRepository
from app.modules.child.service import (
    accept_age_update_generation,
    accept_full_generation,
    accept_narrative_retry_generation,
    list_queued_generation_ids,
    run_claimed_age_update,
    run_claimed_full_generation,
    run_claimed_narrative_retry,
)
from app.modules.child.status import (
    ChildGenerationOperation,
    ChildGenerationStatus,
)
from app.modules.payments.models import Payment
from app.modules.profiles.models import PersonProfile
from app.modules.subscriptions.models import Subscription, SubscriptionPlan
from app.modules.users.models import User
from tests.integration.test_child_interaction import _persist_interaction

pytestmark = pytest.mark.usefixtures("_setup_database")
NOW = datetime(2026, 10, 23, 12, tzinfo=UTC)


@dataclass(frozen=True)
class LifecycleSeed:
    owner_id: UUID
    child_id: UUID
    parent_chart_id: UUID
    child_chart_id: UUID
    questionnaire_id: UUID


class CountingProvider(MockChildSegmentProvider):
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.section_keys: list[str] = []
        self.fail = fail

    async def generate_segment(
        self,
        *,
        prompt: str,
        section_input: ChildSectionRenderInput,
    ) -> dict[str, Any]:
        self.calls += 1
        self.section_keys.append(section_input.section_key)
        if self.fail:
            raise RuntimeError("provider detail must not be persisted")
        return await super().generate_segment(prompt=prompt, section_input=section_input)


class SelectiveProvider(CountingProvider):
    def __init__(self, *, failed_sections: set[str]) -> None:
        super().__init__()
        self.failed_sections = failed_sections

    async def generate_segment(
        self,
        *,
        prompt: str,
        section_input: ChildSectionRenderInput,
    ) -> dict[str, Any]:
        self.calls += 1
        self.section_keys.append(section_input.section_key)
        if section_input.section_key in self.failed_sections:
            payload = await MockChildSegmentProvider.generate_segment(
                self,
                prompt=prompt,
                section_input=section_input,
            )
            return payload | {"section_key": "invalid-section"}
        return await MockChildSegmentProvider.generate_segment(
            self,
            prompt=prompt,
            section_input=section_input,
        )


async def _seed_claimable_full_pipeline(
    db: AsyncSession,
    *,
    idempotency_key: str,
) -> tuple[LifecycleSeed, models.ChildGeneration]:
    owner, child, generation, _ = await _persist_interaction(db)
    age = models.ChildAgeSnapshot(
        child_profile_id=child.id,
        as_of_date=NOW.date(),
        age_years=5,
        age_months=5,
        age_days=0,
        age_stage="3-6",
        age_rules_version="child-age-mvp-1",
        input_hash="l" * 64,
    )
    db.add(age)
    await db.flush()
    questionnaire_repository = ChildQuestionnaireRepository(db)
    draft = await questionnaire_repository.get_or_create_current_draft(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        age_snapshot_id=age.id,
    )
    await questionnaire_repository.save_draft_answers(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        questionnaire_session_id=draft.session.id,
        answers=tuple(
            AnswerInput(question_key=question.key, option=question.options[0].code)
            for question in questions_for_age_stage("3-6")
        ),
    )
    questionnaire = (
        await questionnaire_repository.complete_idempotently(
            owner_user_id=owner.id,
            child_profile_id=child.id,
            questionnaire_session_id=draft.session.id,
            completion_idempotency_key=f"complete-{idempotency_key}",
        )
    ).session
    generation.operation = ChildGenerationOperation.FULL_REPORT.value
    generation.idempotency_key = idempotency_key
    generation.status = ChildGenerationStatus.QUEUED.value
    generation.questionnaire_session_id = questionnaire.id
    generation.attempt_count = 0
    generation.claim_token = None
    generation.lease_expires_at = None
    await db.commit()
    return (
        LifecycleSeed(
            owner.id,
            child.id,
            generation.parent_chart_id,
            generation.child_chart_version_id,
            questionnaire.id,
        ),
        generation,
    )


async def _seed_lifecycle(db: AsyncSession) -> LifecycleSeed:
    owner = User(
        email=f"child-lifecycle-{uuid4()}@example.com",
        name="Parent",
        hashed_password="test-only-hash",  # noqa: S106
        is_active=True,
        is_verified=True,
    )
    db.add(owner)
    await db.flush()
    parent = PersonProfile(
        user_id=owner.id,
        name="Parent",
        birth_date=date(1990, 1, 1),
        birth_time=None,
        birth_time_accuracy="unknown",
        birth_place="Москва",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
    )
    db.add(parent)
    await db.flush()
    parent_chart = NatalChart(
        user_id=owner.id,
        profile_id=parent.id,
        engine_version="test-v1",
        input_hash="p" * 64,
        birth_datetime_utc=datetime(1990, 1, 1, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.7558,
        longitude=37.6173,
        house_system="P",
        calculation_payload={},
    )
    child = models.ChildProfile(
        owner_user_id=owner.id,
        parent_profile_id=parent.id,
        display_name="Ребёнок",
        relationship_type="child",
        child_gender=None,
        birth_date=date(2020, 6, 1),
        birth_time=None,
        birth_time_confidence="unknown",
        birth_place="Москва",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
        caregiver_context={},
        birth_data_hash="c" * 64,
        idempotency_key=f"child-{uuid4()}",
        status="active",
        version=1,
    )
    db.add_all([parent_chart, child])
    await db.flush()
    chart = models.ChildChartVersion(
        child_profile_id=child.id,
        version=1,
        engine_version="test-v1",
        input_hash="d" * 64,
        birth_time_confidence="unknown",
        allowed_fact_families=[],
        excluded_fact_families=["houses"],
        uncertainty_reason="unknown_birth_time",
        calculation_payload={},
    )
    db.add(chart)
    await db.flush()
    age = models.ChildAgeSnapshot(
        child_profile_id=child.id,
        as_of_date=date(2026, 10, 23),
        age_years=6,
        age_months=4,
        age_days=22,
        age_stage="middle_childhood",
        age_rules_version="age-rules-v1",
        input_hash="a" * 64,
    )
    db.add(age)
    await db.flush()
    questionnaire = models.ChildQuestionnaireSession(
        owner_user_id=owner.id,
        child_profile_id=child.id,
        age_snapshot_id=age.id,
        status="completed",
        selected_question_keys=[],
        questionnaire_version="test-questionnaire-v1",
        answer_version="test-answer-v1",
        context_version="test-context-v1",
        consent_version="test-consent-v1",
        completion_idempotency_key=f"complete-{uuid4()}",
        answers_hash="q" * 64,
        completed_at=NOW,
    )
    db.add(questionnaire)
    await db.commit()
    return LifecycleSeed(owner.id, child.id, parent_chart.id, chart.id, questionnaire.id)


async def _grant_direct_child_access(
    db: AsyncSession,
    *,
    user_id: UUID,
    product: str = "child",
    status: str = "active",
    starts_at: datetime = NOW - timedelta(days=1),
    expires_at: datetime | None = NOW + timedelta(days=30),
) -> None:
    payment = Payment(
        user_id=user_id,
        provider="test",
        amount=1.0,
        currency="RUB",
        status="succeeded",
        description="Child access test",
    )
    db.add(payment)
    await db.flush()
    db.add(
        Entitlement(
            user_id=user_id,
            product=product,
            status=status,
            source_payment_id=payment.id,
            starts_at=starts_at,
            expires_at=expires_at,
            metadata_json={},
        )
    )
    await db.commit()


async def _grant_plus_access(db: AsyncSession, *, user_id: UUID) -> None:
    plan = SubscriptionPlan(
        plan_code="astrotype_plus_monthly",
        display_name="Astrotype Plus",
        amount=1.0,
        currency="RUB",
        billing_interval="month",
        interval_count=1,
        is_active=True,
        features_json={},
    )
    db.add(plan)
    await db.flush()
    payment = Payment(
        user_id=user_id,
        provider="test",
        amount=1.0,
        currency="RUB",
        status="succeeded",
        description="Plus access test",
    )
    db.add(payment)
    await db.flush()
    subscription = Subscription(
        user_id=user_id,
        plan_id=plan.id,
        provider="test",
        status="active",
        current_period_start=NOW - timedelta(days=1),
        current_period_end=NOW + timedelta(days=30),
        latest_payment_id=payment.id,
        metadata_json={},
    )
    db.add(subscription)
    await db.flush()
    db.add(
        Entitlement(
            user_id=user_id,
            product="self",
            status="active",
            source_payment_id=payment.id,
            starts_at=NOW - timedelta(days=1),
            expires_at=NOW + timedelta(days=30),
            metadata_json={"subscription_id": str(subscription.id)},
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_accept_generation_returns_queued_id_without_running_pipeline_inline(
    db_session: AsyncSession,
) -> None:
    seed = await _seed_lifecycle(db_session)
    dispatched: list[UUID] = []

    def dispatch(*, generation_id: UUID) -> str:
        dispatched.append(generation_id)
        return f"child-generation-{generation_id}"

    result = await accept_full_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        questionnaire_session_id=seed.questionnaire_id,
        idempotency_key="full-report-one",
        dispatcher=dispatch,
    )

    assert result.status == ChildGenerationStatus.QUEUED.value
    assert result.report_id is None
    assert result.created is True
    assert dispatched == [result.generation_id]
    assert await db_session.scalar(select(func.count()).select_from(models.ChildReport)) == 0
    assert await db_session.scalar(select(func.count()).select_from(models.ChildSegmentGeneration)) == 0


@pytest.mark.asyncio
async def test_http_create_returns_202_generation_without_inline_artifacts(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = await _seed_lifecycle(db_session)
    await _grant_direct_child_access(db_session, user_id=seed.owner_id)
    dispatched: list[UUID] = []

    def dispatch(*, generation_id: UUID) -> str:
        dispatched.append(generation_id)
        return f"child-generation-{generation_id}"

    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    monkeypatch.setattr("app.modules.child.router.dispatch_child_generation", dispatch)

    response = await client.post(
        "/api/v1/child/reports",
        headers={"Idempotency-Key": "http-full-report"},
        json={
            "child_profile_id": str(seed.child_id),
            "questionnaire_session_id": str(seed.questionnaire_id),
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == ChildGenerationStatus.QUEUED.value
    assert body["report_id"] is None
    assert dispatched == [UUID(body["generation_id"])]
    assert await db_session.scalar(select(func.count()).select_from(models.ChildReport)) == 0
    assert await db_session.scalar(select(func.count()).select_from(models.ChildSegmentGeneration)) == 0


@pytest.mark.asyncio
async def test_http_create_denies_free_user_before_any_generation_or_dispatch(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = await _seed_lifecycle(db_session)
    dispatched: list[UUID] = []
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)

    def dispatch(*, generation_id: UUID) -> str:
        dispatched.append(generation_id)
        return f"child-generation-{generation_id}"

    monkeypatch.setattr("app.modules.child.router.dispatch_child_generation", dispatch)

    response = await client.post(
        "/api/v1/child/reports",
        headers={"Idempotency-Key": "free-user-denied"},
        json={
            "child_profile_id": str(seed.child_id),
            "questionnaire_session_id": str(seed.questionnaire_id),
        },
    )

    assert response.status_code == 402
    assert response.json()["detail"] == {
        "access_state": "locked",
        "report_type": "child",
        "required_level": "plus",
        "reason": "plus_required",
        "upgrade_url": "/billing",
    }
    assert dispatched == []
    assert await db_session.scalar(select(func.count()).select_from(models.ChildGeneration)) == 0
    assert await db_session.scalar(select(func.count()).select_from(models.ChildGenerationEvent)) == 0


@pytest.mark.asyncio
async def test_http_create_allows_active_plus_access(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = await _seed_lifecycle(db_session)
    await _grant_plus_access(db_session, user_id=seed.owner_id)
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)
    monkeypatch.setattr(
        "app.modules.child.router.dispatch_child_generation",
        lambda *, generation_id: f"child-generation-{generation_id}",
    )

    response = await client.post(
        "/api/v1/child/reports",
        headers={"Idempotency-Key": "plus-user-allowed"},
        json={"child_profile_id": str(seed.child_id), "questionnaire_session_id": str(seed.questionnaire_id)},
    )

    assert response.status_code == 202
    assert response.json()["status"] == ChildGenerationStatus.QUEUED.value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("product", "entitlement_status", "expires_at"),
    [
        ("career", "active", NOW + timedelta(days=30)),
        ("child", "inactive", NOW + timedelta(days=30)),
        ("child", "active", NOW - timedelta(seconds=1)),
    ],
)
async def test_http_create_rejects_unrelated_inactive_or_expired_direct_grants(
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    product: str,
    entitlement_status: str,
    expires_at: datetime,
) -> None:
    seed = await _seed_lifecycle(db_session)
    await _grant_direct_child_access(
        db_session,
        user_id=seed.owner_id,
        product=product,
        status=entitlement_status,
        expires_at=expires_at,
    )
    app.dependency_overrides[get_current_user] = lambda: seed.owner_id
    monkeypatch.setattr("app.modules.child.router.settings.CHILD_REPORT_ENABLED", True)

    response = await client.post(
        "/api/v1/child/reports",
        headers={"Idempotency-Key": f"denied-{product}-{entitlement_status}"},
        json={"child_profile_id": str(seed.child_id), "questionnaire_session_id": str(seed.questionnaire_id)},
    )

    assert response.status_code == 402
    assert await db_session.scalar(select(func.count()).select_from(models.ChildGeneration)) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("child_status", ["archived", "deletion_pending"])
async def test_generation_acceptance_rejects_non_active_child_without_graph_mutation(
    db_session: AsyncSession,
    child_status: str,
) -> None:
    seed = await _seed_lifecycle(db_session)
    child = await db_session.get(models.ChildProfile, seed.child_id)
    assert child is not None
    child.status = child_status
    await db_session.commit()

    with pytest.raises(ChildLineageMismatchError):
        await accept_full_generation(
            db_session,
            owner_user_id=seed.owner_id,
            child_profile_id=seed.child_id,
            questionnaire_session_id=seed.questionnaire_id,
            idempotency_key=f"non-active-{child_status}",
            dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
        )
    await db_session.commit()

    assert await db_session.scalar(select(func.count()).select_from(models.ChildGeneration)) == 0
    assert await db_session.scalar(select(func.count()).select_from(models.ChildGenerationEvent)) == 0


@pytest.mark.asyncio
async def test_generation_acceptance_rejects_stale_questionnaire_age_lineage_before_write(
    db_session: AsyncSession,
) -> None:
    seed = await _seed_lifecycle(db_session)
    db_session.add(
        models.ChildAgeSnapshot(
            child_profile_id=seed.child_id,
            as_of_date=NOW.date() + timedelta(days=1),
            age_years=6,
            age_months=4,
            age_days=23,
            age_stage="middle_childhood",
            age_rules_version="age-rules-v1",
            input_hash="z" * 64,
        )
    )
    await db_session.commit()

    with pytest.raises(ChildLineageMismatchError):
        await accept_full_generation(
            db_session,
            owner_user_id=seed.owner_id,
            child_profile_id=seed.child_id,
            questionnaire_session_id=seed.questionnaire_id,
            idempotency_key="stale-questionnaire",
            dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
        )
    await db_session.commit()

    assert await db_session.scalar(select(func.count()).select_from(models.ChildGeneration)) == 0
    assert await db_session.scalar(select(func.count()).select_from(models.ChildGenerationEvent)) == 0


@pytest.mark.asyncio
async def test_accept_generation_replay_dispatches_once(db_session: AsyncSession) -> None:
    seed = await _seed_lifecycle(db_session)
    dispatched: list[UUID] = []

    def dispatch(*, generation_id: UUID) -> str:
        dispatched.append(generation_id)
        return f"child-generation-{generation_id}"

    first = await accept_full_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        questionnaire_session_id=seed.questionnaire_id,
        idempotency_key="full-report-replay",
        dispatcher=dispatch,
    )
    second = await accept_full_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        questionnaire_session_id=seed.questionnaire_id,
        idempotency_key="full-report-replay",
        dispatcher=dispatch,
    )

    assert first.generation_id == second.generation_id
    assert (first.created, second.created) == (True, False)
    assert dispatched == [first.generation_id]
    assert await db_session.scalar(select(func.count()).select_from(models.ChildGeneration)) == 1


@pytest.mark.asyncio
async def test_concurrent_worker_claim_is_single_winner(db_session: AsyncSession) -> None:
    seed = await _seed_lifecycle(db_session)
    generation = await ChildRepository(db_session).create_generation_idempotently(
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        parent_chart_id=seed.parent_chart_id,
        child_chart_version_id=seed.child_chart_id,
        questionnaire_session_id=seed.questionnaire_id,
        operation="full_report",
        idempotency_key="claim-race",
    )
    await db_session.commit()
    assert isinstance(db_session.bind, AsyncEngine)
    factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)

    async def claim(task_id: str) -> bool:
        async with factory() as session:
            result = await ChildRepository(session).claim_generation(
                generation_id=generation.generation.generation_id,
                task_id=task_id,
                now=NOW,
                lease_duration=timedelta(minutes=5),
            )
            await session.commit()
            return result is not None

    winners = await asyncio.gather(claim("worker-a"), claim("worker-b"))
    assert sorted(winners) == [False, True]
    persisted = await db_session.scalar(
        select(models.ChildGeneration)
        .where(models.ChildGeneration.generation_id == generation.generation.generation_id)
        .execution_options(populate_existing=True)
    )
    assert persisted is not None
    assert persisted.attempt_count == 1
    assert persisted.status == ChildGenerationStatus.CALCULATING_PAIR.value


@pytest.mark.asyncio
async def test_concurrent_age_update_claim_is_single_winner(db_session: AsyncSession) -> None:
    seed = await _seed_lifecycle(db_session)
    generation = await ChildRepository(db_session).create_generation_idempotently(
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        parent_chart_id=seed.parent_chart_id,
        child_chart_version_id=seed.child_chart_id,
        questionnaire_session_id=seed.questionnaire_id,
        operation=ChildGenerationOperation.AGE_UPDATE.value,
        idempotency_key="age-claim-race",
    )
    await db_session.commit()
    assert isinstance(db_session.bind, AsyncEngine)
    factory = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)

    async def claim(task_id: str) -> bool:
        async with factory() as session:
            result = await ChildRepository(session).claim_generation(
                generation_id=generation.generation.generation_id,
                task_id=task_id,
                now=NOW,
                lease_duration=timedelta(minutes=5),
            )
            await session.commit()
            return result is not None

    winners = await asyncio.gather(claim("age-worker-a"), claim("age-worker-b"))
    assert sorted(winners) == [False, True]
    persisted = await db_session.scalar(
        select(models.ChildGeneration)
        .where(models.ChildGeneration.generation_id == generation.generation.generation_id)
        .execution_options(populate_existing=True)
    )
    assert persisted is not None
    assert persisted.attempt_count == 1
    assert persisted.status == ChildGenerationStatus.AGE_UPDATE_RUNNING.value


@pytest.mark.asyncio
async def test_reconciliation_does_not_redispatch_actively_leased_age_worker(
    db_session: AsyncSession,
) -> None:
    seed = await _seed_lifecycle(db_session)
    repository = ChildRepository(db_session)
    created = await repository.create_generation_idempotently(
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        parent_chart_id=seed.parent_chart_id,
        child_chart_version_id=seed.child_chart_id,
        questionnaire_session_id=seed.questionnaire_id,
        operation=ChildGenerationOperation.AGE_UPDATE.value,
        idempotency_key="active-age-lease",
    )
    await db_session.commit()
    claim = await repository.claim_generation(
        generation_id=created.generation.generation_id,
        task_id="active-age-worker",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await db_session.commit()

    reconciled = await repository.reconcile_stuck_generations(
        now=NOW + timedelta(minutes=4),
        max_attempts=3,
    )
    await db_session.commit()

    assert reconciled.requeued_generation_ids == ()
    assert reconciled.terminal_generation_ids == ()
    persisted = await db_session.scalar(
        select(models.ChildGeneration)
        .where(models.ChildGeneration.generation_id == created.generation.generation_id)
        .execution_options(populate_existing=True)
    )
    assert persisted is not None
    assert persisted.status == ChildGenerationStatus.AGE_UPDATE_RUNNING.value
    assert persisted.claim_token == claim.claim_token
    assert created.generation.generation_id not in await list_queued_generation_ids(
        db_session,
        now=NOW + timedelta(minutes=4),
    )


@pytest.mark.asyncio
async def test_post_report_failure_preserves_deterministic_report(db_session: AsyncSession) -> None:
    seed = await _seed_lifecycle(db_session)
    repository = ChildRepository(db_session)
    created = await repository.create_generation_idempotently(
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        parent_chart_id=seed.parent_chart_id,
        child_chart_version_id=seed.child_chart_id,
        questionnaire_session_id=seed.questionnaire_id,
        operation="full_report",
        idempotency_key="provider-failure",
    )
    await db_session.commit()
    claim = await repository.claim_generation(
        generation_id=created.generation.generation_id,
        task_id="worker-provider-failure",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    report = await repository.create_report_idempotently(
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        generation_id=created.generation.generation_id,
        parent_chart_id=seed.parent_chart_id,
        child_chart_version_id=seed.child_chart_id,
        idempotency_key="deterministic-report",
        version=1,
        status="deterministic_ready",
        scoring_version="test-score-v1",
        reference_version="test-reference-v1",
        questionnaire_version="test-questionnaire-v1",
        prompt_version="child-section-prompt-v1",
        report_payload={"status": "deterministic_ready", "safe": True},
        presentation_manifest={"section_order": []},
    )
    await repository.transition_generation(
        generation_id=created.generation.generation_id,
        claim_token=claim.claim_token,
        expected_status=ChildGenerationStatus.CALCULATING_PAIR,
        target_status=ChildGenerationStatus.DETERMINISTIC_READY,
        now=NOW,
        report_id=report.report.id,
    )
    await db_session.commit()
    await repository.fail_claimed_generation(
        generation_id=created.generation.generation_id,
        claim_token=claim.claim_token,
        now=NOW + timedelta(seconds=1),
        error_code="child_narrative_provider_failure",
    )
    await db_session.commit()

    generation = await db_session.scalar(
        select(models.ChildGeneration)
        .where(models.ChildGeneration.generation_id == created.generation.generation_id)
        .execution_options(populate_existing=True)
    )
    persisted_report = await db_session.get(models.ChildReport, report.report.id)
    assert generation is not None
    assert generation.status == ChildGenerationStatus.NARRATIVE_FAILED.value
    assert generation.report_id == report.report.id
    assert persisted_report is not None
    assert persisted_report.status == "deterministic_ready"
    assert persisted_report.report_payload == {"status": "deterministic_ready", "safe": True}


@pytest.mark.asyncio
async def test_stuck_reconciliation_requeues_then_exhausts_by_publication_stage(
    db_session: AsyncSession,
) -> None:
    seed = await _seed_lifecycle(db_session)
    repository = ChildRepository(db_session)
    pre_report = models.ChildGeneration(
        child_profile_id=seed.child_id,
        owner_user_id=seed.owner_id,
        parent_chart_id=seed.parent_chart_id,
        child_chart_version_id=seed.child_chart_id,
        questionnaire_session_id=seed.questionnaire_id,
        generation_id=uuid4(),
        operation="full_report",
        idempotency_key="stuck-pre",
        status="calculating_pair",
        attempt_count=1,
        claim_token=uuid4(),
        lease_expires_at=NOW - timedelta(seconds=1),
        diagnostics={},
    )
    post_report = models.ChildGeneration(
        child_profile_id=seed.child_id,
        owner_user_id=seed.owner_id,
        parent_chart_id=seed.parent_chart_id,
        child_chart_version_id=seed.child_chart_id,
        questionnaire_session_id=seed.questionnaire_id,
        generation_id=uuid4(),
        operation="full_report",
        idempotency_key="stuck-post",
        status="generating_sections",
        report_id=uuid4(),
        attempt_count=3,
        claim_token=uuid4(),
        lease_expires_at=NOW - timedelta(seconds=1),
        diagnostics={},
    )
    db_session.add_all([pre_report, post_report])
    await db_session.commit()

    result = await repository.reconcile_stuck_generations(now=NOW, max_attempts=3)
    await db_session.commit()
    assert result.requeued_generation_ids == (pre_report.generation_id,)
    assert result.terminal_generation_ids == (post_report.generation_id,)
    await db_session.refresh(pre_report)
    await db_session.refresh(post_report)
    assert pre_report.status == ChildGenerationStatus.QUEUED.value
    assert pre_report.celery_task_id is None
    assert post_report.status == ChildGenerationStatus.NARRATIVE_FAILED.value
    assert post_report.report_id is not None


@pytest.mark.asyncio
async def test_full_worker_path_persists_final_assembly_and_redelivery_calls_provider_once(
    db_session: AsyncSession,
) -> None:
    _, generation = await _seed_claimable_full_pipeline(
        db_session,
        idempotency_key="full-worker-ready",
    )
    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=generation.generation_id,
        task_id="worker-ready",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await db_session.commit()
    provider = CountingProvider()

    result = await run_claimed_full_generation(
        db_session,
        claim=claim,
        provider=provider,
        now=NOW,
    )

    assert result.status == ChildGenerationStatus.READY.value
    assert result.report_id is not None
    assert provider.calls == len(provider.section_keys) > 0
    assert len(provider.section_keys) == len(set(provider.section_keys))
    assembly = await db_session.scalar(
        select(models.ChildReportAssembly).where(models.ChildReportAssembly.generation_id == generation.generation_id)
    )
    assert assembly is not None
    assert assembly.status == "ready"
    assert assembly.payload["status"] == "ready"

    redelivery = await repository.claim_generation(
        generation_id=generation.generation_id,
        task_id="worker-redelivery",
        now=NOW + timedelta(minutes=1),
        lease_duration=timedelta(minutes=5),
    )
    assert redelivery is None
    assert provider.calls == len(provider.section_keys)


@pytest.mark.asyncio
async def test_actual_provider_failure_preserves_deterministic_report_and_safe_diagnostics(
    db_session: AsyncSession,
) -> None:
    _, generation = await _seed_claimable_full_pipeline(
        db_session,
        idempotency_key="full-worker-provider-failure",
    )
    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=generation.generation_id,
        task_id="worker-provider-failure",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await db_session.commit()
    provider = CountingProvider(fail=True)

    result = await run_claimed_full_generation(
        db_session,
        claim=claim,
        provider=provider,
        now=NOW,
    )

    assert result.status == ChildGenerationStatus.NARRATIVE_RETRY_WAITING.value
    assert result.report_id is not None
    report = await db_session.get(models.ChildReport, result.report_id)
    assert report is not None
    assert report.status == ChildGenerationStatus.DETERMINISTIC_READY.value
    assembly = await db_session.scalar(
        select(models.ChildReportAssembly).where(models.ChildReportAssembly.generation_id == generation.generation_id)
    )
    assert assembly is None
    retry_waiting_rows = tuple(
        (
            await db_session.scalars(
                select(models.ChildSegmentGeneration).where(
                    models.ChildSegmentGeneration.generation_id == generation.generation_id,
                    models.ChildSegmentGeneration.status == "retry_waiting",
                )
            )
        ).all()
    )
    assert len(retry_waiting_rows) == 1
    assert retry_waiting_rows[0].error_code == "child_narrative_provider_failure"
    assert "provider detail" not in str(retry_waiting_rows[0].diagnostics)
    assert generation.generation_id not in await list_queued_generation_ids(
        db_session,
        now=NOW + timedelta(seconds=29),
    )

    recovered_claim = await repository.claim_generation(
        generation_id=generation.generation_id,
        task_id="worker-provider-recovered",
        now=NOW + timedelta(seconds=30),
        lease_duration=timedelta(minutes=5),
    )
    assert recovered_claim is not None
    await db_session.commit()
    recovered = await run_claimed_full_generation(
        db_session,
        claim=recovered_claim,
        provider=CountingProvider(),
        now=NOW + timedelta(seconds=30),
    )
    assert recovered.status == ChildGenerationStatus.READY.value
    assembly = await db_session.scalar(
        select(models.ChildReportAssembly).where(models.ChildReportAssembly.generation_id == generation.generation_id)
    )
    assert assembly is not None
    assert assembly.status == "ready"


@pytest.mark.asyncio
async def test_provider_response_ambiguity_is_not_recalled_after_reclaim(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, generation = await _seed_claimable_full_pipeline(
        db_session,
        idempotency_key="full-worker-ambiguous-response",
    )
    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=generation.generation_id,
        task_id="worker-before-crash",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await db_session.commit()
    provider = CountingProvider()
    original_persist = ChildRepository.persist_terminal_segment
    crashed = False

    async def crash_once(
        self: ChildRepository,
        *,
        row: models.ChildSegmentGeneration,
        claim_token: UUID | None = None,
    ) -> models.ChildSegmentGeneration:
        nonlocal crashed
        if not crashed and row.status == "ready":
            crashed = True
            raise RuntimeError("crash after provider response")
        return await original_persist(self, row=row, claim_token=claim_token)

    monkeypatch.setattr(ChildRepository, "persist_terminal_segment", crash_once)
    first = await run_claimed_full_generation(
        db_session,
        claim=claim,
        provider=provider,
        now=NOW,
    )
    assert first.status == ChildGenerationStatus.NARRATIVE_RETRY_WAITING.value
    assert provider.calls == 1
    first_section = provider.section_keys[0]

    second_claim = await repository.claim_generation(
        generation_id=generation.generation_id,
        task_id="worker-after-crash",
        now=NOW + timedelta(seconds=31),
        lease_duration=timedelta(minutes=5),
    )
    assert second_claim is not None
    await db_session.commit()
    second = await run_claimed_full_generation(
        db_session,
        claim=second_claim,
        provider=provider,
        now=NOW + timedelta(seconds=31),
    )

    assert second.status == ChildGenerationStatus.NARRATIVE_FAILED.value
    assert provider.section_keys.count(first_section) == 1
    assert len(provider.section_keys) == len(set(provider.section_keys))
    ambiguous = await db_session.scalar(
        select(models.ChildSegmentGeneration).where(
            models.ChildSegmentGeneration.generation_id == generation.generation_id,
            models.ChildSegmentGeneration.section_key == first_section,
        )
    )
    assert ambiguous is not None
    assert ambiguous.status == "failed"
    assert ambiguous.error_code == "child_narrative_provider_outcome_unknown"


@pytest.mark.asyncio
async def test_expired_dispatch_and_retry_backoff_become_due_without_early_claim(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, generation = await _seed_claimable_full_pipeline(
        db_session,
        idempotency_key="full-worker-backoff",
    )
    generation.celery_task_id = "lost-task"
    generation.dispatched_at = NOW - timedelta(minutes=3)
    generation.dispatch_expires_at = NOW - timedelta(seconds=1)
    await db_session.commit()
    assert generation.generation_id in await list_queued_generation_ids(db_session, now=NOW)

    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=generation.generation_id,
        task_id="worker-transient-failure",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await db_session.commit()

    async def transient_failure(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise RuntimeError("temporary database dependency")

    monkeypatch.setattr(ChildRepository, "create_parent_style_profile", transient_failure)
    result = await run_claimed_full_generation(
        db_session,
        claim=claim,
        provider=CountingProvider(),
        now=NOW,
    )
    assert result.status == ChildGenerationStatus.QUEUED.value
    await db_session.refresh(generation)
    assert generation.next_retry_at == NOW + timedelta(seconds=30)
    assert (
        await repository.claim_generation(
            generation_id=generation.generation_id,
            task_id="worker-too-early",
            now=NOW + timedelta(seconds=29),
            lease_duration=timedelta(minutes=5),
        )
        is None
    )
    assert (
        await repository.claim_generation(
            generation_id=generation.generation_id,
            task_id="worker-due",
            now=NOW + timedelta(seconds=30),
            lease_duration=timedelta(minutes=5),
        )
        is not None
    )


@pytest.mark.asyncio
async def test_age_update_uses_separate_lifecycle_without_pair_or_provider_recalculation(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed, full_generation = await _seed_claimable_full_pipeline(
        db_session,
        idempotency_key="full-before-age-update",
    )
    repository = ChildRepository(db_session)
    full_claim = await repository.claim_generation(
        generation_id=full_generation.generation_id,
        task_id="worker-full-before-age",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert full_claim is not None
    await db_session.commit()
    provider = CountingProvider()
    full_result = await run_claimed_full_generation(
        db_session,
        claim=full_claim,
        provider=provider,
        now=NOW,
    )
    assert full_result.status == ChildGenerationStatus.READY.value
    assert full_result.report_id is not None
    provider_calls_before = provider.calls
    pair_counts_before = (
        await db_session.scalar(select(func.count()).select_from(models.ChildParentStyleScore)),
        await db_session.scalar(select(func.count()).select_from(models.ChildNeedScore)),
        await db_session.scalar(select(func.count()).select_from(models.ChildInteractionScore)),
    )

    dispatched: list[UUID] = []

    def dispatch(*, generation_id: UUID) -> str:
        dispatched.append(generation_id)
        return f"child-generation-{generation_id}"

    accepted = await accept_age_update_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        source_report_id=full_result.report_id,
        idempotency_key="age-update-one",
        guidance_rules_version="age-guidance-v1",
        payload={"actions": ["pause"]},
        dispatcher=dispatch,
        now=NOW,
    )
    assert accepted.status == ChildGenerationStatus.AGE_UPDATE_QUEUED.value
    assert dispatched == [accepted.generation_id]
    age_claim = await repository.claim_generation(
        generation_id=accepted.generation_id,
        task_id="worker-age-update",
        now=NOW + timedelta(minutes=1),
        lease_duration=timedelta(minutes=5),
    )
    assert age_claim is not None
    assert age_claim.generation.status == ChildGenerationStatus.AGE_UPDATE_RUNNING.value
    pinned_snapshot_id = UUID(str(age_claim.generation.operation_payload["age_snapshot_id"]))
    await db_session.commit()

    async def forbidden_pair_path(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("age update entered the pair pipeline")

    monkeypatch.setattr(ChildRepository, "create_parent_style_profile", forbidden_pair_path)
    monkeypatch.setattr(ChildRepository, "create_child_need_profile", forbidden_pair_path)
    monkeypatch.setattr(ChildRepository, "create_interaction_profile", forbidden_pair_path)
    age_result = await run_claimed_age_update(
        db_session,
        claim=age_claim,
        now=NOW + timedelta(days=400),
    )

    assert age_result.status == ChildGenerationStatus.AGE_UPDATE_READY.value
    assert provider.calls == provider_calls_before
    assert pair_counts_before == (
        await db_session.scalar(select(func.count()).select_from(models.ChildParentStyleScore)),
        await db_session.scalar(select(func.count()).select_from(models.ChildNeedScore)),
        await db_session.scalar(select(func.count()).select_from(models.ChildInteractionScore)),
    )
    guidance = await db_session.scalar(select(models.ChildReportAgeGuidance))
    assert guidance is not None
    assert guidance.age_snapshot_id == pinned_snapshot_id


@pytest.mark.asyncio
async def test_age_update_acceptance_pins_source_lineage_and_replay_reuses_snapshot(
    db_session: AsyncSession,
) -> None:
    seed, full_generation = await _seed_claimable_full_pipeline(
        db_session,
        idempotency_key="full-before-age-pin",
    )
    repository = ChildRepository(db_session)
    full_claim = await repository.claim_generation(
        generation_id=full_generation.generation_id,
        task_id="worker-full-before-age-pin",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert full_claim is not None
    await db_session.commit()
    full_result = await run_claimed_full_generation(
        db_session,
        claim=full_claim,
        provider=CountingProvider(),
        now=NOW,
    )
    assert full_result.report_id is not None

    def dispatch(*, generation_id: UUID) -> str:
        return f"child-generation-{generation_id}"

    first = await accept_age_update_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        source_report_id=full_result.report_id,
        idempotency_key="age-update-pinned-replay",
        guidance_rules_version="age-guidance-v1",
        payload={"actions": ["pause"]},
        dispatcher=dispatch,
        now=NOW,
    )
    snapshot_count = await db_session.scalar(select(func.count()).select_from(models.ChildAgeSnapshot))
    replay = await accept_age_update_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        source_report_id=full_result.report_id,
        idempotency_key="age-update-pinned-replay",
        guidance_rules_version="age-guidance-v1",
        payload={"actions": ["pause"]},
        dispatcher=dispatch,
        now=NOW + timedelta(days=400),
    )

    assert replay.generation_id == first.generation_id
    assert await db_session.scalar(select(func.count()).select_from(models.ChildAgeSnapshot)) == snapshot_count
    generation = await db_session.scalar(
        select(models.ChildGeneration).where(models.ChildGeneration.generation_id == first.generation_id)
    )
    assert generation is not None
    assert generation.operation_payload["source_generation_id"] == str(full_generation.generation_id)
    assert generation.operation_payload["source_report_id"] == str(full_result.report_id)
    assert generation.operation_payload["age_snapshot_id"]
    assert generation.operation_payload["age_input_hash"]
    assert generation.operation_payload["age_rules_version"]
    assert generation.operation_payload["guidance_rules_version"] == "age-guidance-v1"
    assert generation.operation_payload["guidance_input_hash"]


@pytest.mark.asyncio
async def test_narrative_retry_reuses_deterministic_artifacts_and_calls_only_failed_sections(
    db_session: AsyncSession,
) -> None:
    seed, source_generation = await _seed_claimable_full_pipeline(
        db_session,
        idempotency_key="full-before-narrative-retry",
    )
    repository = ChildRepository(db_session)
    source_claim = await repository.claim_generation(
        generation_id=source_generation.generation_id,
        task_id="worker-before-narrative-retry",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert source_claim is not None
    await db_session.commit()
    failing_section = "parent_style"
    source_provider = SelectiveProvider(failed_sections={failing_section})
    source_result = await run_claimed_full_generation(
        db_session,
        claim=source_claim,
        provider=source_provider,
        now=NOW,
    )
    assert source_result.status == ChildGenerationStatus.NARRATIVE_FAILED.value
    assert source_result.report_id is not None

    deterministic_models = (
        models.ChildParentStyleScore,
        models.ChildNeedScore,
        models.ChildSynastryEvidence,
        models.ChildInteractionScore,
        models.ChildContextResolution,
        models.ChildGuidanceFacts,
        models.ChildReport,
    )

    async def deterministic_identity() -> dict[str, tuple[tuple[str, str], ...]]:
        result: dict[str, tuple[tuple[str, str], ...]] = {}
        for model in deterministic_models:
            rows = tuple((await db_session.scalars(select(model).order_by(model.id))).all())
            result[model.__tablename__] = tuple(
                (str(row.id), repr({column.name: getattr(row, column.name) for column in model.__table__.columns}))
                for row in rows
            )
        return result

    before = await deterministic_identity()

    def dispatch(*, generation_id: UUID) -> str:
        return f"child-generation-{generation_id}"

    accepted = await accept_narrative_retry_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        source_report_id=source_result.report_id,
        idempotency_key="narrative-retry-one",
        dispatcher=dispatch,
        now=NOW + timedelta(minutes=1),
    )
    assert accepted.status == ChildGenerationStatus.NARRATIVE_RETRY_WAITING.value
    assert (
        await repository.claim_generation(
            generation_id=accepted.generation_id,
            task_id="narrative-retry-too-early",
            now=NOW + timedelta(minutes=1, seconds=29),
            lease_duration=timedelta(minutes=5),
        )
        is None
    )
    retry_claim = await repository.claim_generation(
        generation_id=accepted.generation_id,
        task_id="narrative-retry-due",
        now=NOW + timedelta(minutes=1, seconds=30),
        lease_duration=timedelta(minutes=5),
    )
    assert retry_claim is not None
    assert retry_claim.generation.status == ChildGenerationStatus.GENERATING_SECTIONS.value
    await db_session.commit()

    recovered_provider = SelectiveProvider(failed_sections=set())
    retry_result = await run_claimed_narrative_retry(
        db_session,
        claim=retry_claim,
        provider=recovered_provider,
        now=NOW + timedelta(minutes=1, seconds=30),
    )

    assert retry_result.status == ChildGenerationStatus.READY.value
    assert retry_result.report_id == source_result.report_id
    assert recovered_provider.section_keys == [failing_section]
    assert await deterministic_identity() == before
    retry_segments = tuple(
        (
            await db_session.scalars(
                select(models.ChildSegmentGeneration).where(
                    models.ChildSegmentGeneration.generation_id == accepted.generation_id
                )
            )
        ).all()
    )
    assert [row.section_key for row in retry_segments] == [failing_section]
    assembly = await db_session.scalar(
        select(models.ChildReportAssembly).where(models.ChildReportAssembly.generation_id == accepted.generation_id)
    )
    assert assembly is not None
    assert assembly.status == ChildGenerationStatus.READY.value
    assert assembly.source_generation_id == source_generation.generation_id
    assert assembly.report_id == source_result.report_id


@pytest.mark.asyncio
async def test_generation_events_are_transactional_safe_and_append_only(db_session: AsyncSession) -> None:
    seed = await _seed_lifecycle(db_session)

    def dispatch(*, generation_id: UUID) -> str:
        return f"child-generation-{generation_id}"

    accepted = await accept_full_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        questionnaire_session_id=seed.questionnaire_id,
        idempotency_key="event-audit-generation",
        dispatcher=dispatch,
    )
    repository = ChildRepository(db_session)
    claim = await repository.claim_generation(
        generation_id=accepted.generation_id,
        task_id=f"child-generation-{accepted.generation_id}",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await repository.release_generation_for_retry(
        generation_id=accepted.generation_id,
        claim_token=claim.claim_token,
        now=NOW,
        retry_base_seconds=30,
        max_attempts=3,
        error_code="safe_transient_failure",
    )
    await db_session.commit()

    events = tuple(
        (
            await db_session.scalars(
                select(models.ChildGenerationEvent)
                .where(models.ChildGenerationEvent.generation_id == accepted.generation_id)
                .order_by(models.ChildGenerationEvent.occurred_at, models.ChildGenerationEvent.id)
            )
        ).all()
    )
    assert {event.event_code for event in events} == {
        "accepted",
        "dispatch_claimed",
        "dispatch_succeeded",
        "worker_claimed",
        "retry_released",
    }
    assert len(events) == 5
    assert all(event.attempt_number >= 0 for event in events)
    assert all(event.task_correlation in {None, f"child-generation-{accepted.generation_id}"} for event in events)
    assert all(not hasattr(event, field) for event in (events[0],) for field in ("payload", "message", "child_name"))

    events[0].event_code = "mutated"
    with pytest.raises(models.ImmutableChildArtifactError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_narrative_retry_does_not_repeat_ambiguous_provider_intent(
    db_session: AsyncSession,
) -> None:
    seed, source_generation = await _seed_claimable_full_pipeline(
        db_session,
        idempotency_key="full-before-ambiguous-retry",
    )
    repository = ChildRepository(db_session)
    source_claim = await repository.claim_generation(
        generation_id=source_generation.generation_id,
        task_id="worker-before-ambiguous-retry",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert source_claim is not None
    await db_session.commit()
    source_result = await run_claimed_full_generation(
        db_session,
        claim=source_claim,
        provider=SelectiveProvider(failed_sections={"parent_style"}),
        now=NOW,
    )
    assert source_result.status == ChildGenerationStatus.NARRATIVE_FAILED.value
    await db_session.execute(
        update(models.ChildSegmentGeneration)
        .where(
            models.ChildSegmentGeneration.generation_id == source_generation.generation_id,
            models.ChildSegmentGeneration.status == "failed",
        )
        .values(error_code="child_narrative_provider_outcome_unknown")
    )
    await db_session.commit()

    accepted = await accept_narrative_retry_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        source_report_id=source_result.report_id,  # type: ignore[arg-type]
        idempotency_key="ambiguous-narrative-retry",
        dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
        now=NOW + timedelta(minutes=1),
    )
    claim = await repository.claim_generation(
        generation_id=accepted.generation_id,
        task_id="ambiguous-retry-worker",
        now=NOW + timedelta(minutes=1, seconds=30),
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await db_session.commit()
    provider = CountingProvider()
    result = await run_claimed_narrative_retry(
        db_session,
        claim=claim,
        provider=provider,
        now=NOW + timedelta(minutes=1, seconds=30),
    )

    assert result.status == ChildGenerationStatus.NARRATIVE_FAILED.value
    assert provider.calls == 0
    retry_rows = tuple(
        (
            await db_session.scalars(
                select(models.ChildSegmentGeneration).where(
                    models.ChildSegmentGeneration.generation_id == accepted.generation_id
                )
            )
        ).all()
    )
    assert retry_rows
    assert all(row.error_code == "child_narrative_provider_outcome_unknown" for row in retry_rows)
