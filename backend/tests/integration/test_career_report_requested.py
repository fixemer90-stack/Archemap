"""PostgreSQL proof for Career lifecycle producers."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import settings
from app.modules.analytics.models import BusinessEvent, BusinessEventOutbox
from app.modules.astrotype_v2.models import NatalChart
from app.modules.career.models import (
    CareerGeneration,
    CareerProfile,
    CareerQuestionnaireSession,
    CareerReport,
    CareerSegmentGeneration,
)
from app.modules.career.narrative import CAREER_SECTION_ORDER, MockCareerSegmentProvider
from app.modules.career.narrative_schemas import CareerSectionRenderInput
from app.modules.career.questionnaire import QUESTIONNAIRE_VERSION
from app.modules.career.repository import CareerRepository
from app.modules.career.router import _enqueue_generation
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User
from workers.tasks import career

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


async def _regenerate(
    db: AsyncSession, profile: CareerProfile, source_report_id: UUID, *, key: str = "private-idempotency-key"
) -> tuple[UUID, bool]:
    result = await CareerRepository(db).create_generation_idempotently(
        generation_id=uuid4(),
        user_id=profile.user_id,
        career_profile_id=profile.id,
        chart_id=profile.chart_id,
        operation="regenerate",
        idempotency_key=key,
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
    source_report = await _historical_report(db_session, career_profile)

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


@pytest.fixture
def career_worker(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> async_sessionmaker[AsyncSession]:
    sessions = _sessions(db_session)
    monkeypatch.setattr(career, "async_session_factory", sessions)
    monkeypatch.setattr(career, "_career_provider", MockCareerSegmentProvider)
    return sessions


async def _historical_report(db: AsyncSession, profile: CareerProfile) -> CareerReport:
    fact_key = "dimension:systems_thinking"
    source = CareerReport(
        career_profile_id=profile.id,
        chart_id=profile.chart_id,
        generation_id=uuid4(),
        idempotency_key="historical-source",
        version=1,
        status="ready",
        scoring_version="test",
        reference_version="test",
        questionnaire_version=QUESTIONNAIRE_VERSION,
        prompt_version="test",
        deterministic_payload={
            "profile_id": str(profile.id),
            "chart_id": str(profile.chart_id),
            "scoring_version": "test",
            "top_dimensions": [
                {
                    "fact_key": fact_key,
                    "dimension": "systems_thinking",
                    "score": 88,
                    "confidence": 0.9,
                    "scoring_version": "test",
                    "evidence_refs": [f"natal_fact:{uuid4()}"],
                    "conditional_language_required": False,
                }
            ],
            "low_dimensions": [],
            "career_archetypes": [],
            "preferred_environment": [],
            "risk_environment": [],
            "confirmed_traits": [],
            "contradictions": [],
            "user_preferences": [],
            "context_constraints": [],
            "role_matches": [],
            "career_paths": [],
            "section_contracts": {
                key: {
                    "section_key": key,
                    "owned_fact_keys": [fact_key],
                    "reference_fact_keys": [],
                    "forbidden_fact_keys": ["dimension:leadership"],
                }
                for key in CAREER_SECTION_ORDER
            },
        },
        narrative_payload={"sections": ["private historical narrative"]},
    )
    db.add(source)
    await db.commit()
    return source


async def _queued_regeneration(
    db: AsyncSession, profile: CareerProfile, source: CareerReport, *, key: str = "private-idempotency-key"
) -> UUID:
    operation, created = await _regenerate(db, profile, source.id, key=key)
    assert created
    await db.commit()
    return operation


@pytest.mark.parametrize("case", ["failure", "off", "outbox-rejected", "worker-won", "late-receipt"])
async def test_career_publish_error_only_terminalizes_unclaimed_work(
    db_session: AsyncSession, career_profile: CareerProfile, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", case != "off")
    source = await _historical_report(db_session, career_profile)
    operation = await _queued_regeneration(db_session, career_profile, source)
    query = select(CareerGeneration).where(CareerGeneration.generation_id == operation)
    generation = (await db_session.scalars(query)).one()
    await db_session.commit()
    sessions = _sessions(db_session)
    if case in {"worker-won", "late-receipt"}:
        async with sessions.begin() as worker:
            assert await CareerRepository(worker).claim_generation(operation) is not None
    if case == "outbox-rejected":
        await db_session.execute(text("ALTER TABLE business_event_outbox ADD CHECK (false) NOT VALID"))
        await db_session.commit()

    def publish_error(**_: Any) -> None:
        raise OSError("private broker error")

    if case == "late-receipt":
        monkeypatch.setattr(career.generate_career_report, "delay", lambda **_: SimpleNamespace(id="received"))
    else:
        monkeypatch.setattr(career.generate_career_report, "delay", publish_error)
    if case in {"worker-won", "late-receipt"}:
        await _enqueue_generation(db=db_session, generation=generation, section_keys=[])
    elif case == "outbox-rejected":
        with pytest.raises(IntegrityError):
            await _enqueue_generation(db=db_session, generation=generation, section_keys=[])
        await db_session.commit()
    else:
        with pytest.raises(HTTPException) as error:
            await _enqueue_generation(db=db_session, generation=generation, section_keys=[])
        assert error.value.status_code == 503

    async with sessions() as fresh:
        saved = (await fresh.scalars(query)).one()
        expected = {
            "worker-won": "calculating_dimensions",
            "late-receipt": "calculating_dimensions",
            "outbox-rejected": "queued",
        }.get(case, "failed")
        assert saved.status == expected
        assert saved.celery_task_id is None
        if case == "failure":
            await _assert_terminal_event(
                fresh, saved, event_type="report_failed", entity_id=operation, occurred_at=saved.updated_at
            )
        else:
            assert (
                await fresh.scalar(select(BusinessEvent.id).where(BusinessEvent.event_type == "report_failed")) is None
            )


async def test_career_ready_is_bound_to_new_result_and_not_reemitted_on_redelivery(
    db_session: AsyncSession,
    career_profile: CareerProfile,
    career_worker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    source = await _historical_report(db_session, career_profile)
    operation = await _queued_regeneration(db_session, career_profile, source)

    first, second = await asyncio.gather(
        career._generate_career_report_async(generation_id=operation, section_keys=[]),
        career._generate_career_report_async(generation_id=operation, section_keys=[]),
    )
    assert sum(bool(result.get("duplicate_delivery")) for result in (first, second)) == 1
    replay = await career._generate_career_report_async(generation_id=operation, section_keys=[])
    assert replay["duplicate_delivery"] is True
    assert replay["status"] == "ready"

    async with career_worker() as readback:
        (generation,) = (await readback.scalars(select(CareerGeneration))).all()
        old_report, report = (await readback.scalars(select(CareerReport).order_by(CareerReport.version))).all()
        assert old_report.id == source.id
        assert old_report.narrative_payload == source.narrative_payload
        assert report.id == generation.report_id
        assert report.generation_id == operation
        assert report.status == generation.status == "ready"
        await _assert_terminal_event(
            readback, generation, event_type="report_ready", entity_id=report.id, occurred_at=report.updated_at
        )


@pytest.mark.parametrize("recovery", ["redelivery", "scheduled"])
async def test_career_terminal_outbox_rejection_preserves_prior_durable_reports(
    db_session: AsyncSession,
    career_profile: CareerProfile,
    career_worker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    recovery: str,
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", False)
    source = await _historical_report(db_session, career_profile)
    operation = await _queued_regeneration(db_session, career_profile, source)
    await db_session.execute(text("ALTER TABLE business_event_outbox ADD CONSTRAINT reject_terminal CHECK (false)"))
    await db_session.commit()
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)

    with pytest.raises(IntegrityError, match="reject_terminal"):
        await career._generate_career_report_async(generation_id=operation, section_keys=[])

    async with career_worker() as readback:
        (generation,) = (await readback.scalars(select(CareerGeneration))).all()
        old_report, new_report = (await readback.scalars(select(CareerReport).order_by(CareerReport.version))).all()
        assert generation.generation_id == operation
        assert generation.status == "generating_sections"  # Earlier stage commit survives independently.
        assert new_report.id == generation.report_id
        assert new_report.status == "deterministic_ready"
        assert new_report.narrative_payload["sections"] == []
        assert new_report.deterministic_payload == source.deterministic_payload
        assert old_report.id == source.id
        assert old_report.status == "ready"
        assert old_report.narrative_payload == source.narrative_payload
        assert not (await readback.scalars(select(CareerSegmentGeneration))).all()
        assert not (await readback.scalars(select(BusinessEvent))).all()
        assert not (await readback.scalars(select(BusinessEventOutbox))).all()

    await db_session.execute(text("ALTER TABLE business_event_outbox DROP CONSTRAINT reject_terminal"))
    await db_session.commit()

    def prohibit_provider() -> MockCareerSegmentProvider:
        pytest.fail("publication recovery must not call the narrative provider")

    monkeypatch.setattr(career, "_career_provider", prohibit_provider)
    if recovery == "scheduled":
        assert await career._reconcile_career_publications() == 1
        assert await career._reconcile_career_publications() == 0
    first, second = await asyncio.gather(
        career._generate_career_report_async(generation_id=operation, section_keys=[]),
        career._generate_career_report_async(generation_id=operation, section_keys=[]),
    )
    assert first["status"] == second["status"] == "ready"
    assert first["report_id"] == second["report_id"] == str(new_report.id)
    async with career_worker() as readback:
        (completed,) = (await readback.scalars(select(CareerGeneration))).all()
        report = await readback.get(CareerReport, new_report.id)
        assert report is not None and report.status == "ready"
        assert (await readback.scalars(select(CareerSegmentGeneration))).all()
        await _assert_terminal_event(
            readback, completed, event_type="report_ready", entity_id=report.id, occurred_at=report.updated_at
        )


@pytest.mark.parametrize(
    ("fail_all", "expected_status", "event_type"),
    [(False, "partial_failure", "report_partial"), (True, "narrative_failed", "report_failed")],
)
async def test_assembled_career_degradation_emits_the_persisted_outcome(
    db_session: AsyncSession,
    career_profile: CareerProfile,
    career_worker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    fail_all: bool,
    expected_status: str,
    event_type: str,
) -> None:
    class DegradedProvider(MockCareerSegmentProvider):
        async def generate_segment(self, *, prompt: str, section_input: CareerSectionRenderInput) -> dict[str, Any]:
            if fail_all or section_input.section_key == CAREER_SECTION_ORDER[0]:
                raise RuntimeError("private provider diagnostic")
            return await super().generate_segment(prompt=prompt, section_input=section_input)

    monkeypatch.setattr(career, "_career_provider", DegradedProvider)
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    source = await _historical_report(db_session, career_profile)
    operation = await _queued_regeneration(db_session, career_profile, source)

    result = await career._generate_career_report_async(generation_id=operation, section_keys=[])
    assert result["status"] == expected_status

    async with career_worker() as readback:
        generation = await readback.scalar(select(CareerGeneration).where(CareerGeneration.generation_id == operation))
        assert generation is not None
        report = await readback.get(CareerReport, generation.report_id)
        assert report is not None and report.id != source.id
        assert generation.status == report.status == expected_status
        assert len(report.narrative_payload["sections"]) == (0 if fail_all else len(CAREER_SECTION_ORDER) - 1)
        await _assert_terminal_event(
            readback,
            generation,
            event_type=event_type,
            entity_id=operation if fail_all else report.id,
            occurred_at=generation.updated_at if fail_all else report.updated_at,
        )


@pytest.mark.parametrize("after_foundation", [False, True], ids=["deterministic", "narrative"])
@pytest.mark.parametrize("reject_outbox", [False, True], ids=["commit", "rollback"])
async def test_career_exception_failure_fact_is_atomic_with_the_failed_transition(
    db_session: AsyncSession,
    career_profile: CareerProfile,
    career_worker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    after_foundation: bool,
    reject_outbox: bool,
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", False)
    if after_foundation:
        source = await _historical_report(db_session, career_profile)
        operation = await _queued_regeneration(db_session, career_profile, source)
        sections = ["private invalid section key"]
        business_error = "Unknown Career section keys"
    else:
        operation, created = await _create_or_resume(db_session, career_profile, key="pre-foundation")
        assert created
        sections = []
        business_error = "Field required"  # Completed fixture has no answers.
    if reject_outbox:
        await db_session.execute(text("ALTER TABLE business_event_outbox ADD CONSTRAINT reject_failure CHECK (false)"))
    await db_session.commit()
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)

    if reject_outbox:
        with pytest.raises(IntegrityError, match="reject_failure"):
            await career._generate_career_report_async(generation_id=operation, section_keys=sections)
    else:
        with pytest.raises(ValueError, match=business_error):
            await career._generate_career_report_async(generation_id=operation, section_keys=sections)
        replay = await career._generate_career_report_async(generation_id=operation, section_keys=sections)
        assert replay["duplicate_delivery"] is True

    async with career_worker() as readback:
        (generation,) = (await readback.scalars(select(CareerGeneration))).all()
        assert generation.generation_id == operation
        if after_foundation:
            old_report, report = (await readback.scalars(select(CareerReport).order_by(CareerReport.version))).all()
            assert old_report.status == "ready"
            assert report.id == generation.report_id
            assert (
                report.status == generation.status == ("deterministic_ready" if reject_outbox else "narrative_failed")
            )
        else:
            assert generation.report_id is None
            assert generation.status == ("calculating_dimensions" if reject_outbox else "failed")
            assert not (await readback.scalars(select(CareerReport))).all()
        if reject_outbox:
            assert not (await readback.scalars(select(BusinessEvent))).all()
            assert not (await readback.scalars(select(BusinessEventOutbox))).all()
        else:
            await _assert_terminal_event(
                readback,
                generation,
                event_type="report_failed",
                entity_id=operation,
                occurred_at=generation.updated_at,
            )

    if reject_outbox:
        await db_session.execute(text("ALTER TABLE business_event_outbox DROP CONSTRAINT reject_failure"))
        await db_session.commit()
        assert await career._reconcile_career_publications() == 1
        async with career_worker() as readback:
            (generation,) = (await readback.scalars(select(CareerGeneration))).all()
            assert generation.pending_publication is None
            assert generation.status == ("narrative_failed" if after_foundation else "failed")
            await _assert_terminal_event(
                readback, generation, event_type="report_failed", entity_id=operation, occurred_at=generation.updated_at
            )


async def _assert_terminal_event(
    db: AsyncSession,
    generation: CareerGeneration,
    *,
    event_type: str,
    entity_id: UUID,
    occurred_at: datetime,
) -> None:
    (event,) = (await db.scalars(select(BusinessEvent).where(BusinessEvent.event_type != "report_requested"))).all()
    assert event.event_type == event_type
    assert event.semantic_key == f"v1:{event_type}:{entity_id}:-"
    assert event.entity_id == entity_id
    assert event.subject_id == generation.user_id
    assert event.occurred_at == occurred_at
    assert event.product == "career"
    assert event.mode == "unknown"
    assert event.source_id is None
    assert event.details == {}
    (delivery,) = (await db.scalars(select(BusinessEventOutbox).where(BusinessEventOutbox.event_id == event.id))).all()
    assert delivery.destination == "internal_projection"
    assert delivery.status == "pending"


@pytest.mark.parametrize(
    ("enabled", "section_keys", "expected_status"),
    [(False, [], "ready"), (True, [CAREER_SECTION_ORDER[0]], "generating_sections")],
    ids=["flag-off", "successful-subset-not-terminal"],
)
async def test_career_skips_terminal_emission_for_disabled_or_nonterminal_work(
    db_session: AsyncSession,
    career_profile: CareerProfile,
    career_worker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    enabled: bool,
    section_keys: list[str],
    expected_status: str,
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", False)
    source = await _historical_report(db_session, career_profile)
    operation = await _queued_regeneration(db_session, career_profile, source)
    await db_session.execute(text("ALTER TABLE business_event_outbox ADD CONSTRAINT no_terminal_event CHECK (false)"))
    await db_session.commit()
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", enabled)

    result = await career._generate_career_report_async(generation_id=operation, section_keys=section_keys)
    assert result["status"] == expected_status
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    replay = await career._generate_career_report_async(generation_id=operation, section_keys=section_keys)
    assert replay["duplicate_delivery"] is True

    async with career_worker() as readback:
        (generation,) = (await readback.scalars(select(CareerGeneration))).all()
        report = await readback.get(CareerReport, generation.report_id)
        assert report is not None
        assert generation.status == report.status == expected_status
        assert not (await readback.scalars(select(BusinessEvent))).all()
        assert not (await readback.scalars(select(BusinessEventOutbox))).all()


async def test_new_career_regeneration_after_failure_has_its_own_result(
    db_session: AsyncSession,
    career_profile: CareerProfile,
    career_worker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    source = await _historical_report(db_session, career_profile)
    first = await _queued_regeneration(db_session, career_profile, source, key="first-attempt")
    with pytest.raises(ValueError, match="Unknown Career section keys"):
        await career._generate_career_report_async(generation_id=first, section_keys=["invalid"])
    retry = await _queued_regeneration(db_session, career_profile, source, key="fresh-attempt")
    assert retry != first
    result = await career._generate_career_report_async(generation_id=retry, section_keys=[])
    assert result["status"] == "ready"

    async with career_worker() as readback:
        historical, failed, ready = (await readback.scalars(select(CareerReport).order_by(CareerReport.version))).all()
        assert historical.id == source.id and historical.status == "ready"
        assert failed.generation_id == first and failed.status == "narrative_failed"
        assert ready.generation_id == retry and ready.status == "ready"
        events = (await readback.scalars(select(BusinessEvent))).all()
        assert sorted((evt.event_type, evt.entity_id) for evt in events) == sorted(
            [
                ("report_requested", first),
                ("report_failed", first),
                ("report_requested", retry),
                ("report_ready", ready.id),
            ]
        )
        assert set(await readback.scalars(select(BusinessEventOutbox.event_id))) == {evt.id for evt in events}
