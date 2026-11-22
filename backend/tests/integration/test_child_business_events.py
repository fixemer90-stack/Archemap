"""PostgreSQL proof for first-party Child lifecycle facts."""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import settings
from app.modules.analytics.models import BusinessEvent, BusinessEventOutbox
from app.modules.child import models
from app.modules.child.repository import ChildRepository
from app.modules.child.service import accept_full_generation
from app.modules.child.status import ChildGenerationOperation
from tests.integration.test_child_generation_lifecycle import LifecycleSeed, _seed_lifecycle

pytestmark = pytest.mark.usefixtures("_setup_database")


def _sessions(db: AsyncSession) -> async_sessionmaker[AsyncSession]:
    assert isinstance(db.bind, AsyncEngine)
    return async_sessionmaker(db.bind, expire_on_commit=False)


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
