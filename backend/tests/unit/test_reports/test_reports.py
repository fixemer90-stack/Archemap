"""Unit tests for the reports module."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

import app.modules.report_narratives.service as report_narrative_service
import app.modules.reports.router as reports_router
from app.modules.charts.models import ChartSnapshot
from app.modules.report_narratives.exceptions import NarrativeValidationError
from app.modules.report_narratives.models import ReportNarrative
from app.modules.report_narratives.validators import choose_narrative_recovery_action
from app.modules.reports.models import Report, ReportVersion
from app.modules.reports.schemas import (
    GenerateReportRequest,
    ReportResponse,
    ReportVersionResponse,
    build_narrative_response,
    build_report_response,
)
from app.modules.reports.service import (
    ReportService,
    _build_chart_summary,
    _build_report_data,
    _report_matches_snapshot,
)
from app.modules.reports.tasks import _run_async as _run_async_pdf_task
from tests.unit.test_report_narratives.test_schemas import make_self_narrative_payload

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


class TestBuildReportData:
    def test_includes_snapshot_socionics_contract(self) -> None:
        snapshot = ChartSnapshot(
            id=uuid4(),
            profile_id=uuid4(),
            user_id=uuid4(),
            engine_version="0.1.4",
            birth_data={},
            chart_data=make_chart_data(),
            features={},
            function_strengths={"Te": 0.94, "Si": 0.89},
            socionics={
                "top3": [
                    {
                        "type": "ЛСЭ",
                        "name": "Администратор",
                        "score": 0.803,
                        "confidence": 0.639,
                        "functions": "Te+Si",
                        "model_a": 0.635,
                    }
                ]
            },
        )
        profile = SimpleNamespace(
            name="Balthier",
            birth_date=datetime(1992, 12, 24, tzinfo=UTC).date(),
            birth_time=datetime(1992, 12, 24, 15, 30, tzinfo=UTC).time(),
            birth_time_accuracy="exact",
            birth_place="Москва",
            timezone="Europe/Moscow",
        )
        interpretation = SimpleNamespace(
            primary_archetype="Стратег",
            primary_score=0.78,
            primary_confidence=SimpleNamespace(
                value=0.72,
                label="средняя",
                reason_codes=["balanced"],
            ),
            claims=[],
            all_archetype_scores={"Стратег": 0.78},
            quality_warning=None,
            provenance={"engine_version": "rules-v1"},
        )

        report_data = _build_report_data(
            product="self",
            snapshot=snapshot,
            profile=profile,
            interpretation=interpretation,
            chart_summary=_build_chart_summary(snapshot.chart_data, make_features()),
        )

        assert report_data["socionics"] == snapshot.socionics
        assert report_data["function_strengths"] == snapshot.function_strengths
        assert report_data["chart"]["socionics"] == snapshot.socionics
        assert report_data["chart"]["function_strengths"] == snapshot.function_strengths


class TestReportMatchesSnapshot:
    def test_accepts_matching_source_chart_metadata(self) -> None:
        snapshot = ChartSnapshot(
            id=uuid4(),
            profile_id=uuid4(),
            user_id=uuid4(),
            engine_version="0.1.4",
            birth_data={},
            chart_data=make_chart_data(),
            features={},
            function_strengths={},
            socionics={},
        )

        report_data = {
            "source_chart": {
                "snapshot_id": str(snapshot.id),
                "engine_version": snapshot.engine_version,
            },
            "chart": {
                "planets": [{"name": "Sun", "house": 7}],
                "houses": [{"number": 1, "sign": "Leo", "longitude": 100}],
                "aspects": [],
            },
        }

        assert _report_matches_snapshot(report_data, snapshot) is True

    def test_detects_current_snapshot_report_missing_socionics_payload(self) -> None:
        snapshot = ChartSnapshot(
            id=uuid4(),
            profile_id=uuid4(),
            user_id=uuid4(),
            engine_version="0.1.4",
            birth_data={},
            chart_data=make_chart_data(),
            features={},
            function_strengths={"Te": 0.94},
            socionics={"top3": [{"type": "ЛСЭ", "name": "Администратор"}]},
        )

        report_data = {
            "source_chart": {
                "snapshot_id": str(snapshot.id),
                "engine_version": snapshot.engine_version,
            },
            "chart": {
                "planets": snapshot.chart_data["planets"],
                "houses": snapshot.chart_data["houses"],
                "aspects": snapshot.chart_data["aspects"],
            },
        }

        assert _report_matches_snapshot(report_data, snapshot) is False

    def test_accepts_current_snapshot_report_with_socionics_payload(self) -> None:
        snapshot = ChartSnapshot(
            id=uuid4(),
            profile_id=uuid4(),
            user_id=uuid4(),
            engine_version="0.1.4",
            birth_data={},
            chart_data=make_chart_data(),
            features={},
            function_strengths={"Te": 0.94},
            socionics={"top3": [{"type": "ЛСЭ", "name": "Администратор"}]},
        )

        report_data = {
            "source_chart": {
                "snapshot_id": str(snapshot.id),
                "engine_version": snapshot.engine_version,
            },
            "socionics": snapshot.socionics,
            "function_strengths": snapshot.function_strengths,
            "chart": {
                "socionics": snapshot.socionics,
                "function_strengths": snapshot.function_strengths,
                "planets": [{"name": "Sun", "house": 7}],
                "houses": [{"number": 1, "sign": "Leo", "longitude": 100}],
                "aspects": [],
            },
        }

        assert _report_matches_snapshot(report_data, snapshot) is True

    def test_accepts_legacy_report_when_chart_payload_matches(self) -> None:
        chart_data = make_chart_data()
        snapshot = ChartSnapshot(
            id=uuid4(),
            profile_id=uuid4(),
            user_id=uuid4(),
            engine_version="0.1.4",
            birth_data={},
            chart_data=chart_data,
            features={},
            function_strengths={},
            socionics={},
        )

        report_data = {
            "chart": {
                "planets": chart_data["planets"],
                "houses": chart_data["houses"],
                "aspects": chart_data["aspects"],
            }
        }

        assert _report_matches_snapshot(report_data, snapshot) is True

    def test_detects_stale_chart_payload(self) -> None:
        chart_data = make_chart_data()
        snapshot = ChartSnapshot(
            id=uuid4(),
            profile_id=uuid4(),
            user_id=uuid4(),
            engine_version="0.1.4",
            birth_data={},
            chart_data=chart_data,
            features={},
            function_strengths={},
            socionics={},
        )

        stale_report_data = {
            "chart": {
                "planets": [
                    {
                        **cast(dict[str, Any], chart_data["planets"][0]),
                        "house": 7,
                    }
                ],
                "houses": chart_data["houses"],
                "aspects": chart_data["aspects"],
            }
        }

        assert _report_matches_snapshot(stale_report_data, snapshot) is False


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

    def test_build_narrative_response_exposes_calibration_questions(self) -> None:
        report = make_report()
        now = datetime.now(UTC)
        narrative = ReportNarrative(
            id=uuid4(),
            report_id=report.id,
            product="self",
            prompt_version="self_story_v4",
            model_provider="mock",
            model_name="mock-self-v4",
            status="ready",
            content=make_self_narrative_payload(),
            input_hash="hash-1",
            generation_attempts=1,
            created_at=now,
            updated_at=now,
        )

        response = build_narrative_response(narrative)

        assert len(response.calibration_questions) == 5
        assert response.calibration_questions[0]["answer_type"] == "yes_no"

    def test_build_report_response_exposes_top_level_narrative_progress(self) -> None:
        report = make_report(status="generating_narrative")
        now = datetime.now(UTC)
        payload = make_self_narrative_payload()
        payload["stage_artifacts"] = [
            {
                "stage_id": "plan",
                "status": "ready",
                "prompt_version": "self_plan_v1",
                "model_name": "mock-self-v1",
                "input_hash": "a" * 64,
                "attempt_count": 1,
                "error_message": None,
                "artifact": {"summary": "plan"},
            },
            {
                "stage_id": "identity",
                "status": "ready",
                "prompt_version": "self_section_identity_v1",
                "model_name": "mock-self-v1",
                "input_hash": "b" * 64,
                "attempt_count": 1,
                "error_message": None,
                "artifact": {"summary": "identity"},
            },
        ]
        payload["stage_progress"] = {
            "total_stages": 7,
            "completed_stages": 2,
            "current_stage": "emotional",
            "ready": False,
            "stages": payload["stage_artifacts"],
        }
        narrative = ReportNarrative(
            id=uuid4(),
            report_id=report.id,
            product="self",
            prompt_version="self_story_v5",
            model_provider="mock",
            model_name="mock-self-v5",
            status="generating",
            content=payload,
            input_hash="hash-progress",
            generation_attempts=1,
            created_at=now,
            updated_at=now,
        )
        report.created_at = report.updated_at = now

        response = build_report_response(report, narrative)

        assert response.narrative_progress is not None
        assert response.narrative_progress.current_stage == "emotional"
        assert response.narrative_progress.completed_stages == 2
        assert len(response.narrative_stage_artifacts) == 2
        assert response.narrative_stage_artifacts[0].stage_id == "plan"

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
async def test_get_report_regenerates_stale_self_report(monkeypatch: pytest.MonkeyPatch) -> None:
    original_report = make_report(status="ready")
    refreshed_report = make_report(
        user_id=original_report.user_id,
        profile_id=original_report.profile_id,
        status="deterministic_ready",
        version=original_report.version + 1,
    )

    class FakeResult:
        def scalar_one_or_none(self) -> Report:
            return original_report

    class FakeDB:
        async def execute(self, *_args: Any, **_kwargs: Any) -> FakeResult:
            return FakeResult()

    service = ReportService(cast(Any, FakeDB()))

    async def fake_report_requires_refresh(report: Report, user_id: UUID) -> bool:
        assert report is original_report
        assert user_id == original_report.user_id
        return True

    async def fake_generate_report(
        profile_id: UUID,
        user_id: UUID,
        product: str = "self",
        mode: str = "full",
    ) -> Report:
        assert profile_id == original_report.profile_id
        assert user_id == original_report.user_id
        assert product == original_report.product
        assert mode == original_report.mode
        return refreshed_report

    monkeypatch.setattr(service, "_report_requires_refresh", fake_report_requires_refresh)
    monkeypatch.setattr(service, "generate_report", fake_generate_report)

    result = await service.get_report(original_report.id, original_report.user_id)

    assert result is refreshed_report


def test_choose_narrative_recovery_action_falls_back_after_recoverable_career_boundary_issue() -> None:
    errors = [
        NarrativeValidationError(
            code="career_boundary_violation",
            message="career copy leaked into self report",
            location="sections[2].body",
            recoverable=True,
        )
    ]

    assert choose_narrative_recovery_action(errors, repair_attempts_used=0, llm_available=True) == "repair"
    assert choose_narrative_recovery_action(errors, repair_attempts_used=1, llm_available=True) == "fallback"


def test_choose_narrative_recovery_action_marks_forbidden_language_as_failed() -> None:
    errors = [
        NarrativeValidationError(
            code="forbidden_language",
            message="unsafe language leaked into narrative",
            location="sections[4].body",
            recoverable=False,
        )
    ]

    assert choose_narrative_recovery_action(errors, repair_attempts_used=0, llm_available=True) == "narrative_failed"


@pytest.mark.asyncio
async def test_get_report_route_exposes_top_level_narrative_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = make_report(status="generating_narrative")
    report.created_at = report.updated_at = datetime.now(UTC)
    narrative_payload = make_self_narrative_payload()
    narrative_payload["stage_artifacts"] = [
        {
            "stage_id": "plan",
            "status": "ready",
            "prompt_version": "self_plan_v1",
            "model_name": "mock-self-v1",
            "input_hash": "c" * 64,
            "attempt_count": 1,
            "error_message": None,
            "artifact": {"summary": "plan"},
        },
        {
            "stage_id": "identity",
            "status": "ready",
            "prompt_version": "self_section_identity_v1",
            "model_name": "mock-self-v1",
            "input_hash": "d" * 64,
            "attempt_count": 1,
            "error_message": None,
            "artifact": {"summary": "identity"},
        },
    ]
    narrative_payload["stage_progress"] = {
        "total_stages": 7,
        "completed_stages": 3,
        "current_stage": "relationships",
        "ready": False,
        "stages": narrative_payload["stage_artifacts"],
    }
    narrative_payload["stage_resume"] = {
        "resume_mode": "resume",
        "reused_stages": ["plan", "identity"],
        "regenerated_stages": ["relationships", "assembly"],
        "stale_stages": [],
        "reason": "failed_stage:relationships",
    }
    narrative = ReportNarrative(
        id=uuid4(),
        report_id=report.id,
        product="self",
        prompt_version="self_story_v5",
        model_provider="mock",
        model_name="mock-self-v5",
        status="generating",
        content=narrative_payload,
        input_hash="route-progress",
        generation_attempts=1,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )

    class FakeDB:
        async def flush(self) -> None:
            return None

        async def commit(self) -> None:
            return None

        async def refresh(self, _report: Report) -> None:
            return None

    db = FakeDB()

    async def fake_get_report(self: ReportService, report_id: UUID, user_id: UUID) -> Report:
        assert report_id == report.id
        assert user_id == report.user_id
        return report

    async def fake_get_latest_narrative_for_report(**_kwargs: Any) -> ReportNarrative:
        return narrative

    monkeypatch.setattr(ReportService, "get_report", fake_get_report)
    monkeypatch.setattr(reports_router, "get_latest_narrative_for_report", fake_get_latest_narrative_for_report)

    response = await reports_router.get_report(report.id, cast(Any, db), report.user_id)

    assert response.narrative_progress is not None
    assert response.narrative_progress.current_stage == "relationships"
    assert response.narrative is not None
    assert response.narrative.stage_resume is not None
    assert response.narrative.stage_resume["resume_mode"] == "resume"
    assert response.narrative.stage_resume["regenerated_stages"] == ["relationships", "assembly"]
    assert len(response.narrative_stage_artifacts) == 2
    assert response.narrative_stage_artifacts[1].stage_id == "identity"


@pytest.mark.asyncio
async def test_get_report_route_enqueues_narrative_for_current_deterministic_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = make_report(status="deterministic_ready")
    report.created_at = report.updated_at = datetime.now(UTC)

    class FakeDB:
        def __init__(self) -> None:
            self.flush_calls = 0
            self.commit_calls = 0
            self.refresh_calls = 0

        async def flush(self) -> None:
            self.flush_calls += 1

        async def commit(self) -> None:
            self.commit_calls += 1

        async def refresh(self, _report: Report) -> None:
            self.refresh_calls += 1

    db = FakeDB()

    async def fake_get_report(self: ReportService, report_id: UUID, user_id: UUID) -> Report:
        assert report_id == report.id
        assert user_id == report.user_id
        return report

    async def fake_get_latest_narrative_for_report(**_kwargs: Any) -> None:
        return None

    scheduled: list[dict[str, str]] = []

    class DummyTask:
        def delay(self, **kwargs: str) -> None:
            scheduled.append(kwargs)

    monkeypatch.setattr(ReportService, "get_report", fake_get_report)
    monkeypatch.setattr(reports_router, "get_latest_narrative_for_report", fake_get_latest_narrative_for_report)
    monkeypatch.setitem(
        __import__("sys").modules,
        "workers.tasks.reports",
        SimpleNamespace(generate_report_narrative=DummyTask()),
    )

    response = await reports_router.get_report(report.id, cast(Any, db), report.user_id)

    assert response.status == "generating_narrative"
    assert scheduled == [{"report_id": str(report.id)}]
    assert db.commit_calls == 1
    assert db.refresh_calls == 1


@pytest.mark.asyncio
async def test_get_or_create_narrative_record_recovers_from_insert_race(monkeypatch: pytest.MonkeyPatch) -> None:
    report = make_report(status="deterministic_ready")
    narrative = ReportNarrative(
        id=uuid4(),
        report_id=report.id,
        product="self",
        prompt_version="self_story_v1",
        model_provider="deepseek",
        model_name="deepseek-v4-flash",
        status="narrative_failed",
        content=None,
        input_hash="hash-1",
        generation_attempts=1,
    )

    class FakeDB:
        def __init__(self) -> None:
            self.flush_calls = 0
            self.rollback_calls = 0

        def add(self, _obj: object) -> None:
            return None

        async def flush(self) -> None:
            self.flush_calls += 1
            if self.flush_calls == 1:
                raise IntegrityError("insert", {}, Exception("duplicate"))

        async def rollback(self) -> None:
            self.rollback_calls += 1

    service = report_narrative_service.ReportNarrativeService(cast(Any, FakeDB()))

    calls = {"count": 0}

    async def fake_find_matching_narrative_record(**_kwargs: Any) -> ReportNarrative | None:
        calls["count"] += 1
        return narrative if calls["count"] >= 2 else None

    monkeypatch.setattr(
        report_narrative_service,
        "_find_matching_narrative_record",
        fake_find_matching_narrative_record,
    )

    result = await service._get_or_create_narrative_record(
        report=report,
        input_hash="hash-1",
        model_name="deepseek-chat",
        prompt_version="self_story_v5",
        force_new=False,
    )

    assert result is narrative
    assert cast(Any, service.db).rollback_calls == 1


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

    async def fake_get_latest_narrative_for_report(
        *,
        db: FakeDB,
        report_id: UUID,
        report: Report | None = None,
    ) -> None:
        assert report_id == cast(Report, report).id
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

    async def fake_get_latest_narrative_for_report(
        *,
        db: FakeDB,
        report_id: UUID,
        report: Report | None = None,
    ) -> None:
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

    async def fake_get_latest_narrative_for_report(
        *,
        db: object,
        report_id: UUID,
        report: Report | None = None,
    ) -> None:
        assert report_id == cast(Report, report).id
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
