"""Real PostgreSQL proofs; TEST_DATABASE_URL must name a disposable database."""

import asyncio
import os
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, time, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import Connection, event, func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.core.exceptions import ValidationError
from app.modules.analytics.models import BusinessEvent, BusinessEventOutbox
from app.modules.analytics.repository import BusinessEventConflictError
from app.modules.analytics.schemas import BusinessEventInput, EventDetails, EventType, Mode, Product
from app.modules.analytics.service import claim_outbox, complete_outbox, emit_business_event, retry_outbox
from app.modules.astrotype_v2 import models as self_models
from app.modules.astrotype_v2 import router as self_router
from app.modules.astrotype_v2.api_runtime import build_generation_status_payload, build_report_read_payload_v2
from app.modules.astrotype_v2.repository import AstrotypeV2Repository
from app.modules.astrotype_v2.synthesis import NatalSynthesisV2
from app.modules.auth.models import EmailVerification, IdentityLink
from app.modules.auth.oauth.service import OAuthService
from app.modules.auth.service import AuthService
from app.modules.auth.verification import VerificationService
from app.modules.charts.models import ChartSnapshot
from app.modules.profiles.models import PersonProfile, ProfileActiveNatalReport, ProfileBirthDataRevision
from app.modules.profiles.refinement import BirthDataRevisionRepository, BirthDataSnapshot
from app.modules.users.models import User
from tests.conftest import test_engine
from tests.conftest import test_session_factory as session_factory
from workers.tasks import astrotype_v2 as self_worker

pytestmark = pytest.mark.skipif(
    os.getenv("E23_DISPOSABLE_TEST_DATABASES") != "1", reason="opt in only with dedicated E23 disposable databases"
)


@pytest.fixture
async def _setup_database() -> AsyncGenerator[None, None]:
    """Install only the two tables owned by the outbox in the disposable database."""
    metadata = BusinessEvent.metadata
    tables = tuple(metadata.tables[model.__tablename__] for model in (BusinessEvent, BusinessEventOutbox))
    async with test_engine.begin() as conn:
        if await conn.scalar(text("SELECT current_database()")) != "e23_tests":
            pytest.fail("outbox fixture requires the dedicated e23_tests database")
        for table in tables:
            if await conn.scalar(text("SELECT to_regclass(:name)"), {"name": table.name}) is not None:
                pytest.fail("outbox fixture refuses existing analytics tables")
        await conn.run_sync(metadata.create_all, tables=tables, checkfirst=False)
    try:
        yield
    finally:
        async with test_engine.begin() as conn:
            await conn.run_sync(metadata.drop_all, tables=tables)


NOW = datetime(2026, 1, 1, tzinfo=UTC)


def fact() -> BusinessEventInput:
    return BusinessEventInput(event_type=EventType.REGISTRATION_COMPLETED, entity_id=UUID(int=1), occurred_at=NOW)


@pytest.fixture
async def self_report_tables(registration_tables: None) -> AsyncGenerator[None, None]:
    metadata = self_models.NatalReport.metadata
    tables = (
        *(table for name, table in metadata.tables.items() if name.startswith("astrotype_v2_")),
        metadata.tables[ProfileActiveNatalReport.__tablename__],
        metadata.tables[ProfileBirthDataRevision.__tablename__],
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(metadata.create_all, tables=tables, checkfirst=False)
    try:
        yield
    finally:
        async with test_engine.begin() as conn:
            await conn.run_sync(metadata.drop_all, tables=tables)


@pytest.mark.usefixtures("self_report_tables")
@pytest.mark.parametrize(
    "scenario",
    [
        "off",
        "on",
        "outbox-failure",
        "concurrent-replay",
        "worker-loss",
        "disconnect",
        "complete",
        "partial",
        "terminal-outbox-failure",
        "refinement-replay",
        "refinement-beat",
    ],
)
async def test_self_basic_ready_is_committed_with_foundation_before_narrative(
    monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    enabled = scenario != "off"
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", enabled)
    monkeypatch.setattr(self_worker, "async_session_factory", session_factory)
    user_id, profile_id, generation_id = UUID(int=11), UUID(int=12), UUID(int=13)
    refinement = scenario.startswith("refinement-")
    outbox_failure = scenario == "terminal-outbox-failure" or refinement
    revision_id: UUID | None = None
    checkpointed_narrative: dict[str, object] | None = None
    async with session_factory() as session:
        session.add(User(id=user_id, email="self-owner@example.com", hashed_password="", is_verified=True))
        await session.flush()
        session.add(
            PersonProfile(
                id=profile_id,
                user_id=user_id,
                name="Fixture",
                birth_date=date(1990, 1, 1),
                birth_time=time(12),
                birth_time_accuracy="exact",
                birth_place="Moscow",
                latitude=55.75,
                longitude=37.61,
                timezone="Europe/Moscow",
            )
        )
        await session.flush()
        if refinement:
            accepted = await BirthDataRevisionRepository(session).create_revision(
                user_id=user_id,
                profile_id=profile_id,
                generation_id=generation_id,
                idempotency_key="fixture-revision",
                request_hash="a" * 64,
                new_snapshot=BirthDataSnapshot(
                    birth_time=time(13),
                    birth_time_accuracy="exact",
                    birth_place="Moscow",
                    latitude=55.75,
                    longitude=37.61,
                    timezone="Europe/Moscow",
                ),
            )
            revision_id = accepted.revision.id
        else:
            session.add(
                self_models.NatalReportGeneration(generation_id=generation_id, user_id=user_id, profile_id=profile_id)
            )
        if scenario == "outbox-failure":
            await session.execute(
                text("ALTER TABLE business_event_outbox ADD CONSTRAINT t03_self_outbox CHECK (false)")
            )
        await session.commit()

    observed_report_ids: list[UUID] = []
    real_narrative = self_worker._ensure_ready_segments

    async def narrative_probe(
        *,
        repository: AstrotypeV2Repository,
        chart_id: UUID,
        outline: self_models.ReportOutline,
        synthesis: NatalSynthesisV2,
    ) -> list[self_models.ReportSegmentGeneration]:
        async with session_factory() as fresh:
            report = (await fresh.scalars(select(self_models.NatalReport))).one()

            assert report.status == "narrative_generating"
            assert report.deterministic_payload
            assert report.infographic_data_id is not None
            events = (
                await fresh.scalars(select(BusinessEvent).where(BusinessEvent.event_type != "report_requested"))
            ).all()
            assert len(events) == int(enabled)
            assert await fresh.scalar(select(func.count()).select_from(BusinessEventOutbox)) == int(enabled) + int(
                refinement
            )
            if enabled:
                assert events[0].event_type == "basic_report_ready"
                assert (events[0].entity_id, events[0].subject_id) == (report.id, user_id)
                assert (events[0].product, events[0].occurred_at, events[0].details) == ("self", report.created_at, {})
            observed_report_ids.append(report.id)
        if scenario in {"complete", "partial"} or outbox_failure:
            if outbox_failure:
                async with session_factory.begin() as fresh:
                    await fresh.execute(
                        text(
                            "ALTER TABLE business_event_outbox "
                            "ADD CONSTRAINT t03_terminal_outbox CHECK (false) NOT VALID"
                        )
                    )
            segments = await real_narrative(
                repository=repository, chart_id=chart_id, outline=outline, synthesis=synthesis
            )
            if scenario == "partial":
                for segment in segments[1:]:
                    await repository.session.delete(segment)
                return segments[:1]
            return segments
        if scenario in {"worker-loss", "disconnect"}:
            persisted_outline = await repository.get_outline_for_chart(report.chart_id)
            assert persisted_outline is not None
            await repository.add(
                self_models.ReportSegmentGeneration(
                    chart_id=report.chart_id,
                    outline_id=persisted_outline.id,
                    section_key=persisted_outline.section_keys[0],
                    status="running",
                    provider="fixture",
                    model="fixture",
                    prompt_version="v1",
                    payload={},
                )
            )
            await repository.session.commit()
        if scenario == "disconnect":
            assert await self_worker._reconcile_interrupted_narratives(before=datetime.max.replace(tzinfo=UTC)) == 0
            owner_pid = await repository.session.scalar(text("SELECT pg_backend_pid()"))
            async with session_factory() as killer:
                assert await killer.scalar(text("SELECT pg_terminate_backend(:pid)"), {"pid": owner_pid})
            await repository.session.execute(text("SELECT 1"))
            pytest.fail("The fenced connection should be dead")
        if scenario == "worker-loss":
            raise asyncio.CancelledError
        return []

    monkeypatch.setattr(self_worker, "_ensure_ready_segments", narrative_probe)

    if scenario == "outbox-failure":
        with pytest.raises(IntegrityError):
            await self_worker._generate_natal_report_v2_async(
                user_id=str(user_id), profile_id=str(profile_id), generation_id=str(generation_id), force=True
            )
        assert observed_report_ids == []
        async with session_factory() as fresh:
            for model in (
                self_models.NatalReport,
                self_models.NatalChart,
                self_models.NatalFact,
                BusinessEvent,
                BusinessEventOutbox,
            ):
                assert await fresh.scalar(select(func.count()).select_from(model)) == 0
            await fresh.execute(text("ALTER TABLE business_event_outbox DROP CONSTRAINT t03_self_outbox"))
            await fresh.commit()

    async def force_same_generation() -> dict[str, object]:
        return await self_worker._generate_natal_report_v2_async(
            user_id=str(user_id),
            profile_id=str(profile_id),
            generation_id=str(generation_id),
            revision_id=str(revision_id) if revision_id is not None else None,
            force=True,
        )

    expected_status = "complete" if outbox_failure else scenario
    if expected_status not in {"complete", "partial"}:
        expected_status = "narrative_failed"
    if outbox_failure:
        with pytest.raises(IntegrityError):
            await force_same_generation()
        async with session_factory.begin() as fresh:
            pending = (await fresh.scalars(select(self_models.NatalReport))).one()
            assert pending.status == "narrative_generating"
            assert pending.pending_publication is not None and pending.pending_publication["status"] == "complete"
            checkpointed_narrative = pending.pending_publication["narrative_payload"]
            assert checkpointed_narrative and pending.narrative_payload != checkpointed_narrative
            assert await fresh.scalar(select(self_models.NatalReportGeneration.status)) == "narrative_generating"
            expected_events = {"basic_report_ready", "report_requested"} if refinement else {"basic_report_ready"}
            assert set((await fresh.scalars(select(BusinessEvent.event_type))).all()) == expected_events
            assert await fresh.scalar(select(func.count()).select_from(BusinessEventOutbox)) == len(expected_events)
            segment_count = await fresh.scalar(select(func.count()).select_from(self_models.ReportSegmentGeneration))
            assert segment_count is not None and segment_count > 0
            await fresh.execute(text("ALTER TABLE business_event_outbox DROP CONSTRAINT t03_terminal_outbox"))
        if scenario == "refinement-beat":
            cutoff = datetime.max.replace(tzinfo=UTC)
            assert await self_worker._reconcile_interrupted_narratives(before=cutoff) == 1
            assert await self_worker._reconcile_interrupted_narratives(before=cutoff) == 0
        result = await force_same_generation()
    elif scenario == "worker-loss":
        with pytest.raises(asyncio.CancelledError):
            await force_same_generation()
        result = await force_same_generation()
    elif scenario == "disconnect":
        with pytest.raises(DBAPIError):
            await force_same_generation()
        assert await self_worker._reconcile_interrupted_narratives(before=NOW) == 0
        cutoff = datetime.max.replace(tzinfo=UTC)
        assert await self_worker._reconcile_interrupted_narratives(before=cutoff) == 1
        assert await self_worker._reconcile_interrupted_narratives(before=cutoff) == 0
        result = await force_same_generation()
    elif scenario == "concurrent-replay":
        first, second = await asyncio.gather(force_same_generation(), force_same_generation())
        assert first["report_id"] == second["report_id"]
        result = next(item for item in (first, second) if item["status"] == "narrative_failed")
    else:
        result = await force_same_generation()
    assert result["report_status"] == expected_status
    assert len(observed_report_ids) == 1
    replayed = await force_same_generation()
    assert replayed["report_id"] == result["report_id"]
    assert replayed["status"] == result["status"]
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    reuse_id = UUID(int=14)
    async with session_factory() as session:
        session.add(self_models.NatalReportGeneration(generation_id=reuse_id, user_id=user_id, profile_id=profile_id))
        await session.commit()
    reused = await self_worker._generate_natal_report_v2_async(
        user_id=str(user_id), profile_id=str(profile_id), generation_id=str(reuse_id)
    )
    assert reused["status"] == "already_exists"
    assert len(observed_report_ids) == 1
    async with session_factory() as fresh:
        report = (await fresh.scalars(select(self_models.NatalReport))).one()
        assert str(report.id) == result["report_id"]
        assert report.status == expected_status
        assert report.pending_publication is None
        if checkpointed_narrative is not None:
            assert report.narrative_payload == checkpointed_narrative
        if revision_id is not None:
            readback_revision = await fresh.get(ProfileBirthDataRevision, revision_id)
            assert readback_revision is not None and readback_revision.status == "ready"
        if scenario in {"worker-loss", "disconnect"}:
            generation = (
                await fresh.scalars(
                    select(self_models.NatalReportGeneration).where(
                        self_models.NatalReportGeneration.generation_id == generation_id
                    )
                )
            ).one()
            assert generation.status == "narrative_failed"
            assert generation.diagnostics["error_code"] == "narrative_worker_interrupted"
            segments = list((await fresh.scalars(select(self_models.ReportSegmentGeneration))).all())
            assert len(segments) == 1 and segments[0].status == "running"  # shared outline, don't rewrite it
            payload = build_report_read_payload_v2(
                report=report, outline=None, infographic=None, facts=[], segments=segments
            )
            progress = payload["progress"]
            assert (progress["status"], progress["running_segments"]) == ("narrative_failed", 0)
            assert progress["segments"][0]["status"] == "failed"
            assert payload["segments"][0]["status"] == "failed"
            status = build_generation_status_payload(generation=generation, report=report, segments=segments)
            assert status["sections"][0]["segment_status"] == "failed"

            async def allow_basic_report(**_kwargs: object) -> None:
                pass

            monkeypatch.setattr(self_router, "_require_basic_report_access", allow_basic_report)
            for job_id, expected in ((generation_id, "narrative_failed"), (reuse_id, "already_exists")):
                polled = await self_router.get_v2_generation_status(job_id, fresh, user_id)
                assert polled["report_id"] == str(report.id)
                assert polled["status"] == expected
                assert polled["links"]["progress"].endswith(f"/{report.id}/progress")
                assert polled["sections"] and all(item["segment_status"] == "failed" for item in polled["sections"])
            with pytest.raises(HTTPException) as denied:
                await self_router.get_v2_generation_status(reuse_id, fresh, UUID(int=99))
            assert denied.value.status_code == 404
            assert (
                await AstrotypeV2Repository(fresh).get_report_for_user(
                    report_id=report.id, user_id=user_id, profile_id=UUID(int=99)
                )
                is None
            )
        events = {item.event_type: item for item in (await fresh.scalars(select(BusinessEvent))).all()}
        terminal_type = {"complete": "report_ready", "partial": "report_partial", "narrative_failed": "report_failed"}[
            expected_status
        ]
        if enabled:
            assert set(events) == (
                {"basic_report_ready", terminal_type, "report_requested"}
                if refinement
                else {"basic_report_ready", terminal_type}
            )
            terminal = events[terminal_type]
            assert terminal.entity_id == (generation_id if terminal_type == "report_failed" else report.id)
            assert (terminal.subject_id, terminal.product, terminal.details) == (user_id, "self", {})
            assert terminal.occurred_at == report.updated_at
        else:
            assert not events
        assert await fresh.scalar(select(func.count()).select_from(BusinessEventOutbox)) == len(events)


@pytest.mark.usefixtures("self_report_tables")
@pytest.mark.parametrize("scenario", ["off", "on", "outbox-failure"])
async def test_self_request_is_persisted_with_event_before_queue_dispatch(
    monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", scenario != "off")
    user_id, profile_id = UUID(int=11), UUID(int=12)
    async with session_factory.begin() as db:
        db.add(User(id=user_id, email="request-owner@example.invalid", hashed_password="", is_verified=True))
        await db.flush()
        db.add(
            PersonProfile(
                id=profile_id,
                user_id=user_id,
                name="Fixture",
                birth_date=date(1990, 1, 1),
                birth_place="Moscow",
                latitude=55.75,
                longitude=37.61,
                timezone="Europe/Moscow",
            )
        )
        if scenario == "outbox-failure":
            await db.execute(text("ALTER TABLE business_event_outbox ADD CHECK (false)"))

    calls: list[dict[str, object]] = []

    def dispatch(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)
        return SimpleNamespace(id="fixture-task-id")

    async with session_factory() as db:
        request = self_router._enqueue_persisted_v2_generation(
            repository=AstrotypeV2Repository(db),
            db=db,
            profile_id=profile_id,
            user_id=user_id,
            queue=SimpleNamespace(delay=dispatch),
            force=True,
        )
        if scenario == "outbox-failure":
            with pytest.raises(IntegrityError):
                await request
            await db.commit()
        else:
            accepted = await request
            assert accepted.status_code == 202
            assert calls == [
                {
                    "user_id": str(user_id),
                    "profile_id": str(profile_id),
                    "force": True,
                    "generation_id": accepted.payload["generation_id"],
                }
            ]

    async with session_factory() as fresh:
        jobs = list((await fresh.scalars(select(self_models.NatalReportGeneration))).all())
        events = list((await fresh.scalars(select(BusinessEvent))).all())
        if scenario == "outbox-failure":
            assert not calls and not jobs
        else:
            assert len(jobs) == 1 and jobs[0].celery_task_id == "fixture-task-id"
        if scenario == "on":
            assert len(events) == 1
            recorded = events[0]
            assert (recorded.entity_id, recorded.subject_id, recorded.product, recorded.occurred_at) == (
                jobs[0].generation_id,
                user_id,
                "self",
                jobs[0].created_at,
            )
            assert (recorded.event_type, recorded.details) == ("report_requested", {})
        else:
            assert not events
        assert await fresh.scalar(select(func.count()).select_from(BusinessEventOutbox)) == len(events)


@pytest.fixture
async def registration_tables(_setup_database: None) -> AsyncGenerator[None, None]:
    metadata = User.metadata
    tables = tuple(
        metadata.tables[model.__tablename__]
        for model in (User, PersonProfile, ChartSnapshot, EmailVerification, IdentityLink)
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(metadata.create_all, tables=tables, checkfirst=False)
    try:
        yield
    finally:
        async with test_engine.begin() as conn:
            await conn.run_sync(metadata.drop_all, tables=tables)


@pytest.mark.usefixtures("registration_tables")
@pytest.mark.parametrize("enabled,fail_outbox", [(False, False), (True, False), (True, True)])
async def test_registration_and_analytics_commit_together(
    monkeypatch: pytest.MonkeyPatch, enabled: bool, fail_outbox: bool
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", enabled)
    monkeypatch.setattr(settings, "AUTO_VERIFY_EMAIL", True)
    async with session_factory() as session:
        if fail_outbox:
            await session.execute(
                text("ALTER TABLE business_event_outbox ADD CONSTRAINT t03_reject_queue CHECK (false)")
            )
            await session.commit()
        signup = AuthService(session).register(
            "fixture@example.com",
            "fixture-password",
            "Fixture",
            date(1990, 5, 15),
            "Москва",
            55.75,
            37.61,
            "Europe/Moscow",
        )
        if fail_outbox:
            with pytest.raises(IntegrityError):
                await signup
        else:
            await signup
        await session.commit()

    async with session_factory() as fresh:
        users = (await fresh.scalars(select(User))).all()
        events = (await fresh.scalars(select(BusinessEvent))).all()
        account_count = 0 if fail_outbox else 1
        assert len(users) == account_count
        assert await fresh.scalar(select(func.count()).select_from(PersonProfile)) == account_count
        assert await fresh.scalar(select(func.count()).select_from(ChartSnapshot)) == account_count
        event_count = 1 if enabled and not fail_outbox else 0
        assert len(events) == event_count
        assert await fresh.scalar(select(func.count()).select_from(BusinessEventOutbox)) == event_count
        if event_count:
            assert events[0].entity_id == users[0].id
            assert events[0].occurred_at == users[0].created_at
            assert events[0].details == {"registration_method": "email"}


@pytest.mark.usefixtures("registration_tables")
@pytest.mark.parametrize("enabled", [False, True])
async def test_oauth_emits_only_for_new_account(monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", enabled)
    async with session_factory() as session:
        new = await OAuthService(session)._find_or_create_user("yandex", "provider-1", "new@example.com", "Name", None)
        await session.commit()
    async with session_factory() as session:
        returning = await OAuthService(session)._find_or_create_user(
            "yandex", "provider-1", "new@example.com", "Name", None
        )
        await session.commit()
        assert returning.id == new.id
    async with session_factory() as fresh:
        rows = (await fresh.scalars(select(BusinessEvent))).all()
        assert len(rows) == int(enabled)
        if enabled:
            assert rows[0].event_type == "registration_completed"
            assert rows[0].entity_id == new.id
            assert rows[0].occurred_at == new.created_at
            assert rows[0].details == {"registration_method": "oauth"}
        assert await fresh.scalar(select(func.count()).select_from(BusinessEventOutbox)) == int(enabled)


@pytest.mark.usefixtures("registration_tables")
@pytest.mark.parametrize("scenario", ["same-token", "race-oauth-link", "oauth-link-only"])
async def test_concurrent_verification_records_only_first_transition(
    monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    async with session_factory() as session:
        user = User(email="existing@example.com", hashed_password="", is_verified=False)
        session.add(user)
        await session.flush()
        token = await VerificationService(session).create_verification(user.id)
        await session.commit()

    async def verify() -> bool:
        async with session_factory() as attempt:
            try:
                await VerificationService(attempt).verify_email(token)
            except ValidationError:
                await attempt.rollback()
                return False
            await attempt.commit()
            return True

    async def link() -> bool:
        async with session_factory() as attempt:
            linked = await OAuthService(attempt)._find_or_create_user("yandex", "provider-2", user.email, None, None)
            assert linked.id == user.id
            await attempt.commit()
            return True

    if scenario == "oauth-link-only":
        assert await link()
        assert await verify()  # An unused token may still be consumed, without another transition.
    else:
        race_oauth = scenario == "race-oauth-link"
        results = await asyncio.gather(verify(), link() if race_oauth else verify())
        assert sum(results) == (2 if race_oauth else 1)
    async with session_factory() as fresh:
        stored = await fresh.get(User, user.id)
        assert stored is not None and stored.is_verified
        row = (await fresh.scalars(select(BusinessEvent))).one()
        assert row.event_type == "account_verified"
        assert row.entity_id == user.id
        assert row.details == {}
        assert await fresh.scalar(select(func.count()).select_from(BusinessEventOutbox)) == 1


@pytest.mark.usefixtures("registration_tables")
async def test_failed_verification_outbox_does_not_consume_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "BUSINESS_MONITORING_ENABLED", True)
    async with session_factory() as session:
        account = User(email="verify@example.com", hashed_password="", is_verified=False)
        session.add(account)
        await session.flush()
        account_id = account.id
        token = await VerificationService(session).create_verification(account_id)
        await session.execute(text("ALTER TABLE business_event_outbox ADD CHECK (false)"))
        await session.commit()
        with pytest.raises(IntegrityError):
            await VerificationService(session).verify_email(token)
        await session.commit()
    async with session_factory() as fresh:
        stored = await fresh.get(User, account_id)
        assert stored is not None and not stored.is_verified
        verification = (await fresh.scalars(select(EmailVerification))).one()
        assert verification.used_at is None
        assert await fresh.scalar(select(func.count()).select_from(BusinessEvent)) == 0
        assert await fresh.scalar(select(func.count()).select_from(BusinessEventOutbox)) == 0


@pytest.mark.usefixtures("_setup_database")
async def test_event_outbox_and_caller_mutation_rollback_together(db_session: AsyncSession) -> None:
    await db_session.execute(text("CREATE TABLE t02_caller_mutation (id integer PRIMARY KEY)"))
    await db_session.commit()
    await db_session.execute(text("INSERT INTO t02_caller_mutation VALUES (1)"))
    event = await emit_business_event(db_session, fact(), recorded_at=NOW)
    assert event.id is not None
    assert await db_session.scalar(select(func.count()).select_from(BusinessEventOutbox)) == 1
    await db_session.rollback()
    async with session_factory() as fresh:
        assert await fresh.scalar(select(func.count()).select_from(BusinessEvent)) == 0
        assert await fresh.scalar(select(func.count()).select_from(BusinessEventOutbox)) == 0
        assert await fresh.scalar(text("SELECT count(*) FROM t02_caller_mutation")) == 0
        await fresh.execute(text("DROP TABLE t02_caller_mutation"))
        await fresh.commit()


@pytest.mark.usefixtures("_setup_database")
async def test_committing_sessions_deduplicate_and_conflict_without_changing_history() -> None:
    async def emit() -> tuple[UUID, datetime]:
        async with session_factory() as session:
            event = await emit_business_event(session, fact(), recorded_at=NOW)
            result = (event.id, event.created_at)
            await session.commit()
            return result

    results = await asyncio.gather(emit(), emit())
    assert results[0] == results[1]
    async with session_factory() as session:
        replay = await emit_business_event(session, fact(), recorded_at=NOW + timedelta(days=1))
        assert (replay.id, replay.created_at) == results[0]
        await session.execute(text("CREATE TABLE t02_conflicting_caller_mutation (id integer PRIMARY KEY)"))
        changed = fact().model_copy(update={"mode": Mode.LIVE})
        with pytest.raises(BusinessEventConflictError, match=r"^business event identity conflicts with stored facts$"):
            await emit_business_event(session, changed, recorded_at=NOW)
        await session.commit()  # Catch-and-commit must not alter the event or outbox.
    async with session_factory() as session:
        assert await session.scalar(text("SELECT to_regclass('t02_conflicting_caller_mutation')")) is None
        events = (await session.scalars(select(BusinessEvent))).all()
        assert len(events) == 1
        assert events[0].mode == "unknown"
        assert events[0].created_at == NOW
        assert await session.scalar(select(func.count()).select_from(BusinessEventOutbox)) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"mode": Mode.TEST},
        {"subject_id": UUID(int=2)},
        {"product": Product.SELF},
        {"occurred_at": NOW + timedelta(seconds=1)},
        {"details": EventDetails(input_tokens=2)},
    ],
)
@pytest.mark.usefixtures("_setup_database")
async def test_every_business_fact_is_immutable_on_catch_and_commit(change: dict[str, object]) -> None:
    original = BusinessEventInput(
        event_type=EventType.PROVIDER_USAGE_OBSERVED,
        entity_id=UUID(int=3),
        occurred_at=NOW,
        details=EventDetails(input_tokens=1),
    )
    async with session_factory() as session:
        first = await emit_business_event(session, original, recorded_at=NOW)
        event_id = first.id
        await session.commit()
    async with session_factory() as session:
        with pytest.raises(BusinessEventConflictError):
            await emit_business_event(session, original.model_copy(update=change), recorded_at=NOW)
        await session.commit()
    async with session_factory() as session:
        row = (await session.scalars(select(BusinessEvent))).one()
        assert row.id == event_id
        assert row.mode == "unknown"
        assert row.subject_id is None
        assert row.product is None
        assert row.occurred_at == NOW
        assert row.details == {"input_tokens": 1}
        assert await session.scalar(select(func.count()).select_from(BusinessEventOutbox)) == 1


@pytest.mark.usefixtures("_setup_database")
async def test_claim_contention_restart_and_fencing() -> None:
    async with session_factory() as session:
        await emit_business_event(session, fact(), recorded_at=NOW)
        await session.commit()
    async with session_factory() as first, session_factory() as second:
        claim = await claim_outbox(first, now=NOW, lease_seconds=10)
        assert claim is not None
        assert await claim_outbox(second, now=NOW, lease_seconds=10) is None
        await second.commit()
        await first.commit()
    async with session_factory() as restarted:
        assert await claim_outbox(restarted, now=NOW + timedelta(seconds=9), lease_seconds=10) is None
        replacement = await claim_outbox(restarted, now=NOW + timedelta(seconds=10), lease_seconds=10)
        assert replacement is not None
        assert replacement.outbox_id == claim.outbox_id
        assert replacement.token != claim.token
        await restarted.commit()
    async with session_factory() as stale:
        assert not await complete_outbox(stale, claim, now=NOW + timedelta(seconds=11))
        assert not await retry_outbox(stale, claim, now=NOW + timedelta(seconds=11), delay_seconds=1)
        assert await complete_outbox(stale, replacement, now=NOW + timedelta(seconds=11))
        assert not await complete_outbox(stale, replacement, now=NOW + timedelta(seconds=11))
        await stale.commit()
    async with session_factory() as fresh:
        row = (await fresh.scalars(select(BusinessEventOutbox))).one()
        assert row.status == "delivered"
        assert row.attempts == 2
        assert row.claim_token is None
        assert row.delivered_at == NOW + timedelta(seconds=11)
        assert await claim_outbox(fresh, now=NOW + timedelta(days=1), lease_seconds=10) is None


@pytest.mark.usefixtures("_setup_database")
async def test_retry_budget_delay_and_expired_completion() -> None:
    async with session_factory() as session:
        await emit_business_event(session, fact(), recorded_at=NOW)
        await session.commit()
    async with session_factory() as session:
        for invalid in (0, -1, 3601, True):
            with pytest.raises(ValueError):
                await claim_outbox(session, now=NOW, lease_seconds=invalid)
        with pytest.raises(ValueError):
            await claim_outbox(session, now=datetime(2026, 1, 1), lease_seconds=1)
        for attempt in range(10):
            clock = NOW + timedelta(seconds=attempt * 3)
            claim = await claim_outbox(session, now=clock, lease_seconds=2)
            assert claim is not None
            if attempt == 0:
                for invalid in (0, -1, 86401, True):
                    with pytest.raises(ValueError):
                        await retry_outbox(session, claim, now=clock, delay_seconds=invalid)
            if attempt == 9:
                assert not await complete_outbox(session, claim, now=clock + timedelta(seconds=2))
            else:
                assert await retry_outbox(session, claim, now=clock, delay_seconds=3)
                assert await claim_outbox(session, now=clock + timedelta(seconds=2), lease_seconds=2) is None
            await session.commit()
        assert await claim_outbox(session, now=NOW + timedelta(days=2), lease_seconds=2) is None
        row = (await session.scalars(select(BusinessEventOutbox))).one()
        assert row.attempts == 10
        assert row.status == "pending"


@pytest.mark.usefixtures("_setup_database")
@pytest.mark.parametrize("cancel_enqueue", [False, True], ids=["integrity-error", "cancelled"])
async def test_queue_failure_caught_then_commit_cannot_leave_an_orphan_event(cancel_enqueue: bool) -> None:
    def cancel_outbox_insert(_conn: Connection, _cursor: object, statement: str, *_args: object) -> None:
        if statement.startswith("INSERT INTO business_event_outbox "):
            raise asyncio.CancelledError

    async with session_factory() as session:
        if not cancel_enqueue:
            await session.execute(
                text("ALTER TABLE business_event_outbox ADD CONSTRAINT t02_reject_queue CHECK (false)")
            )
            await session.commit()
        await session.execute(text("CREATE TABLE t02_queue_failure_caller (id integer PRIMARY KEY)"))
        if cancel_enqueue:
            event.listen((await session.connection()).sync_connection, "before_cursor_execute", cancel_outbox_insert)
        with pytest.raises(asyncio.CancelledError if cancel_enqueue else IntegrityError):
            await emit_business_event(session, fact(), recorded_at=NOW)
        await session.commit()
    async with session_factory() as session:
        assert await session.scalar(text("SELECT to_regclass('t02_queue_failure_caller')")) is None
        assert await session.scalar(select(func.count()).select_from(BusinessEvent)) == 0
        assert await session.scalar(select(func.count()).select_from(BusinessEventOutbox)) == 0


@pytest.mark.usefixtures("_setup_database")
async def test_payment_binding_mismatch_aborts_caller_write() -> None:
    payment = BusinessEventInput(
        event_type=EventType.PAYMENT_CONFIRMED, entity_id=UUID(int=9), source_id=UUID(int=10), occurred_at=NOW
    )
    async with session_factory() as session:
        receipt = await emit_business_event(session, payment, recorded_at=NOW)
        await session.commit()
        assert await emit_business_event(session, payment, recorded_at=NOW) == receipt
        await session.execute(text("CREATE TABLE t02_payment_conflict_caller (id integer PRIMARY KEY)"))
        with pytest.raises(BusinessEventConflictError):
            await emit_business_event(session, payment.model_copy(update={"source_id": UUID(int=11)}), recorded_at=NOW)
        await session.commit()
    async with session_factory() as session:
        assert await session.scalar(text("SELECT to_regclass('t02_payment_conflict_caller')")) is None
        stored = (await session.scalars(select(BusinessEvent))).one()
        assert (stored.id, stored.source_id) == (receipt.id, payment.source_id)
        assert await session.scalar(select(func.count()).select_from(BusinessEventOutbox)) == 1


@pytest.mark.usefixtures("_setup_database")
async def test_replay_compares_database_json_not_mutated_identity_map() -> None:
    original = BusinessEventInput(
        event_type=EventType.PROVIDER_USAGE_OBSERVED,
        entity_id=UUID(int=9),
        occurred_at=NOW,
        details=EventDetails(input_tokens=1),
    )
    async with session_factory() as session:
        receipt = await emit_business_event(session, original, recorded_at=NOW)
        await session.commit()
        row = (await session.scalars(select(BusinessEvent))).one()
        row.details["input_tokens"] = 2
        assert await emit_business_event(session, original, recorded_at=NOW) == receipt
        with pytest.raises(BusinessEventConflictError):
            await emit_business_event(
                session, original.model_copy(update={"details": EventDetails(input_tokens=2)}), recorded_at=NOW
            )


@pytest.mark.usefixtures("_setup_database")
async def test_claim_rollback_does_not_consume_attempt_or_leave_valid_token() -> None:
    async with session_factory() as session:
        await emit_business_event(session, fact(), recorded_at=NOW)
        await session.commit()
        discarded = await claim_outbox(session, now=NOW, lease_seconds=10)
        assert discarded is not None
        await session.rollback()
    async with session_factory() as session:
        current = await claim_outbox(session, now=NOW, lease_seconds=10)
        assert current is not None
        assert current.token != discarded.token
        assert not await complete_outbox(session, discarded, now=NOW)
        assert await complete_outbox(session, current, now=NOW)
        await session.commit()
    async with session_factory() as session:
        row = (await session.scalars(select(BusinessEventOutbox))).one()
        assert row.attempts == 1
        assert row.status == "delivered"


MIGRATION_DATABASE_URL = os.getenv("BUSINESS_EVENT_MIGRATION_DATABASE_URL")


@pytest.fixture
async def migration_sessions() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    if MIGRATION_DATABASE_URL is None:
        pytest.skip("set BUSINESS_EVENT_MIGRATION_DATABASE_URL to a dedicated disposable migration database")
    engine = create_async_engine(MIGRATION_DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as conn:
        if await conn.scalar(text("SELECT current_database()")) != "e23_migration":
            pytest.fail("migration test requires the dedicated e23_migration database")
        if await conn.scalar(text("SELECT current_schemas(false)")) != ["public"]:
            pytest.fail("migration test requires public as the only effective search path")
        if await conn.scalar(
            text("""
            SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                           WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema')
        """)
        ):
            pytest.fail("migration test requires a database with no existing user relations")
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def migration(*arguments: str) -> tuple[int, str]:
    import sys

    assert MIGRATION_DATABASE_URL is not None
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alembic",
        *arguments,
        env={**os.environ, "DATABASE_URL": MIGRATION_DATABASE_URL, "LLM_ENABLED": "false"},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    output, _ = await asyncio.wait_for(process.communicate(), timeout=120)
    assert process.returncode is not None
    return process.returncode, output.decode()


async def test_migration_roundtrip_live_schema_parity_and_nonempty_guard(
    migration_sessions: async_sessionmaker[AsyncSession],
) -> None:
    from sqlalchemy import Connection, MetaData, Table, inspect

    session_factory = migration_sessions

    from app.modules.analytics.models import BusinessEvent, BusinessEventOutbox

    code, output = await migration("upgrade", "head")
    assert code == 0, output

    def parity(connection: Connection) -> None:
        connection.execute(text("CREATE SCHEMA t02_expected"))
        expected = MetaData(schema="t02_expected")
        for model in (BusinessEvent, BusinessEventOutbox):
            table = model.__table__
            assert isinstance(table, Table)
            table.to_metadata(expected, schema="t02_expected")
        expected.create_all(connection)
        inspector = inspect(connection)
        for model in (BusinessEvent, BusinessEventOutbox):
            table = model.__table__
            assert isinstance(table, Table)
            for actual, reference in zip(
                sorted(inspector.get_columns(table.name), key=lambda column: column["name"]),
                sorted(inspector.get_columns(table.name, schema="t02_expected"), key=lambda column: column["name"]),
                strict=True,
            ):
                assert (actual["name"], str(actual["type"]), actual["nullable"], actual["default"]) == (
                    reference["name"],
                    str(reference["type"]),
                    reference["nullable"],
                    reference["default"],
                )
            definitions = text(
                "SELECT c.conname, pg_get_constraintdef(c.oid) FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "JOIN pg_namespace n ON n.oid = t.relnamespace "
                "WHERE t.relname = :table AND n.nspname = :schema ORDER BY c.conname"
            )
            actual_constraints = connection.execute(definitions, {"table": table.name, "schema": "public"}).all()
            expected_constraints = connection.execute(
                definitions, {"table": table.name, "schema": "t02_expected"}
            ).all()
            assert [(name, definition.replace("t02_expected.", "")) for name, definition in expected_constraints] == [
                (name, definition) for name, definition in actual_constraints
            ]
            assert {column["name"] for column in inspector.get_columns(table.name)} == set(table.columns.keys())
            assert {
                (index["name"], tuple(index["column_names"]), index["unique"])
                for index in inspector.get_indexes(table.name)
                if not index.get("duplicates_constraint")
            } == {(index.name, tuple(column.name for column in index.columns), index.unique) for index in table.indexes}
            assert {item["name"] for item in inspector.get_check_constraints(table.name)} == {
                item.name for item in table.constraints if item.__class__.__name__ == "CheckConstraint"
            }
            assert {item["name"] for item in inspector.get_unique_constraints(table.name)} == {
                item.name for item in table.constraints if item.__class__.__name__ == "UniqueConstraint"
            }
        expected.drop_all(connection)
        connection.execute(text("DROP SCHEMA t02_expected"))

    async with session_factory() as session:
        await (await session.connection()).run_sync(parity)
        await session.execute(text("CREATE TABLE t02_migration_sentinel (id integer PRIMARY KEY)"))
        await session.execute(text("INSERT INTO t02_migration_sentinel VALUES (42)"))
        await session.commit()
    code, output = await migration("downgrade", "a8b9c0d1e2f3")
    assert code == 0, output
    async with session_factory() as session:
        assert await session.scalar(text("SELECT id FROM t02_migration_sentinel")) == 42
        assert await session.scalar(text("SELECT to_regclass('business_events')")) is None
    code, output = await migration("upgrade", "head")
    assert code == 0, output
    async with session_factory() as session:
        await (await session.connection()).run_sync(parity)
        await emit_business_event(session, fact(), recorded_at=NOW)
        await session.commit()
    for sql in (
        "UPDATE business_events SET mode = 'test'",
        "DELETE FROM business_events",
        "TRUNCATE business_events CASCADE",
    ):
        async with session_factory() as session:
            with pytest.raises(DBAPIError, match="business events are append-only"):
                await session.execute(text(sql))
    code, output = await migration("downgrade", "a8b9c0d1e2f3")
    assert code != 0
    assert "nonempty business monitoring history" in output
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(BusinessEvent)) == 1
        assert await session.scalar(select(func.count()).select_from(BusinessEventOutbox)) == 1
        assert await session.scalar(text("SELECT id FROM t02_migration_sentinel")) == 42
