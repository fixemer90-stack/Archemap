"""Unit tests for the reports module."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

import app.modules.reports.router as reports_router
from app.modules.reports.models import Report, ReportVersion
from app.modules.reports.schemas import GenerateReportRequest, ReportResponse, ReportVersionResponse
from app.modules.reports.service import ReportService, _build_chart_summary
from app.modules.reports.tasks import _run_async as _run_async_pdf_task

# ── Fixtures ─────────────────────────────────────────────────────────


def make_chart_data() -> dict[str, Any]:
    """Create sample chart data."""
    return {
        "birth_datetime": "1990-08-24T11:00:00+00:00",
        "latitude": 55.7558,
        "longitude": 37.6173,
        "timezone": "Europe/Moscow",
        "house_system": "P",
        "planets": [
            {
                "name": "Sun",
                "longitude": 151.09,
                "latitude": 0.0,
                "speed": 0.96,
                "sign": "Virgo",
                "sign_degree": 1.09,
                "house": 9,
                "is_retrograde": False,
            }
        ],
        "houses": [{"number": 1, "longitude": 236.36, "sign": "Scorpio"}],
        "aspects": [
            {
                "planet_a": "Venus",
                "planet_b": "Neptune",
                "aspect_type": "quincunx",
                "angle": 150.86,
                "orb": 0.86,
                "is_applying": False,
            }
        ],
    }


def make_features() -> dict[str, Any]:
    """Create sample features dict."""
    return {
        "fire": 0.186,
        "earth": 0.571,
        "air": 0.171,
        "water": 0.071,
        "cardinal": 0.371,
        "fixed": 0.400,
        "mutable": 0.229,
        "has_birth_time": True,
        "birth_time_quality": 1.0,
    }


def make_report(
    user_id: UUID | None = None,
    profile_id: UUID | None = None,
    product: str = "self",
    status: str = "ready",
    version: int = 1,
) -> Report:
    """Create a sample Report."""
    return Report(
        id=uuid4(),
        user_id=user_id or uuid4(),
        profile_id=profile_id or uuid4(),
        product=product,
        version=version,
        status=status,
        mode="full",
        report_data={"product": product, "archetype": {"primary": "Стратег"}},
        archetype="Стратег",
        score=0.78,
        confidence=0.72,
        pdf_generated=False,
    )


def test_pdf_task_runner_reuses_process_event_loop() -> None:
    async def get_loop_id() -> int:
        import asyncio

        return id(asyncio.get_running_loop())

    first = _run_async_pdf_task(get_loop_id())
    second = _run_async_pdf_task(get_loop_id())

    assert first == second


# ── Chart summary tests ──────────────────────────────────────────────


class TestBuildChartSummary:
    """Test _build_chart_summary helper."""

    def test_basic_structure(self) -> None:
        chart_data = make_chart_data()
        features = make_features()
        summary = _build_chart_summary(chart_data, features)

        assert "planets" in summary
        assert "houses" in summary
        assert "aspects" in summary
        assert "elements" in summary
        assert "modalities" in summary

    def test_elements_from_features(self) -> None:
        chart_data = make_chart_data()
        features = make_features()
        summary = _build_chart_summary(chart_data, features)

        assert summary["elements"]["fire"] == 0.186
        assert summary["elements"]["earth"] == 0.571
        assert summary["elements"]["air"] == 0.171
        assert summary["elements"]["water"] == 0.071

    def test_modalities_from_features(self) -> None:
        chart_data = make_chart_data()
        features = make_features()
        summary = _build_chart_summary(chart_data, features)

        assert summary["modalities"]["cardinal"] == 0.371
        assert summary["modalities"]["fixed"] == 0.400
        assert summary["modalities"]["mutable"] == 0.229

    def test_planets_preserved(self) -> None:
        chart_data = make_chart_data()
        features = make_features()
        summary = _build_chart_summary(chart_data, features)

        assert len(summary["planets"]) == 1
        assert summary["planets"][0]["name"] == "Sun"
        assert summary["planets"][0]["sign"] == "Virgo"

    def test_empty_chart_data(self) -> None:
        chart_data: dict[str, Any] = {}
        features = make_features()
        summary = _build_chart_summary(chart_data, features)

        assert summary["planets"] == []
        assert summary["houses"] == []
        assert summary["aspects"] == []

    def test_missing_features_defaults_to_zero(self) -> None:
        chart_data = make_chart_data()
        features: dict[str, Any] = {}
        summary = _build_chart_summary(chart_data, features)

        assert summary["elements"]["fire"] == 0
        assert summary["modalities"]["cardinal"] == 0


# ── Report model tests ───────────────────────────────────────────────


class TestReportModel:
    """Test Report model defaults."""

    def test_default_status(self) -> None:
        report = Report(
            user_id=uuid4(),
            profile_id=uuid4(),
            product="self",
            status="pending",
        )
        assert report.status == "pending"

    def test_default_mode(self) -> None:
        report = Report(
            user_id=uuid4(),
            profile_id=uuid4(),
            product="self",
            mode="full",
        )
        assert report.mode == "full"

    def test_default_version(self) -> None:
        report = Report(
            user_id=uuid4(),
            profile_id=uuid4(),
            product="self",
            version=1,
        )
        assert report.version == 1

    def test_default_pdf_generated(self) -> None:
        report = Report(
            user_id=uuid4(),
            profile_id=uuid4(),
            product="self",
            pdf_generated=False,
        )
        assert report.pdf_generated is False

    def test_report_with_data(self) -> None:
        data: dict[str, Any] = {"product": "self", "archetype": {"primary": "Стратег"}}
        report = Report(
            user_id=uuid4(),
            profile_id=uuid4(),
            product="self",
            report_data=data,
            archetype="Стратег",
            score=0.78,
            confidence=0.72,
        )
        assert report.report_data == data
        assert report.archetype == "Стратег"
        assert report.score == 0.78
        assert report.confidence == 0.72

    def test_report_optional_fields(self) -> None:
        report = Report(
            user_id=uuid4(),
            profile_id=uuid4(),
            product="self",
        )
        assert report.archetype is None
        assert report.score is None
        assert report.confidence is None
        assert report.pdf_url is None
        assert report.error_message is None


# ── ReportVersion model tests ────────────────────────────────────────


class TestReportVersionModel:
    """Test ReportVersion model."""

    def test_creation(self) -> None:
        rv = ReportVersion(
            report_id=uuid4(),
            version=1,
            report_data={"test": True},
        )
        assert rv.version == 1
        assert rv.report_data == {"test": True}
        assert rv.pdf_url is None
        assert rv.diff_summary is None


# ── Report schema tests ───────────────────────────────────────────────


class TestReportSchemas:
    """Test API response schemas for ORM UUID fields."""

    def test_report_response_accepts_uuid_fields(self) -> None:
        report = make_report()
        report.created_at = report.updated_at = datetime.now(UTC)

        response = ReportResponse.model_validate(report)

        assert response.id == report.id
        assert response.profile_id == report.profile_id

    def test_report_version_response_accepts_uuid_fields(self) -> None:
        version = ReportVersion(
            id=uuid4(),
            report_id=uuid4(),
            version=1,
            report_data={"test": True},
            created_at=datetime.now(UTC),
        )

        response = ReportVersionResponse.model_validate(version)

        assert response.id == version.id
        assert response.report_id == version.report_id


@pytest.mark.asyncio
async def test_generate_report_route_refreshes_report_before_serializing_after_enqueue_status_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeReport:
        def __init__(self) -> None:
            self.id = uuid4()
            self.profile_id = uuid4()
            self.product = "self"
            self.version = 1
            self.status = "deterministic_ready"
            self.mode = "full"
            self.archetype = "Стратег"
            self.score = 0.91
            self.confidence = 0.83
            self.pdf_url = None
            self.pdf_generated = False
            self.report_data = {"product": "self", "archetype": {"primary": "Стратег"}}
            self.error_message = None
            self.created_at = datetime.now(UTC)
            self._updated_at = datetime.now(UTC)
            self._fresh = True

        @property
        def updated_at(self) -> datetime:
            if not self._fresh:
                raise RuntimeError("stale updated_at")
            return self._updated_at

    class FakeDB:
        def __init__(self, report: FakeReport) -> None:
            self.report = report
            self.refresh_calls = 0
            self.commit_calls = 0

        async def flush(self) -> None:
            self.report._fresh = False

        async def commit(self) -> None:
            self.commit_calls += 1

        async def refresh(self, report: FakeReport) -> None:
            assert report is self.report
            self.refresh_calls += 1
            self.report._fresh = True

    report = FakeReport()
    db = FakeDB(report)
    user_id = uuid4()

    async def fake_generate_report(
        self: ReportService,
        profile_id: UUID,
        user_id: UUID,
        product: str = "self",
        mode: str = "full",
    ) -> FakeReport:
        assert profile_id == report.profile_id
        assert user_id == user_id
        assert product == "self"
        assert mode == "full"
        return report

    async def fake_get_latest_narrative_for_report(*, db: FakeDB, report_id: UUID) -> None:
        assert report_id == report.id
        return None

    class DummyTask:
        def delay(self, *args: Any, **kwargs: Any) -> None:
            return None

    monkeypatch.setattr(ReportService, "generate_report", fake_generate_report)
    monkeypatch.setattr(reports_router, "get_latest_narrative_for_report", fake_get_latest_narrative_for_report)

    from workers.tasks import reports as worker_reports

    monkeypatch.setattr(worker_reports, "generate_pdf", DummyTask())
    monkeypatch.setattr(worker_reports, "generate_report_narrative", DummyTask())

    response = await reports_router.generate_report(
        GenerateReportRequest(profile_id=str(report.profile_id), product="self", mode="full"),
        db=cast(Any, db),
        current_user=user_id,
    )

    assert db.refresh_calls == 1
    assert response.id == report.id
    assert response.status == "generating_narrative"


@pytest.mark.asyncio
async def test_generate_report_route_commits_report_before_enqueuing_narrative_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeReport:
        def __init__(self) -> None:
            self.id = uuid4()
            self.profile_id = uuid4()
            self.product = "self"
            self.version = 1
            self.status = "deterministic_ready"
            self.mode = "full"
            self.archetype = "Стратег"
            self.score = 0.91
            self.confidence = 0.83
            self.pdf_url = None
            self.pdf_generated = False
            self.report_data = {"product": "self", "archetype": {"primary": "Стратег"}}
            self.error_message = None
            self.created_at = datetime.now(UTC)
            self.updated_at = datetime.now(UTC)

    class FakeDB:
        def __init__(self, report: FakeReport) -> None:
            self.report = report
            self.commit_calls = 0
            self.refresh_calls = 0

        async def flush(self) -> None:
            return None

        async def commit(self) -> None:
            self.commit_calls += 1

        async def refresh(self, report: FakeReport) -> None:
            assert report is self.report
            self.refresh_calls += 1

    report = FakeReport()
    db = FakeDB(report)
    user_id = uuid4()

    async def fake_generate_report(
        self: ReportService,
        profile_id: UUID,
        user_id: UUID,
        product: str = "self",
        mode: str = "full",
    ) -> FakeReport:
        return report

    async def fake_get_latest_narrative_for_report(*, db: FakeDB, report_id: UUID) -> None:
        return None

    class CommitCheckingTask:
        def __init__(self, db: FakeDB) -> None:
            self.db = db
            self.delay_calls = 0

        def delay(self, *args: Any, **kwargs: Any) -> None:
            assert self.db.commit_calls >= 1, "task enqueued before report commit"
            self.delay_calls += 1
            return None

    narrative_task = CommitCheckingTask(db)

    monkeypatch.setattr(ReportService, "generate_report", fake_generate_report)
    monkeypatch.setattr(reports_router, "get_latest_narrative_for_report", fake_get_latest_narrative_for_report)

    from workers.tasks import reports as worker_reports

    monkeypatch.setattr(worker_reports, "generate_report_narrative", narrative_task)

    response = await reports_router.generate_report(
        GenerateReportRequest(profile_id=str(report.profile_id), product="self", mode="full"),
        db=cast(Any, db),
        current_user=user_id,
    )

    assert db.commit_calls >= 1
    assert narrative_task.delay_calls == 1
    assert response.id == report.id


@pytest.mark.asyncio
async def test_get_report_pdf_renders_on_demand_from_report_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = make_report(status="ready")
    report.pdf_generated = False
    report.pdf_url = None
    captured: dict[str, object] = {}

    async def fake_get_report(self: ReportService, report_id: UUID, user_id: UUID) -> Report:
        captured["report_id"] = report_id
        captured["user_id"] = user_id
        return report

    async def fake_get_latest_narrative_for_report(*, db: object, report_id: UUID) -> None:
        captured["narrative_report_id"] = report_id
        return None

    def fake_generate_report_pdf(
        report_data: dict[str, Any],
        profile_name: str = "",
        *,
        narrative_content: dict[str, Any] | None,
        narrative_status: str | None,
        narrative_error: str | None,
    ) -> bytes:
        captured["report_data"] = report_data
        captured["profile_name"] = profile_name
        captured["narrative_content"] = narrative_content
        captured["narrative_status"] = narrative_status
        captured["narrative_error"] = narrative_error
        return b"%PDF-on-demand"

    monkeypatch.setattr(ReportService, "get_report", fake_get_report)
    monkeypatch.setattr(reports_router, "get_latest_narrative_for_report", fake_get_latest_narrative_for_report)
    monkeypatch.setattr(reports_router, "generate_report_pdf", fake_generate_report_pdf)

    current_user = uuid4()
    response = await reports_router.get_report_pdf(report.id, db=cast(Any, object()), current_user=current_user)

    assert response.status_code == 200
    assert response.media_type == "application/pdf"
    assert response.body == b"%PDF-on-demand"
    assert "attachment" in response.headers["content-disposition"]
    assert captured["report_data"] == report.report_data
    assert captured["narrative_report_id"] == report.id


@pytest.mark.asyncio
async def test_head_report_pdf_returns_headers_without_rendering_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = make_report(status="ready")
    captured: dict[str, object] = {}

    async def fake_get_report(self: ReportService, report_id: UUID, user_id: UUID) -> Report:
        captured["report_id"] = report_id
        captured["user_id"] = user_id
        return report

    monkeypatch.setattr(ReportService, "get_report", fake_get_report)

    current_user = uuid4()
    response = await reports_router.head_report_pdf(
        report.id,
        db=cast(Any, object()),
        current_user=current_user,
    )

    assert response.status_code == 200
    assert response.media_type == "application/pdf"
    assert response.body == b""
    assert "attachment" in response.headers["content-disposition"]
    assert captured["report_id"] == report.id
    assert captured["user_id"] == current_user
