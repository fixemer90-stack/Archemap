"""PostgreSQL proof for first-party Child lifecycle facts."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import settings
from app.modules.analytics.models import BusinessEvent, BusinessEventOutbox
from app.modules.child import models
from app.modules.child.repository import ChildRepository
from app.modules.child.service import (
    _dispatch_accepted_generation,
    accept_full_generation,
    accept_narrative_retry_generation,
    run_claimed_full_generation,
    run_claimed_narrative_retry,
)
from app.modules.child.status import ChildGenerationOperation
from tests.integration.test_child_generation_lifecycle import (
    NOW,
    CountingProvider,
    LifecycleSeed,
    SelectiveProvider,
    _seed_claimable_full_pipeline,
    _seed_lifecycle,
)
from workers.tasks import child as child_worker

pytestmark = pytest.mark.usefixtures("_setup_database")


def _sessions(db: AsyncSession) -> async_sessionmaker[AsyncSession]:
    assert isinstance(db.bind, AsyncEngine)
    return async_sessionmaker(db.bind, expire_on_commit=False)


@pytest.mark.parametrize("degraded", [False, True], ids=["ready", "partial"])
async def test_child_report_outcome_uses_published_assembly(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, degraded: bool
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    seed, generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="child-terminal-fact")
    generation_id = generation.generation_id
    claim = await ChildRepository(db_session).claim_generation(
        generation_id=generation_id,
        task_id="child-terminal",
        now=NOW,
        lease_duration=timedelta(minutes=5),
    )
    assert claim is not None
    await db_session.commit()
    provider = SelectiveProvider(failed_sections={"parent_style"}) if degraded else CountingProvider()
    await run_claimed_full_generation(db_session, claim=claim, provider=provider, now=NOW)

    async with _sessions(db_session)() as fresh:
        assembly = (await fresh.scalars(select(models.ChildReportAssembly))).one()
        persisted = (await fresh.scalars(select(models.ChildGeneration))).one()
        outcome = select(BusinessEvent).where(BusinessEvent.event_type != "report_requested")
        (fact,) = (await fresh.scalars(outcome)).all()
        assert fact.event_type == ("report_partial" if degraded else "report_ready")
        assert fact.entity_id == assembly.id
        assert fact.subject_id == seed.owner_id
        assert fact.product == "child" and fact.details == {} and fact.source_id is None
        assert fact.occurred_at == persisted.finished_at
        outbox = await fresh.scalar(select(BusinessEventOutbox).where(BusinessEventOutbox.event_id == fact.id))
        assert outbox is not None and outbox.status == "pending"


async def _accept(db: AsyncSession, seed: LifecycleSeed) -> tuple[UUID, bool]:
    result = await ChildRepository(db).create_generation_idempotently(
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        parent_chart_id=seed.parent_chart_id,
        child_chart_version_id=seed.child_chart_id,
        questionnaire_session_id=seed.questionnaire_id,
        operation=ChildGenerationOperation.FULL_REPORT.value,
        idempotency_key="private-client-key",
        operation_payload={"private fixture": "must not reach analytics"},
    )
    return result.generation.generation_id, result.created


@pytest.mark.parametrize("winner", ["worker", "new-lease"])
async def test_child_late_dispatch_error_cannot_clear_current_owner(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, winner: str
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    seed = await _seed_lifecycle(db_session)
    generation_id, created = await _accept(db_session, seed)
    assert created
    await db_session.commit()
    commit = db_session.commit
    interleaved = False
    newer = datetime.now(UTC) + timedelta(days=1)

    async def commit_then_interleave() -> None:
        nonlocal interleaved
        await commit()
        if interleaved:
            return
        interleaved = True
        async with _sessions(db_session).begin() as other:
            repository = ChildRepository(other)
            if winner == "worker":
                assert (
                    await repository.claim_generation(
                        generation_id=generation_id,
                        task_id=f"child-generation-{generation_id}",
                        now=newer,
                        lease_duration=timedelta(minutes=5),
                    )
                    is not None
                )
            else:
                assert (
                    await repository.claim_generation_dispatch(
                        generation_id=generation_id, now=newer, lease_duration=timedelta(minutes=5)
                    )
                    == f"child-generation-{generation_id}"
                )

    def lost_publish_reply(*, generation_id: UUID) -> str:
        raise OSError("private broker error")

    monkeypatch.setattr(db_session, "commit", commit_then_interleave)
    assert (
        await _dispatch_accepted_generation(
            db_session,
            repository=ChildRepository(db_session),
            generation_id=generation_id,
            dispatcher=lost_publish_reply,
        )
        is None
    )
    async with _sessions(db_session)() as fresh:
        saved = (await fresh.scalars(select(models.ChildGeneration))).one()
        assert saved.celery_task_id == f"child-generation-{generation_id}"
        if winner == "worker":
            assert saved.status == "calculating_pair" and saved.claim_token is not None
        else:
            assert saved.status == "queued" and saved.dispatched_at == newer
            assert saved.dispatch_expires_at == newer + timedelta(minutes=5)
        assert (await fresh.scalars(select(BusinessEvent.event_type))).all() == ["report_requested"]
        assert (await fresh.scalars(select(models.ChildGenerationEvent.event_code))).all().count("dispatch_failed") == 0


@pytest.mark.parametrize("retry", [False, True], ids=["full", "retry"])
async def test_child_publication_recovers_from_rejected_outbox_without_redispatch(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, retry: bool
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    monkeypatch.setattr(settings, "CHILD_GENERATION_MAX_ATTEMPTS", 1)
    seed, generation = await _seed_claimable_full_pipeline(db_session, idempotency_key="checkpoint-source")
    repository = ChildRepository(db_session)
    generation_id = generation.generation_id
    now = NOW
    claim = await repository.claim_generation(
        generation_id=generation_id, task_id="checkpoint-first", now=now, lease_duration=timedelta(minutes=5)
    )
    assert claim is not None
    await db_session.commit()
    if retry:
        source = await run_claimed_full_generation(
            db_session, claim=claim, provider=SelectiveProvider(failed_sections={"parent_style"}), now=now
        )
        assert source.report_id is not None and source.status == "narrative_failed"
        accepted = await accept_narrative_retry_generation(
            db_session,
            owner_user_id=seed.owner_id,
            child_profile_id=seed.child_id,
            source_report_id=source.report_id,
            idempotency_key="checkpoint-retry",
            dispatcher=lambda *, generation_id: f"child-generation-{generation_id}",
            now=now,
        )
        generation_id = accepted.generation_id
        now += timedelta(minutes=2)
        claim = await repository.claim_generation(
            generation_id=generation_id, task_id="checkpoint-retry", now=now, lease_duration=timedelta(minutes=5)
        )
        assert claim is not None
        await db_session.commit()

    await db_session.execute(
        text("ALTER TABLE business_event_outbox ADD CONSTRAINT reject_child_final CHECK (false) NOT VALID")
    )
    await db_session.commit()
    runner = run_claimed_narrative_retry if retry else run_claimed_full_generation
    provider = CountingProvider()
    with pytest.raises(IntegrityError, match="reject_child_final"):
        await runner(db_session, claim=claim, provider=provider, now=now)
    await db_session.commit()
    assert provider.calls > 0
    sessions = _sessions(db_session)
    generations = select(models.ChildGeneration).where(models.ChildGeneration.generation_id == generation_id)
    assemblies = select(models.ChildReportAssembly).where(models.ChildReportAssembly.generation_id == generation_id)
    ready_facts = select(BusinessEvent).where(BusinessEvent.event_type == "report_ready")
    async with sessions() as fresh:
        pending = await fresh.scalar(generations)
        assert pending is not None and pending.status == "generating_sections" and pending.attempt_count == 1
        candidate = pending.pending_publication
        assert candidate is not None and candidate["status"] == "ready"
        assert await fresh.scalar(assemblies) is None
        assert await fresh.scalar(ready_facts) is None

    def prohibit_dispatch(*, generation_id: UUID) -> str:
        pytest.fail(f"checkpointed work must not redispatch: {generation_id}")

    monkeypatch.setattr(child_worker, "async_session_factory", sessions)
    monkeypatch.setattr(child_worker, "dispatch_child_generation", prohibit_dispatch)
    with pytest.raises(IntegrityError, match="reject_child_final"):
        await child_worker._reconcile_child_generations_async()
    await db_session.execute(text("ALTER TABLE business_event_outbox DROP CONSTRAINT reject_child_final"))
    await db_session.commit()
    results = await asyncio.gather(*(child_worker._reconcile_child_generations_async() for _ in range(2)))
    assert sum(result["terminal"] for result in results) == 1
    assert all(result["requeued"] == result["dispatched"] == 0 for result in results)
    async with sessions() as fresh:
        assembly = await fresh.scalar(assemblies)
        assert assembly is not None and assembly.payload == candidate
        (fact,) = (await fresh.scalars(ready_facts)).all()
        assert fact.entity_id == assembly.id
        delivery = await fresh.scalar(select(BusinessEventOutbox).where(BusinessEventOutbox.event_id == fact.id))
        assert delivery is not None
        terminal = await fresh.scalar(generations)
        assert terminal is not None and terminal.status == "ready" and terminal.pending_publication is None
        assert terminal.attempt_count == 1 and terminal.finished_at == fact.occurred_at


@pytest.mark.parametrize("scheduled", [False, True], ids=["worker", "lease-exhausted"])
async def test_child_failure_uses_generation_identity_and_rolls_back_with_outbox(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, scheduled: bool
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    seed = await _seed_lifecycle(db_session)
    generation_id, _ = await _accept(db_session, seed)
    repo = ChildRepository(db_session)
    claim = await repo.claim_generation(
        generation_id=generation_id, task_id="child-failure", now=NOW, lease_duration=timedelta(seconds=1)
    )
    assert claim is not None
    await db_session.execute(
        text("ALTER TABLE business_event_outbox ADD CONSTRAINT reject_child_failure CHECK (false) NOT VALID")
    )
    await db_session.commit()
    finished_at = NOW + timedelta(seconds=2)
    token = claim.claim_token

    async def finish(session: AsyncSession) -> None:
        repository = ChildRepository(session)
        if scheduled:
            await repository.reconcile_stuck_generations(now=finished_at, max_attempts=1)
        else:
            await repository.fail_claimed_generation(
                generation_id=generation_id, claim_token=token, now=finished_at, error_code="bounded_fixture_code"
            )

    sessions = _sessions(db_session)
    async with sessions() as worker:
        with pytest.raises(IntegrityError, match="reject_child_failure"):
            await finish(worker)
        await worker.commit()
    generation_query = select(models.ChildGeneration).where(models.ChildGeneration.generation_id == generation_id)
    failed_facts = select(BusinessEvent).where(BusinessEvent.event_type == "report_failed")
    async with sessions() as fresh:
        persisted = await fresh.scalar(generation_query)
        assert persisted is not None and persisted.status == "calculating_pair" and persisted.finished_at is None
        assert await fresh.scalar(failed_facts) is None
    await db_session.execute(text("ALTER TABLE business_event_outbox DROP CONSTRAINT reject_child_failure"))
    await db_session.commit()
    async with sessions.begin() as worker:
        await finish(worker)
    async with sessions() as fresh:
        persisted = await fresh.scalar(generation_query)
        assert persisted is not None and persisted.status == "failed" and persisted.finished_at == finished_at
        outcome = (await fresh.scalars(failed_facts)).one()
        assert (outcome.entity_id, outcome.subject_id, outcome.occurred_at) == (
            generation_id,
            seed.owner_id,
            finished_at,
        )
        assert outcome.details == {} and outcome.source_id is None and outcome.product == "child"
        assert await fresh.scalar(select(BusinessEventOutbox.id).where(BusinessEventOutbox.event_id == outcome.id))


async def test_child_request_records_one_private_fact_for_concurrent_acceptance(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    seed = await _seed_lifecycle(db_session)
    sessions = _sessions(db_session)

    async def accept() -> tuple[UUID, bool]:
        async with sessions() as db:
            result = await _accept(db, seed)
            await db.commit()
            return result

    first, second = await asyncio.gather(accept(), accept())
    assert first[0] == second[0]
    assert {first[1], second[1]} == {True, False}
    async with sessions() as db:
        (generation,) = (await db.scalars(select(models.ChildGeneration))).all()
        assert generation.generation_id == first[0]
        (fact,) = (await db.scalars(select(BusinessEvent))).all()
        assert fact.event_type == "report_requested"
        assert fact.semantic_key == f"v1:report_requested:{generation.generation_id}:-"
        assert fact.entity_id == generation.generation_id
        assert fact.subject_id == seed.owner_id
        assert fact.occurred_at == generation.created_at
        assert fact.product == "child"
        assert fact.mode == "unknown"
        assert fact.source_id is None
        assert fact.details == {}
        (outbox,) = (await db.scalars(select(BusinessEventOutbox))).all()
        assert outbox.event_id == fact.id
        assert outbox.destination == "internal_projection"
        assert outbox.status == "pending"


async def test_enabling_monitoring_does_not_backfill_an_accepted_child_request(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", False)
    seed = await _seed_lifecycle(db_session)
    original, created = await _accept(db_session, seed)
    assert created
    await db_session.commit()

    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    sessions = _sessions(db_session)
    async with sessions() as db:
        assert await _accept(db, seed) == (original, False)
        await db.commit()
    async with sessions() as db:
        assert (await db.scalars(select(models.ChildGeneration.generation_id))).all() == [original]
        assert not (await db.scalars(select(BusinessEvent))).all()
        assert not (await db.scalars(select(BusinessEventOutbox))).all()


async def test_child_outbox_failure_rolls_back_acceptance_before_dispatch(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    seed = await _seed_lifecycle(db_session)
    sessions = _sessions(db_session)
    await db_session.execute(
        text("ALTER TABLE business_event_outbox ADD CONSTRAINT child_outbox_failure CHECK (false)")
    )
    await db_session.commit()
    dispatched: list[UUID] = []

    def dispatch(*, generation_id: UUID) -> str:
        dispatched.append(generation_id)
        return f"child-generation-{generation_id}"

    async with sessions() as db:
        with pytest.raises(IntegrityError, match="child_outbox_failure"):
            await accept_full_generation(
                db,
                owner_user_id=seed.owner_id,
                child_profile_id=seed.child_id,
                questionnaire_session_id=seed.questionnaire_id,
                idempotency_key="retryable-acceptance",
                dispatcher=dispatch,
            )
        await db.commit()
    assert not dispatched
    async with sessions() as db:
        assert not (await db.scalars(select(models.ChildGeneration))).all()
        assert not (await db.scalars(select(models.ChildGenerationEvent))).all()
        assert not (await db.scalars(select(BusinessEvent))).all()
        assert not (await db.scalars(select(BusinessEventOutbox))).all()

    await db_session.execute(text("ALTER TABLE business_event_outbox DROP CONSTRAINT child_outbox_failure"))
    await db_session.commit()
    accepted = await accept_full_generation(
        db_session,
        owner_user_id=seed.owner_id,
        child_profile_id=seed.child_id,
        questionnaire_session_id=seed.questionnaire_id,
        idempotency_key="retryable-acceptance",
        dispatcher=dispatch,
    )
    assert accepted.created
    assert dispatched == [accepted.generation_id]
    async with sessions() as db:
        (fact,) = (await db.scalars(select(BusinessEvent))).all()
        assert fact.entity_id == accepted.generation_id
        assert (await db.scalars(select(BusinessEventOutbox.event_id))).all() == [fact.id]
