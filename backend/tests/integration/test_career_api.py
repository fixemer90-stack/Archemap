from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.main import app
from app.modules.astrotype_v2.models import NatalChart
from app.modules.career import models
from app.modules.profiles.models import PersonProfile
from app.modules.users.models import User


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

    queued = await client.get(f"/api/v1/career/generations/{generation_id}")
    assert queued.status_code == 200
    assert queued.json()["deterministic_status"] == "pending"
    assert queued.json()["narrative_status"] == "pending"

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

    db_session.add_all(
        [
            models.CareerSegmentGeneration(
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
            ),
            models.CareerSegmentGeneration(
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
            ),
        ]
    )
    generation.status = "generating_sections"
    report.status = "generating_sections"
    await db_session.commit()

    partial = await client.get(f"/api/v1/career/generations/{generation_id}")
    assert partial.json()["narrative_status"] == "partial_failure"
    assert partial.json()["progress"] == {"total": 2, "ready": 1, "failed": 1, "running": 0}

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
