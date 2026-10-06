"""Real PostgreSQL coverage for refinement report activation and preservation."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, time
from unittest.mock import MagicMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.repository import AstrotypeV2Repository
from app.modules.payments.models import Payment
from app.modules.profiles.models import (
    PersonProfile,
    ProfileActiveNatalReport,
    ProfileBirthDataRevision,
)
from app.modules.users.models import User
from workers.tasks import profile_refinement
from workers.tasks.astrotype_v2 import _get_or_create_chart, _RevisionChartInput


async def _seed_profile(db: AsyncSession) -> tuple[uuid.UUID, PersonProfile]:
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"e10-s03-{user_id}@example.com",
        name="E10 S03",
        hashed_password="unused",  # noqa: S106
        is_active=True,
        is_verified=True,
    )
    profile = PersonProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        name="Profile",
        birth_date=date(1990, 1, 1),
        birth_time=time(12, 0),
        birth_time_accuracy="exact",
        birth_place="Moscow",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
    )
    db.add(user)
    await db.flush()
    db.add(profile)
    await db.flush()
    return user_id, profile


def _chart(*, user_id: uuid.UUID, profile_id: uuid.UUID, input_hash: str) -> models.NatalChart:
    return models.NatalChart(
        user_id=user_id,
        profile_id=profile_id,
        engine_version="0.1.5",
        input_hash=input_hash,
        birth_datetime_utc=datetime(1990, 1, 1, 9, 0, tzinfo=UTC),
        timezone="Europe/Moscow",
        latitude=55.7558,
        longitude=37.6173,
        house_system="P",
        calculation_payload={},
    )


@pytest.mark.usefixtures("_setup_database")
async def test_active_report_switch_is_atomic_retry_safe_and_preserves_old_artifacts(db_session: AsyncSession) -> None:
    user_id, profile = await _seed_profile(db_session)
    old_chart = _chart(user_id=user_id, profile_id=profile.id, input_hash="old" * 21 + "o")
    new_chart = _chart(user_id=user_id, profile_id=profile.id, input_hash="new" * 21 + "n")
    db_session.add_all((old_chart, new_chart))
    await db_session.flush()
    old_report = models.NatalReport(chart_id=old_chart.id, version=1, status="complete")
    new_report = models.NatalReport(
        chart_id=new_chart.id,
        version=2,
        status="narrative_generating",
        generation_id=uuid.uuid4(),
    )
    db_session.add_all((old_report, new_report))
    await db_session.flush()
    old_segment = models.ReportSegmentGeneration(
        chart_id=old_chart.id,
        outline_id=uuid.uuid4(),
        section_key="core_pattern",
        status="ready",
    )
    # The segment FK requires an outline, and keeping it proves historical artifacts survive.
    old_outline = models.ReportOutline(
        id=old_segment.outline_id,
        chart_id=old_chart.id,
        status="ready",
        outline={},
        section_keys=[],
        source_version="v2.0",
    )
    generation = models.NatalReportGeneration(
        generation_id=new_report.generation_id,
        user_id=user_id,
        profile_id=profile.id,
        report_id=new_report.id,
        status="narrative_generating",
    )
    revision = ProfileBirthDataRevision(
        user_id=user_id,
        profile_id=profile.id,
        previous_snapshot={},
        new_snapshot={},
        changed_fields=["birth_time"],
        status="processing",
        generation_id=new_report.generation_id,
        idempotency_key=str(uuid.uuid4()),
        request_hash="a" * 64,
    )
    db_session.add_all((old_outline, old_segment, generation, revision))
    await db_session.flush()
    repository = AstrotypeV2Repository(db_session)
    await repository.activate_report(profile_id=profile.id, user_id=user_id, report_id=old_report.id)
    await db_session.commit()

    current = await repository.get_latest_report_for_profile(profile_id=profile.id, user_id=user_id)
    assert current is not None and current.id == old_report.id
    payments_before = await db_session.scalar(select(func.count()).select_from(Payment))

    revision.chart_id = new_chart.id
    revision.report_id = new_report.id
    revision.status = "deterministic_ready"
    await repository.activate_report(profile_id=profile.id, user_id=user_id, report_id=new_report.id)
    await repository.activate_report(profile_id=profile.id, user_id=user_id, report_id=new_report.id)
    await db_session.commit()

    active = await repository.get_active_report_for_profile(profile_id=profile.id, user_id=user_id)
    assert active is not None and active.id == new_report.id
    assert revision.chart_id == new_chart.id
    assert revision.report_id == new_report.id
    assert revision.status == "deterministic_ready"
    assert await db_session.scalar(select(func.count()).select_from(models.NatalChart)) == 2
    assert await db_session.scalar(select(func.count()).select_from(models.NatalReport)) == 2
    assert await db_session.scalar(select(func.count()).select_from(models.ReportSegmentGeneration)) == 1
    assert await db_session.scalar(select(func.count()).select_from(ProfileActiveNatalReport)) == 1
    assert await db_session.scalar(select(func.count()).select_from(Payment)) == payments_before


@pytest.mark.usefixtures("_setup_database")
async def test_failed_candidate_does_not_replace_old_active_report(db_session: AsyncSession) -> None:
    user_id, profile = await _seed_profile(db_session)
    chart = _chart(user_id=user_id, profile_id=profile.id, input_hash="x" * 64)
    db_session.add(chart)
    await db_session.flush()
    report = models.NatalReport(chart_id=chart.id, version=1, status="complete")
    db_session.add(report)
    await db_session.flush()
    repository = AstrotypeV2Repository(db_session)
    await repository.activate_report(profile_id=profile.id, user_id=user_id, report_id=report.id)
    await db_session.commit()

    # A terminal failure only changes its durable revision; activation is never called.
    failed_generation = models.NatalReportGeneration(
        generation_id=uuid.uuid4(), user_id=user_id, profile_id=profile.id, status="failed"
    )
    failed_revision = ProfileBirthDataRevision(
        user_id=user_id,
        profile_id=profile.id,
        previous_snapshot={},
        new_snapshot={},
        changed_fields=["timezone"],
        status="failed",
        generation_id=failed_generation.generation_id,
        error_code="report_generation_failed",
        idempotency_key=str(uuid.uuid4()),
        request_hash="b" * 64,
    )
    db_session.add_all((failed_generation, failed_revision))
    await db_session.commit()

    active = await repository.get_active_report_for_profile(profile_id=profile.id, user_id=user_id)
    assert active is not None and active.id == report.id
    assert failed_revision.report_id is None
    assert failed_revision.error_code == "report_generation_failed"


@pytest.mark.usefixtures("_setup_database")
async def test_monitor_counts_narrative_and_fatal_failures_but_ignores_clean_deterministic_ready(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id, profile = await _seed_profile(db_session)
    now = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
    revisions = (
        ("deterministic_ready", "narrative_generation_failed"),
        ("failed", "report_generation_failed"),
        ("deterministic_ready", None),
        ("deterministic_ready", "unrelated_error"),
    )
    for index, (status, error_code) in enumerate(revisions):
        generation_id = uuid.uuid4()
        db_session.add(
            models.NatalReportGeneration(
                generation_id=generation_id,
                user_id=user_id,
                profile_id=profile.id,
                status=status,
            )
        )
        db_session.add(
            ProfileBirthDataRevision(
                user_id=user_id,
                profile_id=profile.id,
                previous_snapshot={},
                new_snapshot={},
                changed_fields=["timezone"],
                status=status,
                generation_id=generation_id,
                error_code=error_code,
                idempotency_key=str(uuid.uuid4()),
                request_hash=f"{index}" * 64,
                updated_at=now,
            )
        )
    await db_session.commit()

    @asynccontextmanager
    async def session_context() -> AsyncIterator[AsyncSession]:
        yield db_session

    telemetry = MagicMock()
    warning = MagicMock()
    monkeypatch.setattr(profile_refinement, "async_session_factory", session_context)
    monkeypatch.setattr(profile_refinement, "birth_data_refinement_telemetry", telemetry)
    monkeypatch.setattr(profile_refinement.logger, "warning", warning)
    monkeypatch.setattr(settings, "BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES", 20)
    monkeypatch.setattr(settings, "BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES", 15)

    result = await profile_refinement._monitor_birth_data_refinements_async(now=now)

    assert result == {"stuck": 0, "recent_failed": 2, "alerted": True}
    telemetry.set_recent_failures.assert_called_once_with(2)
    warning.assert_called_once()


@pytest.mark.usefixtures("_setup_database")
async def test_refinement_chart_rebuild_uses_new_time_timezone_and_is_retry_safe(db_session: AsyncSession) -> None:
    user_id, profile = await _seed_profile(db_session)
    repository = AstrotypeV2Repository(db_session)

    original = await _get_or_create_chart(repository=repository, profile=profile, user_id=user_id)
    changed_time = _RevisionChartInput(
        id=profile.id,
        birth_date=profile.birth_date,
        birth_time=time(13, 30),
        birth_time_accuracy="exact",
        birth_place="Moscow",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
    )
    time_chart = await _get_or_create_chart(repository=repository, profile=changed_time, user_id=user_id)
    time_retry = await _get_or_create_chart(repository=repository, profile=changed_time, user_id=user_id)
    changed_place = _RevisionChartInput(
        id=profile.id,
        birth_date=profile.birth_date,
        birth_time=time(13, 30),
        birth_time_accuracy="exact",
        birth_place="Berlin, Germany",
        latitude=52.52,
        longitude=13.405,
        timezone="Europe/Berlin",
    )
    place_chart = await _get_or_create_chart(repository=repository, profile=changed_place, user_id=user_id)
    await db_session.commit()

    assert original.input_hash != time_chart.input_hash
    assert time_chart.birth_datetime_utc == datetime(1990, 1, 1, 10, 30, tzinfo=UTC)
    assert time_retry.id == time_chart.id
    assert place_chart.input_hash != time_chart.input_hash
    assert place_chart.birth_datetime_utc == datetime(1990, 1, 1, 12, 30, tzinfo=UTC)
    assert place_chart.latitude == 52.52
    assert place_chart.longitude == 13.405
    assert place_chart.timezone == "Europe/Berlin"
    assert await db_session.scalar(select(func.count()).select_from(models.NatalChart)) == 3
