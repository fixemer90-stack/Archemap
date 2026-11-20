"""Resume and create fencing regressions; only disposable PostgreSQL fixtures."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.main import app
from app.modules.astrotype_v2.models import NatalChart
from app.modules.career import models
from app.modules.career import router as career_router
from app.modules.career.api_schemas import CreateCareerReportRequest
from app.modules.career.questionnaire import QUESTIONNAIRE_VERSION
from app.modules.career.repository import CareerRepository
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User
from tests.conftest import test_session_factory as session_factory


@pytest.fixture
async def resume_profile(
    _setup_database: None,
    db_session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[models.CareerProfile]:
    del _setup_database, client
    user = User(
        email=f"resume-{uuid.uuid4()}@example.com",
        name="Resume",
        is_active=True,
        is_verified=True,
        hashed_password="not-used",  # noqa: S106 - inert fixture
    )
    db_session.add(user)
    await db_session.flush()
    person = PersonProfile(
        user_id=user.id,
        name="Resume",
        birth_date=date(1990, 1, 1),
        birth_place="Test",
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
        input_hash=uuid.uuid4().hex * 2,
        birth_datetime_utc=datetime(1990, 1, 1, tzinfo=UTC),
        timezone="UTC",
        latitude=0,
        longitude=0,
        house_system="P",
        calculation_payload={},
    )
    db_session.add(chart)
    await db_session.flush()
    profile = models.CareerProfile(
        user_id=user.id,
        profile_id=person.id,
        chart_id=chart.id,
        generation_id=uuid.uuid4(),
        idempotency_key="bootstrap",
        scoring_version="test",
        reference_version="test",
        questionnaire_version=QUESTIONNAIRE_VERSION,
    )
    db_session.add(profile)
    await db_session.flush()
    db_session.add(
        models.CareerQuestionnaireSession(
            career_profile_id=profile.id,
            chart_id=chart.id,
            status="completed",
            questionnaire_version=QUESTIONNAIRE_VERSION,
            context_version="test",
            consent_version="test",
            answers_hash="a" * 64,
        )
    )
    await db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: user.id
    monkeypatch.setattr("app.modules.career.router.settings.CAREER_REPORT_ENABLED", True)
    monkeypatch.setattr("app.modules.career.router._require_career_access", AsyncMock())
    monkeypatch.setattr("app.modules.career.router._enqueue_generation", AsyncMock())
    monkeypatch.setattr("app.api.middleware._increment_rate_limit", AsyncMock(return_value=1))
    yield profile
    # client may be requested before this fixture; release reads before schema teardown.
    await db_session.rollback()


async def test_current_report_is_null_without_generation(
    client: AsyncClient,
    resume_profile: models.CareerProfile,
) -> None:
    response = await client.get("/api/v1/career/reports/current", params={"profile_id": str(resume_profile.profile_id)})
    assert response.status_code == 200
    assert response.json() is None


async def _saved_generation(
    db: AsyncSession,
    profile: models.CareerProfile,
    *,
    status: str,
    operation: str = "create",
) -> models.CareerGeneration:
    generation = models.CareerGeneration(
        generation_id=uuid.uuid4(),
        user_id=profile.user_id,
        career_profile_id=profile.id,
        chart_id=profile.chart_id,
        operation=operation,
        idempotency_key=uuid.uuid4().hex,
        status=status,
        diagnostics={},
    )
    db.add(generation)
    await db.commit()
    return generation


@pytest.mark.parametrize(
    "saved_status",
    [
        "queued",
        "calculating_dimensions",
        "deterministic_ready",
        "generating_sections",
        "ready",
        "partial_failure",
        "narrative_failed",
        "failed",
    ],
)
async def test_fresh_create_key_resumes_saved_attempt_without_dispatch(
    client: AsyncClient,
    resume_profile: models.CareerProfile,
    db_session: AsyncSession,
    saved_status: str,
) -> None:
    generation = await _saved_generation(db_session, resume_profile, status=saved_status)
    report = None
    if saved_status in {"deterministic_ready", "generating_sections", "ready", "partial_failure", "narrative_failed"}:
        report = models.CareerReport(
            career_profile_id=resume_profile.id,
            chart_id=resume_profile.chart_id,
            generation_id=generation.generation_id,
            idempotency_key="saved-report",
            version=1,
            status=saved_status,
            scoring_version="test",
            reference_version="test",
            questionnaire_version=QUESTIONNAIRE_VERSION,
            prompt_version="test",
            deterministic_payload={"saved": "untouched"},
            narrative_payload={},
            assembled_payload={"saved": "untouched"},
        )
        db_session.add(report)
        await db_session.flush()
        generation.report_id = report.id
        db_session.add(
            models.CareerSegmentGeneration(
                career_profile_id=resume_profile.id,
                chart_id=resume_profile.chart_id,
                generation_id=generation.generation_id,
                section_key="professional_summary",
                status="ready",
                prompt_version="test",
                input_payload={},
                output_payload={"body": "Saved body"},
            )
        )
        await db_session.commit()
    current = await client.get("/api/v1/career/reports/current", params={"profile_id": str(resume_profile.profile_id)})
    assert current.status_code == 200
    assert current.json()["generation_id"] == str(generation.generation_id)
    assert current.json()["status"] == saved_status
    response = await client.post(
        "/api/v1/career/reports",
        json={"profile_id": str(resume_profile.profile_id)},
        headers={"Idempotency-Key": "fresh-on-reentry"},
    )
    assert response.status_code == 202
    assert response.json()["generation_id"] == str(generation.generation_id)
    assert response.json()["status"] == saved_status
    if report is not None:
        assert current.json()["report_id"] == response.json()["report_id"] == str(report.id)
        assert current.json()["progress"]["ready"] == 1
        await db_session.refresh(report)
        assert report.deterministic_payload == report.assembled_payload == {"saved": "untouched"}
        segments = await CareerRepository(db_session).list_segments_for_generation(generation.generation_id)
        assert len(segments) == 1
        assert segments[0].output_payload == {"body": "Saved body"}
    assert await db_session.scalar(select(func.count()).select_from(models.CareerGeneration)) == 1
    assert isinstance(career_router._enqueue_generation, AsyncMock)
    career_router._enqueue_generation.assert_not_awaited()


async def test_rollover_requires_explicit_regeneration_without_relabeling_saved_report(
    client: AsyncClient,
    resume_profile: models.CareerProfile,
    db_session: AsyncSession,
) -> None:
    generation = await _saved_generation(db_session, resume_profile, status="ready")
    report = models.CareerReport(
        career_profile_id=resume_profile.id,
        chart_id=resume_profile.chart_id,
        generation_id=generation.generation_id,
        idempotency_key="old-report",
        version=1,
        status="ready",
        scoring_version="test",
        reference_version="test",
        questionnaire_version="career-q-old",
        prompt_version="test",
        deterministic_payload={},
        narrative_payload={},
        assembled_payload={},
    )
    db_session.add(report)
    await db_session.flush()
    generation.report_id = report.id
    await db_session.commit()
    current = await client.get("/api/v1/career/reports/current", params={"profile_id": str(resume_profile.profile_id)})
    assert current.status_code == 200
    assert current.json()["report_id"] == str(report.id)
    response = await client.post(
        "/api/v1/career/reports",
        json={"profile_id": str(resume_profile.profile_id)},
        headers={"Idempotency-Key": "new-answers-new-key"},
    )
    assert response.status_code == 409
    assert "regenerate" in response.json()["detail"].lower()
    assert isinstance(career_router._enqueue_generation, AsyncMock)
    career_router._enqueue_generation.assert_not_awaited()
    await db_session.refresh(report)
    assert report.questionnaire_version == "career-q-old"
    replay = await client.post(
        "/api/v1/career/reports",
        json={"profile_id": str(resume_profile.profile_id)},
        headers={"Idempotency-Key": generation.idempotency_key},
    )
    assert replay.status_code == 202
    assert replay.json()["generation_id"] == str(generation.generation_id)


async def test_distinct_concurrent_create_keys_dispatch_once_with_postgresql_row_fence(
    resume_profile: models.CareerProfile,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Both sessions observe no generation absent the row fence. Hold the first
    # lookup long enough for the second independent connection to contend.
    original = CareerRepository.get_latest_generation

    async def slow_latest(self: CareerRepository, **kwargs: uuid.UUID) -> models.CareerGeneration | None:
        result = await original(self, **kwargs)
        await asyncio.sleep(0.1)
        return result

    monkeypatch.setattr(CareerRepository, "get_latest_generation", slow_latest)

    async def create(key: str) -> bytes:
        async with session_factory() as session:
            response = await career_router.create_career_report(
                body=CreateCareerReportRequest(profile_id=resume_profile.profile_id),
                idempotency_key=key,
                db=session,
                current_user=resume_profile.user_id,
            )
            return bytes(response.body)

    first, second = await asyncio.gather(create("distinct-first"), create("distinct-second"))
    assert first == second
    assert isinstance(career_router._enqueue_generation, AsyncMock)
    career_router._enqueue_generation.assert_awaited_once()
    count = await db_session.scalar(select(func.count()).select_from(models.CareerGeneration))
    assert count == 1


async def test_exact_key_replays_after_questionnaire_rollover_even_before_new_completion(
    client: AsyncClient,
    resume_profile: models.CareerProfile,
    db_session: AsyncSession,
) -> None:
    saved = await _saved_generation(db_session, resume_profile, status="failed")
    await db_session.execute(delete(models.CareerQuestionnaireSession))
    await db_session.commit()
    response = await client.post(
        "/api/v1/career/reports",
        json={"profile_id": str(resume_profile.profile_id)},
        headers={"Idempotency-Key": saved.idempotency_key},
    )
    assert response.status_code == 202
    assert response.json()["generation_id"] == str(saved.generation_id)


async def test_current_route_checks_ownership_and_access_before_loading_artifacts(
    client: AsyncClient,
    resume_profile: models.CareerProfile,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _saved_generation(db_session, resume_profile, status="ready")
    generation_read = AsyncMock(side_effect=AssertionError("protected generation read"))
    report_read = AsyncMock(side_effect=AssertionError("protected report read"))
    segment_read = AsyncMock(side_effect=AssertionError("protected section read"))
    monkeypatch.setattr(CareerRepository, "get_latest_generation", generation_read)
    monkeypatch.setattr(CareerRepository, "get_report_by_generation_id", report_read)
    monkeypatch.setattr(CareerRepository, "list_segments_for_generation", segment_read)
    access = AsyncMock(side_effect=HTTPException(status_code=402, detail="locked"))
    monkeypatch.setattr(career_router, "_require_career_access", access)
    params = {"profile_id": str(resume_profile.profile_id)}
    locked = await client.get("/api/v1/career/reports/current", params=params)
    assert locked.status_code == 402
    access.assert_awaited_once()
    access.reset_mock()
    app.dependency_overrides[get_current_user] = lambda: uuid.uuid4()
    foreign = await client.get("/api/v1/career/reports/current", params=params)
    assert foreign.status_code == 404
    access.assert_not_awaited()
    for read in (generation_read, report_read, segment_read):
        read.assert_not_awaited()


async def test_owned_chart_without_career_profile_returns_null_without_bootstrapping(
    client: AsyncClient,
    resume_profile: models.CareerProfile,
    db_session: AsyncSession,
) -> None:
    person_id = resume_profile.profile_id
    await db_session.execute(delete(models.CareerProfile))
    await db_session.commit()
    response = await client.get("/api/v1/career/reports/current", params={"profile_id": str(person_id)})
    assert response.status_code == 200
    assert response.json() is None
    assert await db_session.scalar(select(func.count()).select_from(models.CareerProfile)) == 0
    assert await db_session.scalar(select(func.count()).select_from(models.CareerGeneration)) == 0
    missing = await client.get("/api/v1/career/reports/current", params={"profile_id": str(uuid.uuid4())})
    assert missing.status_code == 404


async def test_exact_cross_target_key_is_rejected_before_returning_current(
    resume_profile: models.CareerProfile,
    db_session: AsyncSession,
) -> None:
    from app.modules.career.repository import CareerGenerationTargetMismatchError

    original = await _saved_generation(db_session, resume_profile, status="ready")
    other = models.CareerProfile(
        user_id=resume_profile.user_id,
        profile_id=resume_profile.profile_id,
        chart_id=resume_profile.chart_id,
        generation_id=uuid.uuid4(),
        idempotency_key="another-target",
        scoring_version="test",
        reference_version="test",
        questionnaire_version=QUESTIONNAIRE_VERSION,
    )
    db_session.add(other)
    await db_session.commit()
    await _saved_generation(db_session, other, status="failed")
    repository = CareerRepository(db_session)
    with pytest.raises(CareerGenerationTargetMismatchError):
        await repository.resume_or_create_generation(
            profile=other,
            user_id=other.user_id,
            idempotency_key=original.idempotency_key,
            questionnaire=None,
        )
    assert await db_session.scalar(select(func.count()).select_from(models.CareerGeneration)) == 2


async def test_current_is_latest_regeneration_with_deterministic_tie_break_not_latest_success(
    client: AsyncClient,
    resume_profile: models.CareerProfile,
    db_session: AsyncSession,
) -> None:
    older = await _saved_generation(db_session, resume_profile, status="ready")
    newer = await _saved_generation(db_session, resume_profile, status="failed", operation="regenerate")
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    older.created_at = newer.created_at = timestamp
    older.id = uuid.UUID(int=1)
    newer.id = uuid.UUID(int=2)
    await db_session.commit()
    current = await client.get("/api/v1/career/reports/current", params={"profile_id": str(resume_profile.profile_id)})
    assert current.status_code == 200
    assert current.json()["generation_id"] == str(newer.generation_id)
    assert current.json()["status"] == "failed"
    fresh = await client.post(
        "/api/v1/career/reports",
        json={"profile_id": str(resume_profile.profile_id)},
        headers={"Idempotency-Key": "fresh-after-regeneration"},
    )
    assert fresh.status_code == 202
    assert fresh.json()["generation_id"] == str(newer.generation_id)
    replay = await client.post(
        "/api/v1/career/reports",
        json={"profile_id": str(resume_profile.profile_id)},
        headers={"Idempotency-Key": older.idempotency_key},
    )
    assert replay.status_code == 202
    assert replay.json()["generation_id"] == str(older.generation_id)
    assert isinstance(career_router._enqueue_generation, AsyncMock)
    career_router._enqueue_generation.assert_not_awaited()
