"""API tests for report narrative endpoints."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.core.exceptions import NotFoundError
from app.dependencies import get_current_user
from app.main import app
from app.modules.report_narratives.models import ReportNarrative
from app.modules.reports.models import Report
from app.modules.reports.service import ReportService


class _DummyPipeline:
    def __init__(self, store: dict[str, int]) -> None:
        self._store = store
        self._commands: list[tuple[str, str, int]] = []

    def incr(self, key: str) -> None:
        self._commands.append(("incr", key, 0))

    def expire(self, key: str, seconds: int) -> None:
        self._commands.append(("expire", key, seconds))

    async def execute(self) -> list[object]:
        for command, key, _value in self._commands:
            if command == "incr":
                self._store[key] = self._store.get(key, 0) + 1
        self._commands.clear()
        return []


class _DummyRedis:
    def __init__(self) -> None:
        self._store: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        value = self._store.get(key)
        return str(value) if value is not None else None

    async def ttl(self, key: str) -> int:
        return 60 if key in self._store else -1

    def pipeline(self) -> _DummyPipeline:
        return _DummyPipeline(self._store)


@pytest.fixture
def current_user_id() -> UUID:
    return uuid4()


@pytest.fixture(autouse=True)
def override_current_user(current_user_id: UUID, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    app.dependency_overrides[get_current_user] = lambda: current_user_id
    monkeypatch.setattr("app.api.middleware.get_redis_client", lambda: _DummyRedis())
    yield
    app.dependency_overrides.pop(get_current_user, None)


def make_report(*, user_id: UUID, status: str = "ready", product: str = "self") -> Report:
    report = Report(
        id=uuid4(),
        user_id=user_id,
        profile_id=uuid4(),
        product=product,
        version=1,
        status=status,
        mode="full",
        report_data={"product": product, "archetype": {"primary": "Стратег"}},
        archetype="Стратег",
        score=0.78,
        confidence=0.72,
        pdf_generated=False,
    )
    report.created_at = report.updated_at = datetime.now(UTC)
    return report


def make_narrative(report: Report, *, status: str = "ready") -> ReportNarrative:
    narrative = ReportNarrative(
        id=uuid4(),
        report_id=report.id,
        product=report.product,
        prompt_version="self_story_v1",
        model_provider="mock",
        model_name="mock-self-v1",
        status=status,
        content={
            "title": "Ваш внутренний портрет",
            "hero": {
                "heading": "Как вас воспринимают",
                "body": "Тёплый и собранный образ.",
                "evidence_notes": [{"fact_ids": ["sun_virgo_house_9"], "note": "Солнце в Деве."}],
            },
            "sections": [
                {
                    "slug": "strengths",
                    "heading": "Сильные стороны",
                    "body": "Вы умеете наводить порядок в сложных темах.",
                    "evidence_notes": [{"fact_ids": ["sun_virgo_house_9"], "note": "Солнце в 9 доме."}],
                }
            ],
            "career_cta": {
                "label": "Развернуть карьерный сценарий",
                "reason": "Для глубокой карьеры нужен отдельный отчёт.",
            },
        },
        input_hash="hash123",
    )
    narrative.created_at = narrative.updated_at = datetime.now(UTC)
    return narrative


class TestReportNarrativeApi:
    @pytest.mark.asyncio
    async def test_get_report_returns_deterministic_payload_with_null_narrative_while_generation_in_progress(
        self,
        client: AsyncClient,
        current_user_id: UUID,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        report = make_report(user_id=current_user_id, status="generating_narrative")

        monkeypatch.setattr(ReportService, "get_report", AsyncMock(return_value=report))
        monkeypatch.setattr(
            "app.modules.reports.router.get_latest_narrative_for_report",
            AsyncMock(return_value=None),
        )

        response = await client.get(f"/api/v1/reports/{report.id}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "generating_narrative"
        assert payload["report_data"]["product"] == "self"
        assert payload["narrative"] is None

    @pytest.mark.asyncio
    async def test_get_report_returns_ready_narrative_payload(
        self,
        client: AsyncClient,
        current_user_id: UUID,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        report = make_report(user_id=current_user_id, status="ready")
        narrative = make_narrative(report)

        monkeypatch.setattr(ReportService, "get_report", AsyncMock(return_value=report))
        monkeypatch.setattr(
            "app.modules.reports.router.get_latest_narrative_for_report",
            AsyncMock(return_value=narrative),
        )

        response = await client.get(f"/api/v1/reports/{report.id}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["narrative"]["prompt_version"] == "self_story_v1"
        assert payload["narrative"]["model_name"] == "mock-self-v1"
        assert payload["narrative"]["sections"][0]["slug"] == "strengths"
        assert payload["narrative"]["career_cta"]["label"] == "Развернуть карьерный сценарий"

    @pytest.mark.asyncio
    async def test_generate_report_response_can_return_generating_narrative_status(
        self,
        client: AsyncClient,
        current_user_id: UUID,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        report = make_report(user_id=current_user_id, status="generating_narrative")

        monkeypatch.setattr(ReportService, "generate_report", AsyncMock(return_value=report))
        monkeypatch.setattr(
            "workers.tasks.reports.generate_pdf",
            type("PdfTaskStub", (), {"delay": staticmethod(lambda **_: None)}),
        )
        monkeypatch.setattr(
            "workers.tasks.reports.generate_report_narrative",
            type("NarrativeTaskStub", (), {"delay": staticmethod(lambda **_: None)}),
        )
        monkeypatch.setattr(
            "app.modules.reports.router.get_latest_narrative_for_report",
            AsyncMock(return_value=None),
        )

        response = await client.post(
            "/api/v1/reports/generate",
            json={"profile_id": str(report.profile_id), "product": "self", "mode": "full"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "generating_narrative"
        assert payload["narrative"] is None

    @pytest.mark.asyncio
    async def test_regenerate_endpoint_enqueues_forced_narrative_attempt(
        self,
        client: AsyncClient,
        current_user_id: UUID,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        report = make_report(user_id=current_user_id, status="ready")
        captured: dict[str, object] = {}

        monkeypatch.setattr(ReportService, "get_report", AsyncMock(return_value=report))
        monkeypatch.setattr(
            "app.modules.reports.router.get_latest_narrative_for_report",
            AsyncMock(return_value=None),
        )

        class NarrativeTaskStub:
            @staticmethod
            def delay(*, report_id: str, force: bool = False) -> None:
                captured["report_id"] = report_id
                captured["force"] = force

        monkeypatch.setattr(
            "workers.tasks.reports.generate_report_narrative",
            NarrativeTaskStub,
        )

        response = await client.post(f"/api/v1/reports/{report.id}/narrative/regenerate")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "generating_narrative"
        assert captured == {"report_id": str(report.id), "force": True}

    @pytest.mark.asyncio
    async def test_regenerate_endpoint_denies_access_to_foreign_report(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(ReportService, "get_report", AsyncMock(side_effect=NotFoundError("Report not found")))

        response = await client.post(f"/api/v1/reports/{uuid4()}/narrative/regenerate")

        assert response.status_code == 404
        assert response.json()["detail"] == "Report not found"
