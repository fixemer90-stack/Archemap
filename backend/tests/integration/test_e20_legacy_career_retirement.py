"""Persisted archive safety; only run against an explicitly disposable database."""

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.main import app
from app.modules.authorization.models import Entitlement
from app.modules.charts.models import ChartSnapshot
from app.modules.payments.models import Payment
from app.modules.profiles.models import PersonProfile
from app.modules.report_narratives import tasks as narrative_tasks
from app.modules.report_narratives.models import ReportNarrative
from app.modules.report_narratives.service import ReportNarrativeService
from app.modules.reports.models import Report, ReportVersion
from app.modules.reports.retirement import LegacyCareerRetiredError
from app.modules.reports.service import ReportService
from app.modules.users.models import User
from tests.conftest import test_session_factory as session_factory


async def _seed_archive(db: AsyncSession, *, status: str, payload: dict[str, Any]) -> tuple[UUID, UUID, UUID]:
    user = User(email=f"e20-{uuid4()}@example.com", name="Archive", hashed_password="unused", is_active=True)  # noqa: S106 - inert fixture
    db.add(user)
    await db.flush()
    person = PersonProfile(
        user_id=user.id,
        name="Archive",
        birth_date=date(1990, 1, 1),
        birth_time_accuracy="unknown",
        birth_place="Archive",
        latitude=0,
        longitude=0,
        timezone="UTC",
    )
    payment = Payment(user_id=user.id, provider="mock", amount=1, status="succeeded")
    db.add_all([person, payment])
    await db.flush()
    grant = Entitlement(
        user_id=user.id,
        product="career",
        source_payment_id=payment.id,
        starts_at=datetime.now(UTC) - timedelta(days=1),
        status="active",
    )
    report = Report(
        user_id=user.id,
        profile_id=person.id,
        product="career",
        version=3,
        status=status,
        report_data=payload,
        error_message="historical error",
    )
    db.add_all([grant, report])
    await db.flush()
    db.add_all(
        [
            ChartSnapshot(
                user_id=user.id,
                profile_id=person.id,
                engine_version="ancient",
                birth_data={"historical": True},
                chart_data={"historical": True},
                features={},
                function_strengths={},
                socionics={},
            ),
            ReportVersion(report_id=report.id, version=1, report_data={"original": "version"}),
            ReportNarrative(
                report_id=report.id,
                product="career",
                prompt_version="legacy",
                model_provider="mock",
                model_name="mock",
                status="pending",
                content={"sections": []},
                input_hash="a" * 64,
            ),
        ]
    )
    await db.commit()
    return user.id, person.id, report.id


async def _snapshot() -> dict[str, Any]:
    async with session_factory() as db:
        result = {}
        for model in (Report, ReportVersion, ReportNarrative, ChartSnapshot, Entitlement):
            rows = (await db.execute(select(model).order_by(model.id))).scalars().all()
            result[model.__tablename__] = [
                {column.name: getattr(row, column.key) for column in model.__table__.columns} for row in rows
            ]
        return result


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
@pytest.mark.parametrize(
    "historical_status", ["ready", "failed", "pending", "generating", "deterministic_ready", "narrative_failed"]
)
async def test_e20_archive_routes_preserve_all_persisted_state(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, historical_status: str
) -> None:
    payload = {
        "product": "career",
        "provenance": {"engine_version": "ancient"},
        "claims": [],
        "legacy_extra": {"untouched": True},
    }
    user_id, _, report_id = await _seed_archive(db_session, status=historical_status, payload=payload)
    app.dependency_overrides[get_current_user] = lambda: user_id
    monkeypatch.setattr(
        "app.modules.reports.service.ReportService._report_requires_refresh",
        AsyncMock(side_effect=AssertionError("archive must not inspect refresh")),
    )
    monkeypatch.setattr(
        "app.modules.charts.service.ChartService.get_or_compute",
        AsyncMock(side_effect=AssertionError("archive must not compute charts")),
    )
    counter = MagicMock()
    monkeypatch.setattr("app.modules.reports.retirement.retirement_telemetry.counter", counter)
    before = await _snapshot()
    read = await client.get(f"/api/v1/reports/{report_id}")
    assert read.status_code == 200, read.text
    assert read.json()["status"] == historical_status
    assert read.json()["report_data"] == payload
    listing = await client.get("/api/v1/reports", params={"product": "career"})
    assert listing.status_code == 200
    assert listing.json()["items"][0]["report_data"] == payload
    versions = await client.get(f"/api/v1/reports/{report_id}/versions")
    assert versions.status_code == 200
    version = await client.get(f"/api/v1/reports/{report_id}/versions/1")
    assert version.status_code == 200
    assert version.json()["report_data"] == {"original": "version"}
    for method in ("GET", "HEAD", "POST"):
        pdf = await client.request(method, f"/api/v1/reports/{report_id}/pdf")
        assert pdf.status_code == 200, pdf.text
        if method != "HEAD":
            assert pdf.content.startswith(b"%PDF")
    await db_session.commit()
    assert await _snapshot() == before
    operations = [call.args[1]["operation"] for call in counter.add.call_args_list]
    assert operations.count("archive_read") == 2  # explicit GET and list, never PDF's internal reads
    assert operations.count("archive_versions") == 2
    assert operations.count("archive_pdf") == 3


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
@pytest.mark.parametrize("entry", ["service", "queued", "celery", "failure_finalizer"])
async def test_e20_career_narrative_writers_cannot_mutate_even_when_caught_and_committed(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    _, _, report_id = await _seed_archive(db_session, status="ready", payload={"product": "career", "historical": True})
    before = await _snapshot()
    provider = MagicMock()
    provider.generate_structured = AsyncMock(side_effect=AssertionError("no provider calls"))
    monkeypatch.setattr("app.modules.report_narratives.service.get_llm_provider", lambda settings: provider)
    counter = MagicMock()
    monkeypatch.setattr("app.modules.reports.retirement.retirement_telemetry.counter", counter)
    monkeypatch.setattr(narrative_tasks, "async_session_factory", session_factory)
    if entry == "failure_finalizer":
        await narrative_tasks._finalize_narrative_task_failure_async(report_id, "must not overwrite")
    else:
        with pytest.raises(LegacyCareerRetiredError):
            if entry == "service":
                await ReportNarrativeService(db_session, llm_provider=provider).generate_for_report(
                    report_id, force=True
                )
            elif entry == "celery":
                from workers.tasks.reports import generate_report_narrative

                await asyncio.to_thread(cast(Any, generate_report_narrative).run, str(report_id), True)
            else:
                await narrative_tasks._generate_report_narrative_async(report_id, force=True)
    await db_session.commit()
    assert await _snapshot() == before
    provider.generate_structured.assert_not_called()
    counter.add.assert_called_once_with(1, {"operation": "blocked_worker"})


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_e20_regenerate_retires_before_payload_load(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id, _, report_id = await _seed_archive(db_session, status="ready", payload={"original": True})
    app.dependency_overrides[get_current_user] = lambda: user_id
    monkeypatch.setattr(
        "app.modules.reports.service.ReportService.get_report",
        AsyncMock(side_effect=AssertionError("metadata only before retirement")),
    )
    before = await _snapshot()
    response = await client.post(f"/api/v1/reports/{report_id}/narrative/regenerate")
    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "legacy_career_generation_retired"
    await db_session.commit()
    assert await _snapshot() == before


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_e20_empty_archive_is_honestly_unavailable_without_rewriting_ready_status(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id, _, report_id = await _seed_archive(db_session, status="ready", payload={})
    app.dependency_overrides[get_current_user] = lambda: user_id
    counter = MagicMock()
    monkeypatch.setattr("app.modules.reports.retirement.retirement_telemetry.counter", counter)
    before = await _snapshot()
    response = await client.get(f"/api/v1/reports/{report_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["report_data"] == {}
    assert response.json()["archive_status"] == "unavailable"
    for method in ("GET", "HEAD", "POST"):
        pdf = await client.request(method, f"/api/v1/reports/{report_id}/pdf")
        assert pdf.status_code == 404
    await db_session.commit()
    assert await _snapshot() == before
    assert [call.args[1] for call in counter.add.call_args_list] == [{"operation": "archive_missing"}] * 4


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_e20_http_and_direct_generation_are_single_count_no_ops(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id, profile_id, _ = await _seed_archive(db_session, status="ready", payload={"unchanged": True})
    app.dependency_overrides[get_current_user] = lambda: user_id
    counter = MagicMock()
    monkeypatch.setattr("app.modules.reports.retirement.retirement_telemetry.counter", counter)
    monkeypatch.setattr(ReportService, "_find_existing", AsyncMock(side_effect=AssertionError("no report lookup")))
    before = await _snapshot()
    response = await client.post("/api/v1/reports/generate", json={"profile_id": str(profile_id), "product": "career"})
    assert response.status_code == 410
    counter.add.assert_called_once_with(1, {"operation": "blocked_generation"})
    counter.reset_mock()
    with pytest.raises(LegacyCareerRetiredError):
        await ReportService(db_session).generate_report(profile_id, user_id, product="career")
    await db_session.commit()
    counter.add.assert_called_once_with(1, {"operation": "blocked_generation"})
    assert await _snapshot() == before
    counter.reset_mock()
    # The public interpretation consumer cannot produce Career v1 claims either.
    interpreted = await client.post(
        "/api/v1/rules/interpret", json={"profile_id": str(profile_id), "product": "career"}
    )
    assert interpreted.status_code == 410
    counter.add.assert_called_once_with(1, {"operation": "blocked_generation"})
    assert await _snapshot() == before


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
@pytest.mark.parametrize("denial", ["foreign", "expired", "revoked", "future"])
async def test_e20_archive_and_writers_keep_ownership_and_access_before_payload(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, denial: str
) -> None:
    user_id, profile_id, report_id = await _seed_archive(
        db_session, status="ready", payload={"private": "never deserialize"}
    )
    grant = (await db_session.execute(select(Entitlement))).scalar_one()
    if denial == "expired":
        grant.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    elif denial == "revoked":
        grant.status = "revoked"
    elif denial == "future":
        grant.starts_at = datetime.now(UTC) + timedelta(days=1)
    await db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: uuid4() if denial == "foreign" else user_id
    monkeypatch.setattr(ReportService, "get_report", AsyncMock(side_effect=AssertionError("no protected payload")))
    counter = MagicMock()
    monkeypatch.setattr("app.modules.reports.retirement.retirement_telemetry.counter", counter)
    before = await _snapshot()
    paths = [
        ("GET", ""),
        ("GET", "/versions"),
        ("GET", "/versions/1"),
        ("GET", "/pdf"),
        ("HEAD", "/pdf"),
        ("POST", "/pdf"),
        ("POST", "/narrative/regenerate"),
    ]
    expected = 404 if denial == "foreign" else 402
    for method, suffix in paths:
        response = await client.request(method, f"/api/v1/reports/{report_id}{suffix}")
        assert response.status_code == expected
        assert "private" not in response.text
    generation = await client.post(
        "/api/v1/reports/generate", json={"profile_id": str(profile_id), "product": "career"}
    )
    assert generation.status_code == expected
    counter.add.assert_not_called()
    await db_session.commit()
    assert await _snapshot() == before


@pytest.mark.asyncio
@pytest.mark.usefixtures("_setup_database")
async def test_e20_archive_list_filters_profile_before_pagination_and_counts_owned_missing(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id, profile_id, report_id = await _seed_archive(db_session, status="ready", payload={"selected": True})
    other = PersonProfile(
        user_id=user_id,
        name="Other",
        birth_date=date(1991, 1, 1),
        birth_time_accuracy="unknown",
        birth_place="Other",
        latitude=0,
        longitude=0,
        timezone="UTC",
    )
    empty = PersonProfile(
        user_id=user_id,
        name="Empty",
        birth_date=date(1992, 1, 1),
        birth_time_accuracy="unknown",
        birth_place="Empty",
        latitude=0,
        longitude=0,
        timezone="UTC",
    )
    db_session.add_all([other, empty])
    await db_session.flush()
    db_session.add_all(
        [
            Report(user_id=user_id, profile_id=other.id, product="career", status="ready", report_data={"other": True})
            for _ in range(101)
        ]
    )
    await db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: user_id
    counter = MagicMock()
    monkeypatch.setattr("app.modules.reports.retirement.retirement_telemetry.counter", counter)
    selected = await client.get(
        "/api/v1/reports", params={"product": "career", "profile_id": str(profile_id), "limit": 100}
    )
    assert selected.status_code == 200
    assert selected.json()["total"] == 1
    assert [item["id"] for item in selected.json()["items"]] == [str(report_id)]
    counter.reset_mock()
    missing = await client.get("/api/v1/reports", params={"product": "career", "profile_id": str(empty.id)})
    assert missing.status_code == 200
    assert missing.json()["total"] == 0
    counter.add.assert_called_once_with(1, {"operation": "archive_missing"})
    counter.reset_mock()
    foreign = await client.get("/api/v1/reports", params={"product": "career", "profile_id": str(uuid4())})
    assert foreign.status_code == 404
    counter.add.assert_not_called()
