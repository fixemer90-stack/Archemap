"""PostgreSQL proof for the Career report-requested producer."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import settings
from app.modules.analytics.models import BusinessEvent, BusinessEventOutbox
from app.modules.astrotype_v2.models import NatalChart
from app.modules.career.models import CareerGeneration, CareerProfile, CareerQuestionnaireSession, CareerReport
from app.modules.career.questionnaire import QUESTIONNAIRE_VERSION
from app.modules.career.repository import CareerRepository
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User

pytestmark = pytest.mark.usefixtures("_setup_database")


@pytest.fixture
async def career_profile(db_session: AsyncSession) -> AsyncIterator[CareerProfile]:
    user = User(
        email="career-events@example.com",
        name="Career events",
        hashed_password="not-used",  # noqa: S106 - inert fixture value
    )
    db_session.add(user)
    await db_session.flush()
    person = PersonProfile(
        user_id=user.id,
        name="private profile fixture",
        birth_date=date(1990, 1, 1),
        birth_place="private birthplace fixture",
        latitude=0,
        longitude=0,
        timezone="UTC",
        birth_time_accuracy="unknown",
    )
    db_session.add(person)
    await db_session.flush()
    chart = NatalChart(
        user_id=user.id,
        profile_id=person.id,
        engine_version="test",
        input_hash="a" * 64,
        birth_datetime_utc=datetime(1990, 1, 1, tzinfo=UTC),
        timezone="UTC",
        latitude=0,
        longitude=0,
        house_system="P",
        calculation_payload={},
    )
    db_session.add(chart)
    await db_session.flush()
    profile = CareerProfile(
        user_id=user.id,
        profile_id=person.id,
        chart_id=chart.id,
        generation_id=uuid4(),
        idempotency_key="bootstrap",
        scoring_version="test",
        reference_version="test",
        questionnaire_version=QUESTIONNAIRE_VERSION,
    )
    db_session.add(profile)
    await db_session.flush()
    db_session.add(
        CareerQuestionnaireSession(
            career_profile_id=profile.id,
            chart_id=chart.id,
            status="completed",
            questionnaire_version=QUESTIONNAIRE_VERSION,
            context_version="test",
            consent_version="test",
            answers_hash="b" * 64,
        )
    )
    await db_session.commit()
    yield profile
    await db_session.rollback()


def _sessions(db: AsyncSession) -> async_sessionmaker[AsyncSession]:
    assert isinstance(db.bind, AsyncEngine)
    return async_sessionmaker(db.bind, expire_on_commit=False)


async def _regenerate(db: AsyncSession, profile: CareerProfile, source_report_id: UUID) -> tuple[UUID, bool]:
    result = await CareerRepository(db).create_generation_idempotently(
        generation_id=uuid4(),
        user_id=profile.user_id,
        career_profile_id=profile.id,
        chart_id=profile.chart_id,
        operation="regenerate",
        idempotency_key="private-idempotency-key",
        source_report_id=source_report_id,
        diagnostics={"section_keys": ["private diagnostic fixture"]},
    )
    return result.generation.generation_id, result.created


async def _create_or_resume(db: AsyncSession, profile: CareerProfile, *, key: str) -> tuple[UUID, bool]:
    repo = CareerRepository(db)
    questionnaire = await repo.get_questionnaire_session(
        career_profile_id=profile.id, questionnaire_version=QUESTIONNAIRE_VERSION
    )
    result = await repo.resume_or_create_generation(
        profile=profile,
        user_id=profile.user_id,
        idempotency_key=key,
        questionnaire=questionnaire,
    )
    return result.generation.generation_id, result.created


async def test_career_request_emits_once_for_concurrent_replays(
    db_session: AsyncSession, career_profile: CareerProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    sessions = _sessions(db_session)
    source_report = CareerReport(
        career_profile_id=career_profile.id,
        chart_id=career_profile.chart_id,
        generation_id=uuid4(),
        idempotency_key="historical-report",
        version=1,
        status="ready",
        scoring_version="test",
        reference_version="test",
        questionnaire_version=QUESTIONNAIRE_VERSION,
        prompt_version="test",
        deterministic_payload={"private report fixture": True},
    )
    db_session.add(source_report)
    await db_session.commit()

    async def accept() -> tuple[UUID, bool]:
        async with sessions() as db:
            result = await _regenerate(db, career_profile, source_report.id)
            await db.commit()
            return result

    first, second = await asyncio.gather(accept(), accept())
    assert sorted((first[1], second[1])) == [False, True]
    assert first[0] == second[0]

    async with sessions() as readback:
        (generation,) = (await readback.scalars(select(CareerGeneration))).all()
        assert generation.generation_id == first[0]
        assert generation.status == "queued"
        (event,) = (await readback.scalars(select(BusinessEvent))).all()
        assert event.event_type == "report_requested"
        assert event.semantic_key == f"v1:report_requested:{generation.generation_id}:-"
        assert event.entity_id == generation.generation_id
        assert event.subject_id == generation.user_id
        assert event.occurred_at == generation.created_at
        assert event.product == "career"
        assert event.mode == "unknown"
        assert event.source_id is None
        assert event.details == {}
        (delivery,) = (await readback.scalars(select(BusinessEventOutbox))).all()
        assert delivery.event_id == event.id
        assert delivery.destination == "internal_projection"
        assert delivery.status == "pending"


async def test_career_create_reuse_does_not_backfill_a_request_accepted_with_monitoring_off(
    db_session: AsyncSession, career_profile: CareerProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", False)
    original, created = await _create_or_resume(db_session, career_profile, key="original")
    assert created
    await db_session.commit()

    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    sessions = _sessions(db_session)
    async with sessions() as db:
        assert await _create_or_resume(db, career_profile, key="fresh-key-reuse") == (original, False)
        await db.commit()
    async with sessions() as readback:
        assert (await readback.scalars(select(CareerGeneration.generation_id))).all() == [original]
        assert not (await readback.scalars(select(BusinessEvent))).all()
        assert not (await readback.scalars(select(BusinessEventOutbox))).all()


async def test_career_outbox_failure_rolls_back_generation_even_if_caller_commits(
    db_session: AsyncSession, career_profile: CareerProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    await db_session.execute(text("ALTER TABLE business_event_outbox ADD CONSTRAINT injected_failure CHECK (false)"))
    await db_session.commit()

    sessions = _sessions(db_session)
    async with sessions() as db:
        with pytest.raises(IntegrityError, match="injected_failure"):
            await _create_or_resume(db, career_profile, key="retryable-create")
        await db.commit()

    async with sessions() as readback:
        assert not (await readback.scalars(select(CareerGeneration))).all()
        assert not (await readback.scalars(select(BusinessEvent))).all()
        assert not (await readback.scalars(select(BusinessEventOutbox))).all()

    await db_session.execute(text("ALTER TABLE business_event_outbox DROP CONSTRAINT injected_failure"))
    await db_session.commit()
    operation, created = await _create_or_resume(db_session, career_profile, key="retryable-create")
    assert created
    await db_session.commit()
    async with sessions() as readback:
        assert (await readback.scalars(select(CareerGeneration.generation_id))).all() == [operation]
        (event,) = (await readback.scalars(select(BusinessEvent))).all()
        assert event.entity_id == operation
        assert (await readback.scalars(select(BusinessEventOutbox.event_id))).all() == [event.id]
