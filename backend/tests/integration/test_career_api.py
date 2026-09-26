from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.main import app
from app.modules.astrotype_v2.models import NatalChart
from app.modules.authorization.models import Entitlement
from app.modules.career import models
from app.modules.career.repository import CareerGenerationTargetMismatchError, CareerRepository
from app.modules.payments.models import Payment
from app.modules.profiles.models import PersonProfile
from app.modules.reports.models import Report
from app.modules.users.models import User
from tests.conftest import test_session_factory as session_factory


async def _call_career_route_matrix(
    client: AsyncClient,
    *,
    profile_id: uuid.UUID,
    questionnaire_id: uuid.UUID,
    generation_id: uuid.UUID,
    report_id: uuid.UUID,
) -> list[Response]:
    return [
        await client.get("/api/v1/career/questionnaires/current", params={"profile_id": str(profile_id)}),
        await client.put(
            f"/api/v1/career/questionnaires/{questionnaire_id}/answers",
            json={"answers": {}},
        ),
        await client.post(
            f"/api/v1/career/questionnaires/{questionnaire_id}/complete",
            headers={"Idempotency-Key": "access-complete"},
        ),
        await client.post(
            "/api/v1/career/reports",
            json={"profile_id": str(profile_id)},
            headers={"Idempotency-Key": "access-create"},
        ),
        await client.get(f"/api/v1/career/generations/{generation_id}"),
        await client.get(f"/api/v1/career/reports/{report_id}"),
        await client.get(f"/api/v1/career/reports/{report_id}/sections"),
        await client.post(
            f"/api/v1/career/reports/{report_id}/regenerate",
            json={"section_keys": []},
            headers={"Idempotency-Key": "access-regenerate"},
        ),
        await client.get(f"/api/v1/career/reports/{report_id}/versions"),
        await client.get(f"/api/v1/career/reports/{report_id}/pdf"),
    ]


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_career_api_persists_lifecycle_idempotency_and_locked_payload(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    chart_id = uuid.uuid4()
    career_profile_id = uuid.uuid4()
    questionnaire_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"career-{user_id}@example.com",
        name="Алина",
        hashed_password="not-used",  # noqa: S106 - inert fixture value
        is_active=True,
        is_verified=True,
    )
    person = PersonProfile(
        id=profile_id,
        user_id=user_id,
        name="Алина",
        birth_date=date(1990, 1, 1),
        birth_time=time(12, 0),
        birth_time_accuracy="exact",
        birth_place="Москва",
        latitude=55.75,
        longitude=37.61,
        timezone="Europe/Moscow",
    )
    chart = NatalChart(
        id=chart_id,
        user_id=user_id,
        profile_id=profile_id,
        engine_version="0.1.5",
        input_hash="a" * 64,
        birth_datetime_utc=datetime(1990, 1, 1, 9, 0, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.75,
        longitude=37.61,
        house_system="P",
        calculation_payload={},
    )
    career_profile = models.CareerProfile(
        id=career_profile_id,
        user_id=user_id,
        profile_id=profile_id,
        chart_id=chart_id,
        generation_id=uuid.uuid4(),
        idempotency_key="questionnaire-bootstrap",
        status="questionnaire_completed",
        version=1,
        scoring_version="career-mvp-1",
        reference_version="career-ref-1",
        questionnaire_version="career-q-1",
    )
    questionnaire = models.CareerQuestionnaireSession(
        id=questionnaire_id,
        career_profile_id=career_profile_id,
        chart_id=chart_id,
        status="completed",
        questionnaire_version="career-q-1",
        context_version="career-context-1",
        consent_version="career-consent-1",
        completion_idempotency_key="complete-1",
        answers_hash="b" * 64,
    )
    generation = models.CareerGeneration(
        generation_id=generation_id,
        user_id=user_id,
        career_profile_id=career_profile_id,
        chart_id=chart_id,
        operation="create",
        idempotency_key="queued-1",
        status="queued",
        diagnostics={},
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(person)
    await db_session.flush()
    db_session.add(chart)
    await db_session.flush()
    db_session.add(career_profile)
    await db_session.flush()
    db_session.add_all([questionnaire, generation])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user_id

    async def allow_access(*, db: AsyncSession, user_id: uuid.UUID) -> None:
        del db, user_id

    monkeypatch.setattr("app.modules.career.router._require_career_access", allow_access)
    monkeypatch.setattr("app.modules.career.router.settings.CAREER_REPORT_ENABLED", True)

    legacy_report = Report(
        user_id=user_id,
        profile_id=profile_id,
        product="career",
        status="ready",
        report_data={"legacy_marker": "must-not-cross-target-boundary"},
    )
    db_session.add(legacy_report)
    await db_session.commit()
    legacy_target_read = await client.get(f"/api/v1/career/reports/{legacy_report.id}")
    assert legacy_target_read.status_code == 404
    assert "legacy_marker" not in legacy_target_read.text

    queued = await client.get(f"/api/v1/career/generations/{generation_id}")
    assert queued.status_code == 200
    assert queued.json()["deterministic_status"] == "pending"
    assert queued.json()["narrative_status"] == "pending"

    generation.status = "failed"
    generation.diagnostics = {"error": "career_deterministic_failure"}
    await db_session.commit()
    terminal_failed = await client.get(f"/api/v1/career/generations/{generation_id}")
    assert terminal_failed.status_code == 200
    assert terminal_failed.json()["status"] == "failed"
    assert terminal_failed.json()["deterministic_status"] == "failed"
    assert terminal_failed.json()["narrative_status"] == "pending"
    assert terminal_failed.json()["diagnostics"] == {"error": "career_deterministic_failure"}

    generation.status = "queued"
    generation.diagnostics = {}
    await db_session.commit()

    report = models.CareerReport(
        career_profile_id=career_profile_id,
        chart_id=chart_id,
        generation_id=generation_id,
        idempotency_key="report-1",
        version=1,
        status="deterministic_ready",
        scoring_version="career-mvp-1",
        reference_version="career-ref-1",
        questionnaire_version="career-q-1",
        prompt_version="career-prompt-1",
        deterministic_payload={"top_dimensions": [{"fact_key": "dimension:systems", "score": 88}]},
        narrative_payload={"sections": []},
        assembled_payload={"contract_version": "career_report_v1"},
    )
    db_session.add(report)
    await db_session.flush()
    generation.report_id = report.id
    generation.status = "deterministic_ready"
    await db_session.commit()

    deterministic = await client.get(f"/api/v1/career/generations/{generation_id}")
    assert deterministic.json()["deterministic_status"] == "ready"
    progressive = await client.get(f"/api/v1/career/reports/{report.id}")
    assert progressive.status_code == 200
    assert progressive.json()["deterministic_payload"]["top_dimensions"][0]["score"] == 88

    ready_segment = models.CareerSegmentGeneration(
        career_profile_id=career_profile_id,
        chart_id=chart_id,
        generation_id=generation_id,
        section_key="professional_summary",
        status="ready",
        prompt_version="career-prompt-1",
        provider="mock",
        model_version="mock-1",
        input_payload={},
        output_payload={"section_key": "professional_summary", "title": "Профиль", "body": "Текст"},
    )
    failed_segment = models.CareerSegmentGeneration(
        career_profile_id=career_profile_id,
        chart_id=chart_id,
        generation_id=generation_id,
        section_key="work_style",
        status="failed",
        prompt_version="career-prompt-1",
        provider="mock",
        model_version="mock-1",
        input_payload={},
        output_payload={},
        error="career_provider_failure",
    )
    db_session.add_all([ready_segment, failed_segment])
    generation.status = "generating_sections"
    report.status = "generating_sections"
    await db_session.commit()

    partial = await client.get(f"/api/v1/career/generations/{generation_id}")
    assert partial.json()["narrative_status"] == "partial_failure"
    assert partial.json()["progress"] == {"total": 2, "ready": 1, "failed": 1, "running": 0}

    ready_segment.status = "failed"
    ready_segment.output_payload = {}
    ready_segment.error = "career_provider_failure"
    report.status = "narrative_failed"
    generation.status = "narrative_failed"
    await db_session.commit()
    narrative_failed = await client.get(f"/api/v1/career/generations/{generation_id}")
    assert narrative_failed.status_code == 200
    assert narrative_failed.json()["status"] == "narrative_failed"
    assert narrative_failed.json()["deterministic_status"] == "ready"
    assert narrative_failed.json()["narrative_status"] == "failed"
    assert narrative_failed.json()["progress"] == {"total": 2, "ready": 0, "failed": 2, "running": 0}

    report.status = "ready"
    generation.status = "ready"
    await db_session.commit()
    ready = await client.get(f"/api/v1/career/generations/{generation_id}")
    assert ready.json()["narrative_status"] == "ready"

    enqueue = AsyncMock()
    monkeypatch.setattr("app.modules.career.router._enqueue_generation", enqueue)
    headers = {"Idempotency-Key": "create-idempotent-1"}
    first = await client.post("/api/v1/career/reports", json={"profile_id": str(profile_id)}, headers=headers)
    second = await client.post("/api/v1/career/reports", json={"profile_id": str(profile_id)}, headers=headers)
    assert first.status_code == second.status_code == 202
    assert first.json()["generation_id"] == second.json()["generation_id"]
    assert enqueue.await_count == 1

    async def deny_access(*, db: AsyncSession, user_id: uuid.UUID) -> None:
        del db, user_id
        raise HTTPException(
            status_code=402,
            detail={
                "contract_version": "career_locked_v1",
                "access_state": "locked",
                "required_product": "plus",
                "reason": "missing_career_access",
            },
        )

    monkeypatch.setattr("app.modules.career.router._require_career_access", deny_access)
    locked = await client.get(f"/api/v1/career/reports/{report.id}")
    assert locked.status_code == 402
    locked_text = locked.text
    for protected in ("top_dimensions", "sections", "score", "artifact"):
        assert protected not in locked_text


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_persisted_entitlement_and_ownership_matrix_covers_every_career_route(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    owner_id = uuid.uuid4()
    foreign_user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    chart_id = uuid.uuid4()
    career_profile_id = uuid.uuid4()
    questionnaire_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    report_id = uuid.uuid4()
    create_generation_id = uuid.uuid4()
    regenerate_generation_id = uuid.uuid4()

    owner = User(
        id=owner_id,
        email=f"career-access-owner-{owner_id}@example.com",
        name="Owner",
        account_tier="free",
        hashed_password="not-used",  # noqa: S106 - inert fixture value
        is_active=True,
        is_verified=True,
    )
    foreign_user = User(
        id=foreign_user_id,
        email=f"career-access-foreign-{foreign_user_id}@example.com",
        name="Foreign",
        account_tier="free",
        hashed_password="not-used",  # noqa: S106 - inert fixture value
        is_active=True,
        is_verified=True,
    )
    db_session.add_all([owner, foreign_user])
    await db_session.flush()

    person = PersonProfile(
        id=profile_id,
        user_id=owner_id,
        name="Owner",
        birth_date=date(1990, 1, 1),
        birth_time=time(12, 0),
        birth_time_accuracy="exact",
        birth_place="Москва",
        latitude=55.75,
        longitude=37.61,
        timezone="Europe/Moscow",
    )
    chart = NatalChart(
        id=chart_id,
        user_id=owner_id,
        profile_id=profile_id,
        engine_version="0.1.5",
        input_hash="d" * 64,
        birth_datetime_utc=datetime(1990, 1, 1, 9, 0, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.75,
        longitude=37.61,
        house_system="P",
        calculation_payload={},
    )
    db_session.add(person)
    await db_session.flush()
    db_session.add(chart)
    await db_session.flush()

    career_profile = models.CareerProfile(
        id=career_profile_id,
        user_id=owner_id,
        profile_id=profile_id,
        chart_id=chart_id,
        generation_id=uuid.uuid4(),
        idempotency_key="access-bootstrap",
        status="questionnaire_completed",
        version=1,
        scoring_version="career-mvp-1",
        reference_version="career-ref-1",
        questionnaire_version="career-q-1",
    )
    questionnaire = models.CareerQuestionnaireSession(
        id=questionnaire_id,
        career_profile_id=career_profile_id,
        chart_id=chart_id,
        status="completed",
        questionnaire_version="career-q-1",
        context_version="career-context-1",
        consent_version="career-consent-1",
        completion_idempotency_key="completed-before-route-matrix",
        answers_hash="e" * 64,
    )
    report = models.CareerReport(
        id=report_id,
        career_profile_id=career_profile_id,
        chart_id=chart_id,
        generation_id=generation_id,
        idempotency_key="access-report",
        version=1,
        status="ready",
        scoring_version="career-mvp-1",
        reference_version="career-ref-1",
        questionnaire_version="career-q-1",
        prompt_version="career-prompt-1",
        deterministic_payload={},
        narrative_payload={"sections": []},
        assembled_payload={"contract_version": "career_report_v1", "sections": []},
    )
    db_session.add_all([career_profile, questionnaire])
    await db_session.flush()
    original_generation = models.CareerGeneration(
        generation_id=generation_id,
        user_id=owner_id,
        career_profile_id=career_profile_id,
        chart_id=chart_id,
        operation="create",
        idempotency_key="access-original",
        status="ready",
        diagnostics={},
    )
    db_session.add(original_generation)
    await db_session.flush()
    db_session.add(report)
    await db_session.flush()
    original_generation.report_id = report_id
    db_session.add_all(
        [
            models.CareerGeneration(
                generation_id=create_generation_id,
                user_id=owner_id,
                career_profile_id=career_profile_id,
                chart_id=chart_id,
                operation="create",
                idempotency_key="access-create",
                status="queued",
                diagnostics={},
            ),
            models.CareerGeneration(
                generation_id=regenerate_generation_id,
                user_id=owner_id,
                career_profile_id=career_profile_id,
                chart_id=chart_id,
                source_report_id=report_id,
                operation="regenerate",
                idempotency_key="access-regenerate",
                status="queued",
                diagnostics={"section_keys": []},
            ),
        ]
    )

    owner_payment = Payment(
        user_id=owner_id,
        provider="test",
        amount=1.0,
        currency="RUB",
        status="succeeded",
        description="Career route matrix",
    )
    foreign_payment = Payment(
        user_id=foreign_user_id,
        provider="test",
        amount=1.0,
        currency="RUB",
        status="succeeded",
        description="Career ownership matrix",
    )
    db_session.add_all([owner_payment, foreign_payment])
    await db_session.flush()
    owner_entitlement = Entitlement(
        user_id=owner_id,
        product="self",
        status="active",
        source_payment_id=owner_payment.id,
        starts_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=30),
    )
    db_session.add_all(
        [
            owner_entitlement,
            Entitlement(
                user_id=foreign_user_id,
                product="self",
                status="active",
                source_payment_id=foreign_payment.id,
                starts_at=now - timedelta(days=1),
                expires_at=now + timedelta(days=30),
            ),
        ]
    )
    await db_session.commit()

    monkeypatch.setattr("app.modules.career.router.settings.CAREER_REPORT_ENABLED", True)
    app.dependency_overrides[get_current_user] = lambda: owner_id

    plus_responses = await _call_career_route_matrix(
        client,
        profile_id=profile_id,
        questionnaire_id=questionnaire_id,
        generation_id=generation_id,
        report_id=report_id,
    )
    assert [response.status_code for response in plus_responses] == [200, 409, 422, 202, 200, 200, 200, 202, 200, 200]
    assert plus_responses[8].json()["versions"][0]["report_id"] == str(report_id)

    owner_entitlement.expires_at = now - timedelta(seconds=1)
    await db_session.commit()
    expired_responses = await _call_career_route_matrix(
        client,
        profile_id=profile_id,
        questionnaire_id=questionnaire_id,
        generation_id=generation_id,
        report_id=report_id,
    )
    assert {response.status_code for response in expired_responses} == {402}

    owner_entitlement.expires_at = None
    owner_entitlement.status = "inactive"
    await db_session.commit()
    inactive_responses = await _call_career_route_matrix(
        client,
        profile_id=profile_id,
        questionnaire_id=questionnaire_id,
        generation_id=generation_id,
        report_id=report_id,
    )
    assert {response.status_code for response in inactive_responses} == {402}

    await db_session.execute(delete(Entitlement).where(Entitlement.id == owner_entitlement.id))
    await db_session.commit()
    free_responses = await _call_career_route_matrix(
        client,
        profile_id=profile_id,
        questionnaire_id=questionnaire_id,
        generation_id=generation_id,
        report_id=report_id,
    )
    assert {response.status_code for response in free_responses} == {402}

    legacy_payment = Payment(
        user_id=owner_id,
        provider="test",
        amount=1.0,
        currency="RUB",
        status="succeeded",
        description="Grandfathered Career",
    )
    db_session.add(legacy_payment)
    await db_session.flush()
    db_session.add(
        Entitlement(
            user_id=owner_id,
            product="career",
            status="active",
            source_payment_id=legacy_payment.id,
            starts_at=now - timedelta(days=1),
            expires_at=None,
        )
    )
    await db_session.commit()
    grandfathered_responses = await _call_career_route_matrix(
        client,
        profile_id=profile_id,
        questionnaire_id=questionnaire_id,
        generation_id=generation_id,
        report_id=report_id,
    )
    assert [response.status_code for response in grandfathered_responses] == [
        200,
        409,
        422,
        202,
        200,
        200,
        200,
        202,
        200,
        200,
    ]

    app.dependency_overrides[get_current_user] = lambda: foreign_user_id
    foreign_responses = await _call_career_route_matrix(
        client,
        profile_id=profile_id,
        questionnaire_id=questionnaire_id,
        generation_id=generation_id,
        report_id=report_id,
    )
    assert {response.status_code for response in foreign_responses} == {404}


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_concurrent_generation_create_is_atomic_validates_target_and_keeps_history(
    db_session: AsyncSession,
) -> None:
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    chart_id = uuid.uuid4()
    career_profile_id = uuid.uuid4()
    db_session.add(
        User(
            id=user_id,
            email=f"career-race-{user_id}@example.com",
            name="Race",
            hashed_password="not-used",  # noqa: S106 - inert fixture value
            is_active=True,
            is_verified=True,
        )
    )
    await db_session.flush()
    db_session.add(
        PersonProfile(
            id=profile_id,
            user_id=user_id,
            name="Race",
            birth_date=date(1990, 1, 1),
            birth_time=time(12, 0),
            birth_time_accuracy="exact",
            birth_place="Москва",
            latitude=55.75,
            longitude=37.61,
            timezone="Europe/Moscow",
        )
    )
    await db_session.flush()
    db_session.add(
        NatalChart(
            id=chart_id,
            user_id=user_id,
            profile_id=profile_id,
            engine_version="0.1.5",
            input_hash="c" * 64,
            birth_datetime_utc=datetime(1990, 1, 1, 9, 0, tzinfo=UTC),
            timezone="Europe/Moscow",
            latitude=55.75,
            longitude=37.61,
            house_system="P",
            calculation_payload={},
        )
    )
    await db_session.flush()
    db_session.add(
        models.CareerProfile(
            id=career_profile_id,
            user_id=user_id,
            profile_id=profile_id,
            chart_id=chart_id,
            generation_id=uuid.uuid4(),
            idempotency_key="race-bootstrap",
            status="questionnaire_completed",
            version=1,
            scoring_version="career-mvp-1",
            reference_version="career-ref-1",
            questionnaire_version="career-q-1",
        )
    )
    await db_session.commit()

    async def create(candidate_generation_id: uuid.UUID) -> tuple[uuid.UUID, bool]:
        async with session_factory() as session:
            result = await CareerRepository(session).create_generation_idempotently(
                generation_id=candidate_generation_id,
                user_id=user_id,
                career_profile_id=career_profile_id,
                chart_id=chart_id,
                operation="create",
                idempotency_key="same-key",
                source_report_id=None,
                diagnostics={},
            )
            await session.commit()
            return result.generation.generation_id, result.created

    first, second = await asyncio.gather(create(uuid.uuid4()), create(uuid.uuid4()))
    assert first[0] == second[0]
    assert sorted((first[1], second[1])) == [False, True]

    async def claim() -> bool:
        async with session_factory() as session:
            claimed = await CareerRepository(session).claim_generation(first[0])
            await session.commit()
            return claimed is not None

    assert sorted(await asyncio.gather(claim(), claim())) == [False, True]

    async with session_factory() as session:
        with pytest.raises(CareerGenerationTargetMismatchError):
            await CareerRepository(session).create_generation_idempotently(
                generation_id=uuid.uuid4(),
                user_id=user_id,
                career_profile_id=uuid.uuid4(),
                chart_id=chart_id,
                operation="create",
                idempotency_key="same-key",
                source_report_id=None,
                diagnostics={},
            )

    async def allocate_and_insert_report(key: str) -> int:
        async with session_factory() as session:
            version = await CareerRepository(session).allocate_report_version(career_profile_id)
            session.add(
                models.CareerReport(
                    career_profile_id=career_profile_id,
                    chart_id=chart_id,
                    generation_id=uuid.uuid4(),
                    idempotency_key=key,
                    version=version,
                    status="deterministic_ready",
                    scoring_version="career-mvp-1",
                    reference_version="career-ref-1",
                    questionnaire_version="career-q-1",
                    prompt_version="career-prompt-1",
                    deterministic_payload={},
                    narrative_payload={},
                    assembled_payload={},
                )
            )
            await session.commit()
            return version

    versions = await asyncio.gather(
        allocate_and_insert_report("report-race-1"),
        allocate_and_insert_report("report-race-2"),
    )
    assert sorted(versions) == [1, 2]

    generations = (uuid.uuid4(), uuid.uuid4())
    db_session.add_all(
        [
            models.CareerDimensionScore(
                career_profile_id=career_profile_id,
                chart_id=chart_id,
                generation_id=generation_id,
                dimension="systems_thinking",
                score=score,
                confidence=0.9,
                scoring_version="career-mvp-1",
                breakdown={},
            )
            for generation_id, score in zip(generations, (80.0, 90.0), strict=True)
        ]
    )
    await db_session.commit()

    rows = (
        (await db_session.execute(select(models.CareerDimensionScore).order_by(models.CareerDimensionScore.score)))
        .scalars()
        .all()
    )
    assert [(row.generation_id, row.score) for row in rows] == [(generations[0], 80.0), (generations[1], 90.0)]
